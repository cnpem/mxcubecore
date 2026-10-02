import os
import time

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.Session import Session


class LNLSSession(Session):
    def get_proposal(self):
        proposal = super().get_proposal()
        return proposal.replace("sc", "").replace("rap", "").replace("industrial", "").replace("tc", "")

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
        HWR.beamline.session.proposal_code = None
        HWR.beamline.session.proposal_id = None

    def get_default_subdir(self, sample_data: dict) -> str:
        if isinstance(sample_data, dict):
            address = sample_data.get("location")
            puck = address.split(":")[0]
            sample = address.split(":")[1]
        else:
            address = sample_data.location
            puck = address[0]
            sample = address[1]
        subdir = HWR.beamline.sample_changer.return_subdir_value(puck, sample)
        return subdir
