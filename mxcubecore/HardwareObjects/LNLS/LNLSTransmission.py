import logging

from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSActuator import EPICSActuator
from mxcubecore.HardwareObjects.LNLS.set_transmission_mnc import (
    get_transmission,
    set_foils,
)
from mxcubecore.HardwareObjects.LNLS.get_transmission_mnc import compute_transmission

from mxcubecore import HardwareRepository as HWR

class LNLSTransmission(EPICSActuator):
    """
    Docstring here.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSTransmission.LNLSTransmission
    epics:
        "MNC:B:TRANSMISSION:":
            channels:
            rbv:
                suffix: "RBV"
                polling_period: 200
            val:
                suffix: "SET"
    configuration:
        tolerance: 0.5
        default_limits: (0, 100)
    """

    def __init__(self, name):
        super().__init__(name)
        self.unit = 1

    def _set_value(self, value):
        self.setpoint = value
        self.update_state(self.STATES.BUSY)
        try:
            energy = HWR.beamline.energy.get_value()
            transmission_setup = get_transmission(energy, value)
            user_transmission = round(transmission_setup[0] * 100, 2)
            actual_transmission = round(transmission_setup[1] * 100, 2)
            filter_combination = transmission_setup[2]
            logging.getLogger("HWR").info(f"Requested transmission: {user_transmission}")
            logging.getLogger("HWR").info(f"Closest possible value: {actual_transmission}")
            logging.getLogger("HWR").info(f"Filter combination: {filter_combination}")
            foil_status = set_foils(filter_combination)
            if foil_status == 0:
                logging.getLogger("HWR").info("Transmission successfully set")
            else:
                logging.getLogger("HWR").info("Error setting transmission: foil status not ok")
        except Exception as e:
            logging.getLogger("HWR").error(f"Error while setting transmission: {e}")

    def get_value(self):
        print("Getting transmission value")
        energy = HWR.beamline.energy.get_value()
        transmission, status = compute_transmission(energy)
        transmission = transmission * 100
        print(f"Value is {transmission}")
        print(f"Status is {status}")
        if status != 1:
            return transmission
        return -1