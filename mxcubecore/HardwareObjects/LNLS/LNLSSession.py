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
        self.session_id = None
        self.proposal_number = None
        self.proposal_code = None
        self.proposal_id = None
        lims = HWR.beamline.lims
        operator = lims._active_user
        lims.session_manager.active_session = None
        lims.investigations = []
        with lims._active_user_lock:
            lims._active_user = None
        if operator is not None:
            lims.remove_user(operator)
        if lims._last_login_user == operator:
            lims._last_login_user = None

    def get_default_subdir(self, sample_data: dict) -> str:
        try:
            if isinstance(sample_data, dict):
                address = sample_data.get("location")
                puck = address.split(":")[0]
                sample = address.split(":")[1]
            else:
                address = sample_data.location
                puck = address[0]
                sample = address[1]
            subdir = HWR.beamline.sample_changer.return_subdir_value(puck, sample)
        except:
            subdir = super().get_default_subdir(sample_data)
        return subdir
