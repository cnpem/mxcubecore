from mxcubecore.HardwareObjects.abstract.AbstractEnergy import AbstractEnergy
from mxcubecore import HardwareRepository as HWR

class LNLSEnergy(AbstractEnergy):
    def __init__(self, name):
        AbstractEnergy.__init__(self, name)
        self.energy_actuator = HWR.beamline.get_object_by_role("energy_actuator")

    def get_value(self):
        value = self.energy_actuator.get_value()
        return value