from mxcubecore.HardwareObjects.LNLS.EPICS.EPICSMotor import EPICSMotor
from mxcubecore import HardwareRepository as HWR
import logging
from math import (
    asin,
    atan,
    sin,
    tan,
)


class ResolutionVirtualMotor(EPICSMotor):
    """
    This class implements the resolution virtual motor.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSResolution.ResolutionVirtualMotor
    epics:
    "MNC:B:PB04:CS1:m9":
        channels:
        "":
    "MX2:cam1:BeamX":
        channels:
        beam_x:
            suffix: ""
            polling_period: 200
    "MX2:cam1:BeamY":
        channels:
        beam_y:
            suffix: ""
            polling_period: 200
    configuration:
    tolerance: 0.01
    pixel_size_mm: 0.172
    n_pixels_x: 1475
    n_pixels_y: 1679
    """
    BEAM_X_RBV = "beam_x"
    BEAM_Y_RBV = "beam_y"

    def __init__(self,  name: str):
        super().__init__(name)
        self.wavelength = HWR.beamline.get_object_by_role("wavelength")

    def init(self):
        self.pixel_size_mm = self.get_property("pixel_size_mm")
        self.n_pixels_x = self.get_property("n_pixels_x")
        self.n_pixels_y = self.get_property("n_pixels_y")
        self.dx = self.n_pixels_x  * self.pixel_size_mm
        self.dy = self.n_pixels_y  * self.pixel_size_mm
        super().init()

    def get_limits(self):
        llm = self.get_channel_value(self.MOTOR_LLM)
        hlm = self.get_channel_value(self.MOTOR_HLM)
        low_limit = self.distance_to_resolution(llm)
        high_limit = self.distance_to_resolution(hlm)
        return (low_limit, high_limit)

    def get_radius(self):
        distance = self.get_channel_value("rbv")
        beam_x = self.get_channel_value(self.BEAM_X_RBV) * self.pixel_size_mm
        radius_x = min(beam_x, self.dx - beam_x)
        beam_y = self.get_channel_value(self.BEAM_Y_RBV) * self.pixel_size_mm
        radius_y = min(beam_y, self.dy - beam_y)
        return min(radius_x, radius_y)

    def distance_to_resolution(self, distance):
        wavelength = self.wavelength.get_value()
        radius = self.get_radius()
        try:
            two_theta = atan(radius / distance)
            theta = two_theta / 2
            return wavelength / (2 * sin(theta))
        except Exception as e:
            msg = f"Error converting distance to resolution: {e}"
            self.print_log(level="error", msg=msg)
            return None

    def resolution_to_distance(self, resolution):
        wavelength = self.wavelength.get_value()
        radius = self.get_radius()
        try:
            theta = asin(wavelength / (2 * resolution))
            two_theta = 2 * theta
            distance = radius / tan(two_theta)
            return distance
        except Exception as e:
            msg = f"Error converting resolution to distance: {e}"
            self.print_log(level="error", msg=msg)
            return None

    def get_value(self):
        distance = super().get_value()
        return self.distance_to_resolution(distance)

    def update_value(self, value=None) -> None:
        value = self.get_value()
        super().update_value(value)

    def _set_value(self, value):
        resolution = value
        distance = self.resolution_to_distance(resolution)
        if distance is not None:
            super()._set_value(distance)
