from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore.HardwareObjects.BeamlineActions import BeamlineActions


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
                "name": "Dry","command": "HardwareObjects.LNLS.LNLSBeamlineActions.Dry"
                },
                {
                "type": "controller",
                "name": "Home",
                "command": "HardwareObjects.LNLS.LNLSBeamlineActions.Home"
                },
                ]
    """


class SampleChangerAction:
    def __init__(self, movement_option):
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.sc = HWR.beamline.sample_changer
        self.movement_option = movement_option

    def __call__(self, *args, **kwargs):
        self.sc._set_state(AbstractSampleChanger.SampleChangerState.Moving)  # noqa: SLF001
        self._bluesky_api.execute_plan(
            plan_name="run_sample_changer_command",
            kwargs={"movement_option": self.movement_option, **kwargs},
        )
        self.sc._set_state(AbstractSampleChanger.SampleChangerState.Ready)  # noqa: SLF001
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
