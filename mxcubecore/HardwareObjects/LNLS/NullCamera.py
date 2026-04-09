"""
Class for cameras connected by EPICS Area Detector
"""
from mxcubecore.BaseHardwareObjects import HardwareObject


class NullCamera(HardwareObject):

    def init(self):
        super().init()
        self.stream_hash = ''
        self._current_stream_size = (0, 0)

    def get_width(self) -> int:
        return 1280

    def get_height(self) -> int:
        return 1024

    def get_available_stream_sizes(self):
        return []

    def get_stream_size(self):
        return (1280, 1024, 1)