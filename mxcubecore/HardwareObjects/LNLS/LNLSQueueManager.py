from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.QueueManager import QueueManager


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
            print(f"\nMULTI POINTS DC\n")
            number_of_points = len(self._queue_entry_list[0].get_data_model().get_children())
            print(f"\nNUMBER OF POINTS: {number_of_points}\n")
            mxcollect.multi_crystals = True
        else:
            print(f"\nSINGLE POINT DC\n")
            mxcollect.multi_crystals = False
        super().execute(entry)

    def __execute_task(self):
        super().__execute_task()
        mxcollect = HWR.beamline.get_object_by_role('collect')
        mxcollect.multi_crystals = False
        print("\nFIM DE EXECUTE TASK E FIM DA COLETA\n")