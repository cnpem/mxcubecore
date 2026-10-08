import json
import logging
import os
from typing import Optional

from pydantic import BaseModel, Field

from mxcubecore import HardwareRepository as HWR
from mxcubecore.model import queue_model_objects
from mxcubecore.model.queue_model_objects import DataCollection
from mxcubecore.queue_entry.base_queue_entry import (
    QueueExecutionException,
    TaskPrerequisite,
)
from mxcubecore.queue_entry.data_collection import DataCollectionQueueEntry

def _unit(unit):
    return {"json_schema_extra": {"unit": unit}}


class LnlsPathParameters(BaseModel):
    prefix: str = ""
    subdir: str = ""
    experiment_name: Optional[str] = None


class LnlsCommonParameters(BaseModel):
    type: str = "lnls_multi_crystals_collection"
    label: str = "Multi Crystals Collection"


class LnlsCollectionParameters(BaseModel):
    shape: str = ""
    kappa: Optional[float] = None
    kappa_phi: Optional[float] = None
    energy: float = 0.0
    transmission: float = 0.0
    resolution: float = 0.0


class LnlsUserParameters(BaseModel):
    num_images: int = Field(100, gt=0, title="Number of images")
    first_image: int = Field(1, ge=1, title="First image")
    exp_time: float = Field(0.005, gt=0, title="Exposure time", **_unit("s"))
    osc_range: float = Field(0.1, gt=0, title="Oscillation range", **_unit("°"))
    osc_start: float = Field(0.0, title="Oscillation start", **_unit("°"))


class LnlsLegacyParameters(BaseModel):
    pass


class LnlsMultiCrystalsCollectionTaskParameters(BaseModel):
    path_parameters: LnlsPathParameters
    common_parameters: LnlsCommonParameters
    collection_parameters: LnlsCollectionParameters
    user_collection_parameters: LnlsUserParameters
    legacy_parameters: LnlsLegacyParameters

    @staticmethod
    def update_dependent_fields(field_data):
        return {}

    @staticmethod
    def ui_schema():
        return json.dumps(
            {
                "ui:order": [
                    "num_images",
                    "first_image",
                    "exp_time",
                    "osc_range",
                    "osc_start",
                    "*",
                ],
                "ui:submitButtonOptions": {"norender": "true"},
                **{
                    name: {"ui:widget": "hidden"}
                    for name in (
                        "energy",
                        "transmission",
                        "resolution",
                        "kappa",
                        "kappa_phi",
                    )
                },
            }
        )


class LnlsMultiCrystalsCollectionQueueModel(DataCollection):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class LnlsMultiCrystalsCollectionQueueEntry(DataCollectionQueueEntry):
    QMO = LnlsMultiCrystalsCollectionQueueModel
    DATA_MODEL = LnlsMultiCrystalsCollectionTaskParameters
    NAME = "Multi Crystals Collection"
    REQUIRES = [TaskPrerequisite.POINT, TaskPrerequisite.NO_SHAPE_2D]

    def __init__(self, view=None, data_model=None, view_set_queue_entry=True):
        super().__init__(view, data_model, view_set_queue_entry)
        self._shape = None

    def set_container(self, queue_entry_container):
        super().set_container(queue_entry_container)
        if queue_entry_container is not None:
            self._assign_run_number()

    def _assign_run_number(self):
        pt = self.get_data_model().acquisitions[0].path_template
        if pt.run_number:
            return
        pt.run_number = HWR.beamline.queue_model.get_next_run_number(pt)
        while any(os.path.isfile(f) for f in pt.get_first_and_last_file()):
            pt.run_number += 1
            if pt.run_number > 1000:
                msg = "Over a thousand runs of the same collection"
                raise RuntimeError(msg)

    def get_data_collect_parameters(self):
        self._task_data_to_acquisition()
        dc = self.get_data_model()
        cpos = dc.acquisitions[0].acquisition_parameters.centred_position
        empty_cpos = queue_model_objects.CentredPosition()
        return queue_model_objects.to_collect_dict(
            dc, dc.get_sample_node(), cpos if cpos != empty_cpos else None
        )[0]

    def pre_execute(self):
        super().pre_execute()
        self._task_data_to_acquisition()

    def _task_data_to_acquisition(self):
        model = self.get_data_model()
        task_data = model.task_data
        acq = model.acquisitions[0].acquisition_parameters
        acq.set_from_dict(
            {
                **task_data.common_parameters.model_dump(),
                **task_data.user_collection_parameters.model_dump(),
            }
        )
        acq.energy = HWR.beamline.energy.get_value()
        acq.transmission = HWR.beamline.transmission.get_value()
        acq.resolution = HWR.beamline.resolution.get_value()
        self._shape = None
        shape_id = (
            getattr(model, "shape", None) or task_data.collection_parameters.shape
        )
        if shape_id not in (None, "", -1) and HWR.beamline.sample_view:
            self._shape = HWR.beamline.sample_view.get_shape(shape_id)
            if self._shape is not None:
                acq.centred_position = self._shape.get_centred_position()

    def execute(self):
        data_collect_parameters = self.get_data_collect_parameters()
        print(data_collect_parameters)
        if self._shape is None:
            raise QueueExecutionException("No point selected for this task", self)
        x, y = self._shape.screen_coord[:2]   # pixels on the sample view
        logging.getLogger("HWR").info(f"{self._shape.name}: screen_coord = ({x}, {y})")
        HWR.beamline.sample_view.move_to_beam(x, y)
        queue_manager = HWR.beamline.get_object_by_role('queue_manager')
        points_snapshots_folder = queue_manager.points_snapshots_folder
        json_path = queue_manager.json_path
        owner = ""
        HWR.beamline.collect.do_collect_multicrystals(owner, data_collect_parameters, points_snapshots_folder, json_path)