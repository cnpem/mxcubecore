from pyicat_plus.client.main import IcatClient

from mxcubecore.HardwareObjects.ICATLIMS import ICATLIMS


class LNLSLIMS(ICATLIMS):
    def init(self):
        self.url = self.get_property("ws_root")
        self.ingesters = self.get_property("queue_urls")
        self.investigations = []
        self.samples = []
        self._last_login_user = None

    def _create_icat_client(self):
        return IcatClient(
            icatplus_restricted_url=self.get_property("icatplus_restricted_url")
        )

    def is_single_session_available(self):
        """
        True if there is no active session and there is
        a single session available
        """
        return (
            self.session_manager.active_session is None
            and len(self.session_manager.sessions) == 1
        )

    def _create_icat_session(self, user_name: str, password: str):
        icat_client = self._create_icat_client()
        icat_session = icat_client.do_log_in(
            username=user_name, password=password, plugin="oidc"
        )
        return icat_session, icat_client

    def login(self, user_name, token, is_local_host):
        self.is_local_host = is_local_host
        session_manager, icat_session, sessions = super().login(
            user_name, token, self.session_manager
        )
        self.session_manager = session_manager
        self.add_user_and_shared_sessions(icat_session, sessions)
        if self.is_single_session_available():
            single_session = self.session_manager.sessions[0]
            self.set_active_session_by_id(single_session.session_id)

        self._last_login_user = user_name
        return session_manager

    def _last_login_session(self):
        return self._icat_session_dict.get(self._last_login_user) or self.icat_session

    def get_user_name(self):
        return self._last_login_session().username

    def get_full_user_name(self):
        return self._last_login_session().full_name

    def get_active_lims(self):
        return self.get_lims_name()[0]

    def finalize_data_collection(self, data_collect_parameters):
        return

    def store_robot_action(self, proposal_id: str):
        return
