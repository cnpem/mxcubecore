import logging
import requests

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractMultiCollect import (
    AbstractMultiCollect,
)
import random
from mxcubeweb.core.util.convertutils import to_camel


class LNLSMultiCollect(AbstractMultiCollect, HardwareObject):
    """
    Class for data collection at LNLS.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSMultiCollect.LNLSMultiCollect
    epics:
        "MNC:B:PILATUS4_4M:cam1:":
            channels:
                detector_sequence_id:
                    suffix: "SequenceId"
    configuration:
        auto_processing:
            program: []
    """

    def __init__(self, name):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.wavelength = HWR.beamline.get_object_by_role("wavelength")
        self.machine_info = HWR.beamline.get_object_by_role("machine_info")
        self.detector_distance = HWR.beamline.get_object_by_role("detector_distance")
        self._centring_status = None
        self.ready_event = None
        self.actual_frame_num = 0
        self.collection_id = None
        self.xds_directory = ""

    def init(self):
        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))
        self.mx_collect_channels = self._CommandContainer__channels

    def flyscan_procedure(self, owner, data_collect_parameters):
        data_collect_parameters["status"] = "Data collection successful"
        file_parameters = data_collect_parameters["fileinfo"]
        file_name = "%(prefix)s_%(run_number)04d" % file_parameters
        start = float(
            data_collect_parameters["oscillation_sequence"][0]["start"]
        )  # omega start pos
        step_size = float(data_collect_parameters["oscillation_sequence"][0]["range"])
        num_of_points = int(
            data_collect_parameters["oscillation_sequence"][0]["number_of_images"]
        )
        end = start + step_size * num_of_points
        acquire_time = float(
            data_collect_parameters["oscillation_sequence"][0]["exposure_time"]
        )
        self._bluesky_api.execute_plan(
            plan_name="flyscan",
            kwargs={
                "start": start,
                "end": end,
                "file_path": file_parameters["directory"],
                "file_name": file_name,
                "angle_increment": step_size,
                "acquire_time": acquire_time,
                "num_images": num_of_points,
                "snapshot_num": self.number_of_snapshots,
                "debug": True
            },
        )

    def get_pxpmm(self):
        diffractometer = HWR.beamline.diffractometer
        zoom_enum = diffractometer.zoom.get_value()
        current_zoom = zoom_enum.name
        mm_per_pixel_x = diffractometer.zoom.get_property("mm_per_pixel_x")[current_zoom]
        mm_per_pixel_y = diffractometer.zoom.get_property("mm_per_pixel_y")[current_zoom]
        pixel_per_mm_x = round(1 / mm_per_pixel_x, 6)
        pixel_per_mm_y = round(1 / mm_per_pixel_y, 6)
        return [pixel_per_mm_x, pixel_per_mm_y]

    def get_grid_start_by_axis(self, selected_grid_dict, axis):
        diff_from_beam = (
            selected_grid_dict["screen_coord"][axis] - selected_grid_dict["beam_pos"][axis]
        )
        pxpmm = self.get_pxpmm()[axis]
        return diff_from_beam / pxpmm

    def get_grid_start_position(self, selected_grid_dict):
        diffractometer = HWR.beamline.diffractometer
        sampx = diffractometer.sampx.get_value()
        samp_y = diffractometer.sampy.get_value()

        grid_x = self.get_grid_start_by_axis(selected_grid_dict, 0)
        grid_y = -1 * self.get_grid_start_by_axis(selected_grid_dict, 1)

        start_x = sampx - grid_x
        start_y = samp_y - grid_y

        return start_x, start_y

    def get_grid_scan_data(self):
        grid_list = HWR.beamline.sample_view.get_grids()
        selected_grid_dict = None
        for grid in grid_list:
            grid_as_dict = grid.as_dict()
            if grid_as_dict["selected"]:
                grid_found_msg = "Found selected grid {}".format(grid_as_dict["name"])
                selected_grid_dict = grid_as_dict
                selected_grid = grid
                break
            else:
                print("Ignoring grid {}".format(grid_as_dict["id"]))

        if selected_grid_dict is None:
            grid_found_msg = "Found unselected grid {}".format(grid_as_dict["name"])
            logging.getLogger("HWR").info(grid_found_msg)
            selected_grid_dict = grid_list[0].as_dict()
            selected_grid = grid_list[0]

        start_x, start_y = self.get_grid_start_position(selected_grid_dict)
        width = selected_grid_dict["dx_mm"]
        height = selected_grid_dict["dy_mm"]
        steps_x = selected_grid_dict["steps_x"]
        steps_y = selected_grid_dict["steps_y"]

        return start_x, start_y, width, height, steps_x, steps_y, selected_grid

    def return_gridscan_processing_results(self, grid):
        num_cols = grid.num_cols
        num_rows = grid.num_rows
        grid_result = {
            "heatmap": {}
        }
        for row in range(num_rows):
            for col in range(num_cols):
                flat_index = row * num_cols + col
                cell_id = str(row * num_cols + col + 1)
                score = random.randint(0, 255)
                color = [score, 0, 0]
                grid_result["heatmap"][cell_id] = [
                    score,
                    color
                ]
        shape = HWR.beamline.sample_view.get_shape(grid.id)
        shape.set_result(grid_result)
        shape.result_data_path = None
        shape_dict = to_camel(shape.as_dict())
        shape_dict["cellCountFun"] = "left-to-right"
        HWR.beamline.sample_view.emit("newGridResult", shape_dict)

    def gridscan_procedure(self, owner, data_collect_parameters):
        start_x, start_y, width, height, steps_x, steps_y, selected_grid = self.get_grid_scan_data()
        file_parameters = data_collect_parameters["fileinfo"]
        file_name = "%(prefix)s_%(run_number)04d" % file_parameters
        exp_time = float(
            data_collect_parameters["oscillation_sequence"][0]["exposure_time"]
        )
        start_angle = float(data_collect_parameters["oscillation_sequence"][0]["start"])
        oscillation_range = float(
            data_collect_parameters["oscillation_sequence"][0]["range"]
        )
        self._bluesky_api.execute_plan(
            plan_name="complete_grid_scan",
            kwargs={
                "start_x": start_x,
                "start_y": start_y,
                "width": width,
                "height": height,
                "num_rows": steps_x,
                "num_cols": steps_y,
                "file_path": file_parameters["directory"],
                "file_name": file_name,
                "start_angle": start_angle,
                "oscillation_range": oscillation_range,
                "acquire_time": exp_time,
                "debug": True
            },
        )
        self.return_gridscan_processing_results(selected_grid)

    def helical_scan_procedure(self, owner, data_collect_parameters):
        cplist = []
        points = HWR.beamline.sample_view.get_points()
        for point in points:
            print(dir(point))
            cp = point.get_centred_positions()[0].as_dict()
            cplist.append(cp)
        logging.getLogger("HWR").info(f"\n{cplist}\n")
        logging.getLogger("HWR").info(f"\n{data_collect_parameters}\n")

    def get_detector_sequence_id(self):
        sequence_id = int(self.mx_collect_channels["detector_sequence_id"].get_value()) + 2
        return sequence_id

    def perform_xlsx_request(self, data_collect_parameters):
        try:
            wl = round(self.wavelength.get_value(), 6)
            dd = round(self.detector_distance.get_value(), 6)
            bc = round(self.machine_info.get_current(), 6)
            cb = int(data_collect_parameters["fileinfo"]["run_number"])
            cb = f"{cb:04d}"
            sequence_id = self.get_detector_sequence_id()
            prefix = data_collect_parameters['fileinfo']['prefix']
            file_name = f"{prefix}_{cb}_{sequence_id}_master.h5"
            file_path = data_collect_parameters["fileinfo"]['directory']
            file_abs_path = f"{file_path}/{file_name}"
            file_abs_path = file_abs_path.replace("//", "/")
            logging.getLogger("HWR").info(f"filename is {file_abs_path}")
            timeout_seconds = 3
            dataFromMxcube = data_collect_parameters
            additionalData = {"Collection Batch": cb,
                            "Wavelength": wl, "Detector distance (mm)": dd,
                            "Electric Current (mA)": bc, "Loop image": "", "Absolute Path": file_abs_path}
            proposalId = data_collect_parameters["fileinfo"]["directory"].split('/proposals/')[1].split('/')[0]
            url = 'http://10.39.50.105:5000/turn-mxcube-data-in-dict-to-proposal-xlsx'
            payload = {"proposalId": proposalId, "dataFromMxcube": dataFromMxcube, "additionalData": additionalData}
            response = requests.post(url, json=payload, timeout=timeout_seconds)
            logging.getLogger("HWR").info(str(response.status_code))
            logging.getLogger("HWR").info(str(response.text))
            logging.getLogger("HWR").info(str(response.json()))
        except requests.exceptions.Timeout:
            logging.getLogger("HWR").info("XLSX data saving timed out (collection will still happen)")
        except Exception as e:
            logging.getLogger("HWR").info(f"Error trying to send info: {e}")
            logging.getLogger("HWR").info("Collection will still happen")

    def do_collect(self, owner, data_collect_parameters):
        #self.perform_xlsx_request(data_collect_parameters)
        experiment_type = data_collect_parameters["experiment_type"]
        if experiment_type == "OSC":
            self.flyscan_procedure(owner, data_collect_parameters)
        elif experiment_type == "Mesh":
            self.gridscan_procedure(owner, data_collect_parameters)
        elif experiment_type == "Helical":
            self.helical_scan_procedure(owner, data_collect_parameters)