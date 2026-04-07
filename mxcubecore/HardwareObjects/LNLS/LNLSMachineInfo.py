import time

import gevent

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractMachineInfo import AbstractMachineInfo


class LNLSMachineInfo(AbstractMachineInfo):
    """
    This class implements the beam current visualization for LNLS.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSMachineInfo.LNLSMachineInfo
    epics:
    "SI-Glob:AP-CurrInfo:Current-Mon":
        channels:
            current:
                suffix: ''
                polling_period: 200
    "SI-Glob:AP-CurrInfo:Lifetime-Mon":
        channels:
            lifetime:
                suffix: ''
                polling_period: 200
    "AS-Glob:AP-MachShift:Mode-Sts":
        channels:
            message:
                suffix: ''
                polling_period: 200
    "AS-Glob:AP-InjCtrl:Mode-Sel":
        channels:
            fill_mode:
                suffix: ''
                polling_period: 200
    configuration:
        parameters: '["current", "message", "lifetime", "fill_mode"]'
    """

    CURRENT_RBV = "current"
    MESSAGE_RBV = "message"
    LIFETIME_RBV = "lifetime"
    FILL_MODE_RBV = "fill_mode"

    def init(self):
        super().init()
        self._run()

    def _run(self):
        gevent.spawn(self._update_me)

    def _update_me(self):
        while True:
            gevent.sleep(5)
            values = {}
            values.update(self.get_value())
            self.update_value()

    def get_current(self) -> float:
        return self.get_channel_value(self.CURRENT_RBV)

    def get_message(self) -> str:
        mode_ring = self.get_channel_value(self.MESSAGE_RBV)
        if mode_ring == 0:
            return "Users"
        elif mode_ring == 1:
            return "Commissioning"
        elif mode_ring == 2:
            return "Conditioning"
        elif mode_ring == 3:
            return "Injection"
        elif mode_ring == 4:
            return "Machine Study"
        elif mode_ring == 5:
            return "Maintenance"
        elif mode_ring == 6:
            return "Standby"
        elif mode_ring == 7:
            return "Shutdown"
        elif mode_ring == 8:
            return "MachineStartup"
        elif mode_ring == 9:
            return "BLComissioning"
        return " --- "

    def get_lifetime(self) -> str:
        hour = int(self.get_channel_value(self.LIFETIME_RBV)/3600)
        minute = int(((hour * 60) % 60))
        hour_real = f"{hour}:{minute}"
        return hour_real

    def get_fill_mode(self) -> str:
        return self.get_channel_value(self.FILL_MODE_RBV)
