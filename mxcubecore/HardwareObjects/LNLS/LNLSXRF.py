import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject


class LNLSXRF(HardwareObject):
    """
    XRF class for LNLS. It uses bluesky to launch the XRF
    data collection.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSXRF.LNLSXRF
    configuration: {}
    """

    def __init__(self, name):
        super().__init__(name)
        self.energy = HWR.beamline.get_object_by_role("energy")
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")

    def init(self):
        self._ready_event = gevent.event.Event()

    def start_spectrum(
        self,
        integration_time,
        data_dir,
        archive_dir,
        prefix,
        session_id,
        blsample_id,
        cpos,
    ):

        if self._bluesky_api.api.status()["manager_state"] == "executing_queue":
            raise RuntimeError("Another Bluesky plan is still running")

        collection_number = int(prefix.split("_")[-1])
        collection_number = f"{collection_number:05d}"
        prefix = "_".join(prefix.split("_")[0:-1])
        file_name = f"{prefix}_{collection_number}"

        plan_kwargs = {
            "file_path": data_dir,
            "file_name": file_name,
            "acquire_time": integration_time,
            "new_sample": False,
        }

        self._bluesky_api.execute_plan(
            plan_name="xrf",
            kwargs=plan_kwargs,
        )

        self._ready_event.set()
        return
