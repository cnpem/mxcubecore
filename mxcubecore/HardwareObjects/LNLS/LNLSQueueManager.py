import logging

from mxcubecore import HardwareRepository as HWR
from mxcubecore import queue_entry
from mxcubecore.HardwareObjects.QueueManager import QueueManager
from mxcubecore.model import queue_model_objects
from mxcubecore.queue_entry import data_collection


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
        self.pause_before_centring = self.get_property("pause_before_centring", False)
        data_collection.center_before_collect = self.center_before_collect

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

    def should_pause_before_centring(self, entry=None):
        return self.pause_before_centring

    def center_before_collect(self, view, dm, queue, sample_view):
        """
        LNLS version of base_queue_entry.center_before_collect.
        """
        log = logging.getLogger("user_level_log")

        if self.should_pause_before_centring(self.get_current_entry()):
            view.setText(1, "Waiting for input")
            log.info("Please select, or center on a new position and press resume.")
            queue.pause(True)

        if sample_view.get_selected_shapes():
            shape = sample_view.get_selected_shapes()[0]
            pos = shape.mpos()
        else:
            log.info("No centred position selected, using current position.")
            pos = sample_view.get_positions()
            shape = sample_view.add_shape_from_mpos([pos], (0, 0), "P")

        view.setText(1, "Centring completed")
        log.info("Centring completed")

        return queue_model_objects.CentredPosition(pos), shape

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