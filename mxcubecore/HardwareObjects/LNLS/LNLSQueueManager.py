import logging

from mxcubecore import queue_entry
from mxcubecore.HardwareObjects.QueueManager import QueueManager
from mxcubecore import HardwareRepository as HWR


class LNLSQueueManager(QueueManager):
    """
    This class implements a queue manager for LNLS.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSQueueManager.LNLSQueueManager
    configuration:
      site_entry_path: LNLS
    """

    def init(self):
        super().init()
        self.json_path = None
        self.points_snapshots_folder = None

    def execute(self, entry=None):
        roots = [entry] if entry is not None else self.get_queue_entry_list()
        mc_entries = self.find_entries(roots, "LnlsMultiCrystalsCollectionQueueEntry")

        if mc_entries:
            logging.getLogger("HWR").info(f"{len(mc_entries)} multi-crystals collection(s) will run")
            sv = HWR.beamline.get_object_by_role('sample_view')
            json_path, points_snapshots_folder = sv.save_points_and_snapshot_to_png()
            self.json_path = json_path
            self.points_snapshots_folder = points_snapshots_folder

        super().execute(entry)

    @staticmethod
    def find_entries(roots, class_name):

        cls = getattr(queue_entry, class_name, None)
        if cls is None:
            return []

        found = []

        def walk(e):
            if not e.is_enabled():
                return
            if isinstance(e, cls) and not e.get_data_model().is_executed():
                found.append(e)
            for child in e.get_queue_entry_list():
                walk(child)

        for root in roots:
            walk(root)

        return found