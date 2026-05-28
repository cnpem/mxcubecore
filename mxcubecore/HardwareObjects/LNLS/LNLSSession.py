import os
import time

from mxcubecore.HardwareObjects.Session import Session
from mxcubecore import HardwareRepository as HWR


class LNLSSession(Session):
    def get_proposal(self):
        proposal = super().get_proposal()
        return proposal.replace("sc", "").replace("rap", "")

    def get_base_image_directory(self):
        start_time = time.strftime("%Y%m%d")
        proposal = self.get_proposal()
        directory = os.path.join(
            self.base_directory,
            proposal,
            "data",
            start_time,
        )
        return directory

    def clear_session(self):
        HWR.beamline.session.session_id = None
        HWR.beamline.session.proposal_number = None
        HWR.beamline.session.proposal_id = None