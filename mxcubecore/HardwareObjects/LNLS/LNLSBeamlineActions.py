from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore.HardwareObjects.BeamlineActions import BeamlineActions
from mxcubecore.BaseHardwareObjects import HardwareObjectState


class LNLSBeamlineActions(BeamlineActions):
    """
    This class allows sample changer actions to be accessible from other classes
    of mxcubecore or from the 'Beamline Ations' options at frontend. To use it
    at mxcubecore code:

    from mxcubecore.HardwareObjects.LNLS.LNLSBeamlineActions import Mount
    mount = Mount()
    mount.mount(1)

    To implement a button that performs these actions at 'Beamline Actions',
    implement the command at the yaml file.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSBeamlineActions.LNLSBeamlineActions
    configuration:
    commands: [{
                "type": "controller",
                "name": "Soak",
                "command": "HardwareObjects.LNLS.LNLSBeamlineActions.Soak"
                },
                {
                "type": "controller",
                "name": "Dry",
                "command": "HardwareObjects.LNLS.LNLSBeamlineActions.Dry"
                },
                {
                "type": "controller",
                "name": "Home",
                "command": "HardwareObjects.LNLS.LNLSBeamlineActions.Home"
                },
                ]
    """
    def __init__(self, name):
        super().__init__(name)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.sc = HWR.beamline.get_object_by_role("sample_changer")
        self.diffractometer = HWR.beamline.get_object_by_role("diffractometer")
        self.STATES = HardwareObjectState

    def update_diffractometer_states(self, state_value):
        self.diffractometer.backlight.update_state(state_value)
        self.diffractometer.backlightswitch.update_state(state_value)
        self.diffractometer.frontlight.update_state(state_value)
        self.diffractometer.frontlightswitch.update_state(state_value)
        if not self.diffractometer.kappa.check_is_absent():
            self.diffractometer.kappa.update_state(state_value)
        if not self.diffractometer.kappa_phi.check_is_absent():
            self.diffractometer.kappa_phi.update_state(state_value)
        self.diffractometer.omega.update_state(state_value)
        self.diffractometer.phiy.update_state(state_value)
        self.diffractometer.phiz.update_state(state_value)
        self.diffractometer.sampx.update_state(state_value)
        self.diffractometer.sampy.update_state(state_value)
        self.diffractometer.sampz.update_state(state_value)

    def abort_command(self, cmd_name):
        self.sc._set_state(AbstractSampleChanger.SampleChangerState.Ready)  # noqa: SLF001
        self.update_diffractometer_states(self.STATES.READY)



class SampleChangerAction:
    def __init__(self, movement_option):
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.movement_option = movement_option
        self.sc = HWR.beamline.get_object_by_role("sample_changer")
        self.diffractometer = HWR.beamline.get_object_by_role("diffractometer")
        self.STATES = HardwareObjectState

    def update_diffractometer_states(self, state_value):
        self.diffractometer.backlight.update_state(state_value)
        self.diffractometer.backlightswitch.update_state(state_value)
        self.diffractometer.frontlight.update_state(state_value)
        self.diffractometer.frontlightswitch.update_state(state_value)
        if not self.diffractometer.kappa.check_is_absent():
            self.diffractometer.kappa.update_state(state_value)
        if not self.diffractometer.kappa_phi.check_is_absent():
            self.diffractometer.kappa_phi.update_state(state_value)
        self.diffractometer.omega.update_state(state_value)
        self.diffractometer.phiy.update_state(state_value)
        self.diffractometer.phiz.update_state(state_value)
        self.diffractometer.sampx.update_state(state_value)
        self.diffractometer.sampy.update_state(state_value)
        self.diffractometer.sampz.update_state(state_value)

    def __call__(self, *args, **kwargs):
        self.update_diffractometer_states(self.STATES.OFF)
        self.sc._set_state(AbstractSampleChanger.SampleChangerState.Moving)  # noqa: SLF001
        self._bluesky_api.execute_plan(
            plan_name="run_sample_changer_command",
            kwargs={"movement_option": self.movement_option, **kwargs},
        )
        self.sc._set_state(AbstractSampleChanger.SampleChangerState.Ready)  # noqa: SLF001
        self.update_diffractometer_states(self.STATES.READY)
        return args


class Soak(SampleChangerAction):
    def __init__(self):
        super().__init__("soak")


class Home(SampleChangerAction):
    def __init__(self):
        super().__init__("home")


class Dry(SampleChangerAction):
    def __init__(self):
        super().__init__("dry")


class Mount(SampleChangerAction):
    def __init__(self):
        super().__init__("mount")

    def mount(self, sample_value):
        return self(sample_value=sample_value)

    def unmount(self):
        self.movement_option = "unmount"
        return self()
