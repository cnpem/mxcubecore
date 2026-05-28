import time
import gevent
import logging
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

    def start_spectrum(self, integration_time, data_dir, archive_dir, prefix, session_id, blsample_id, cpos,):
            beam_energy = self.energy.get_value()
            print("integration_time: ", integration_time)
            print("data_dir: ", data_dir)
            print("prefix: ", prefix)
            print("beam_energy: ", beam_energy)

            #proc_dir = data_dir.replace('/data/', '/proc/') + '/xrfproc_{}'.format(prefix)
            #try:
            #    os.makedirs(data_dir, exist_ok=True)
            #    os.makedirs(proc_dir, exist_ok=True)
            #except Exception as e:
            #    logging.getLogger("HWR").info("error creating XRF directories: {}".format(e))

            plan_kwargs = {
                "file_path": data_dir,
                "file_name": prefix,
                "acquire_time": integration_time,
                "beam_energy": beam_energy
            }

            print("plan_params: ", plan_kwargs)

            #self._bluesky_api.execute_plan(
            #    plan_name="xrf",
            #    kwargs=plan_kwargs,
            #)

            time.sleep(3)
            self._ready_event.set()
            return
