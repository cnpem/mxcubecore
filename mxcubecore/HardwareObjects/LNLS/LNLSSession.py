from mxcubecore.HardwareObjects.Session import Session
import time
import os

class LNLSSession(Session):
    def get_base_image_directory(self):
        start_time = time.strftime("%Y%m%d")
        proposal = self.get_proposal()
        proposal = proposal.replace("test0020", "00000000")
        directory = os.path.join(
                self.base_directory,
                proposal,
                "data",
                start_time,
            )
        return directory