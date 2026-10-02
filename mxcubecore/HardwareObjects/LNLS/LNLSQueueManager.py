from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.QueueManager import QueueManager

import logging


class LNLSQueueManager(QueueManager):
    """
    This class implements a queue manager for LNLS.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSQueueManager.LNLSQueueManager
    configuration: {}
    """

    def init(self):
        super().init()
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")

    def pause(self, state):
        if state:
            self._bluesky_api.pause()
        else:
            self._bluesky_api.resume()
        self.set_pause(state)

    def stop(self):
        self._bluesky_api.abort()
        super().stop()

    def execute(self, entry=None):
        mxcollect = HWR.beamline.get_object_by_role('collect')
        if not entry:
            logging.getLogger("HWR").info("Multiple Points Data Collection")
            data_model_children_list = self._queue_entry_list[0].get_data_model().get_children()
            number_of_points = len(data_model_children_list)
            logging.getLogger("HWR").info(f"Number of Points: {number_of_points}")
            sample_view = HWR.beamline.get_object_by_role("sample_view")
            json_file_path, points_snapshots_folder = sample_view.save_points_and_snapshot_to_png()
            mxcollect.multi_crystals = True
            mxcollect.current_json_path = json_file_path
            mxcollect.current_points_snapshots_folder = points_snapshots_folder

        else:
            logging.getLogger("HWR").info("Single Point Data Collection")
            mxcollect.multi_crystals = False
            mxcollect.current_json_path = None
            mxcollect.current_points_snapshots_folder = None
        super().execute(entry)

    def __execute_task(self):
        super().__execute_task()
        mxcollect = HWR.beamline.get_object_by_role('collect')
        mxcollect.multi_crystals = False
        mxcollect.current_json_path = None
        mxcollect.current_points_snapshots_folder = None
        logging.getLogger("HWR").info("End of task and end of data collection")