import logging

from mxcubeweb.app import MXCUBEApplication as frontendApplication

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract import AbstractSampleChanger
from mxcubecore.HardwareObjects.abstract.sample_changer import Container
from mxcubecore.HardwareObjects.LNLS.LNLSBeamlineActions import Mount
from mxcubecore.queue_entry.base_queue_entry import CENTRING_METHOD


class LNLSStaubli(AbstractSampleChanger.SampleChanger):
    """
    This class calls the mount and unmount actions and also handles the
    logic of which sample is mounted, which samples are in the queue, and
    which samples are accessible from the 'get samples from SC' button.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSStaubli.LNLSStaubli
    epics:
    "MNC:B:ROBCS801:":
        channels:
            get_loop:
                suffix: "GetLoop"
            puck_id_1:
                suffix: "PuckID1"
            puck_id_2:
                suffix: "PuckID2"
            puck_id_3:
                suffix: "PuckID3"
    "MNC:B:SoftIOC:SP:1:SampPres_RBV":
        channels:
            sample_present:
                suffix : ""
    configuration: {}
    """

    __TYPE__ = "Sample Changer"
    NO_OF_BASKETS = 3
    NO_OF_SAMPLES_IN_BASKET = 16

    def __init__(self, name):
        scannable = False
        super().__init__(self.__TYPE__, scannable, name)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")

    def init(self):
        self.frontend_application = frontendApplication
        self._selected_sample = -1
        self._selected_basket = -1
        self.previous_get_loop_value = 0
        self.sc_channels = self._CommandContainer__channels
        self.no_of_baskets = self.get_property(
            "no_of_baskets", LNLSStaubli.NO_OF_BASKETS
        )
        self.no_of_samples_in_basket = self.get_property(
            "no_of_samples_in_basket", LNLSStaubli.NO_OF_SAMPLES_IN_BASKET
        )
        for i in range(self.no_of_baskets):
            basket = Container.Basket(
                self, i + 1, samples_num=self.no_of_samples_in_basket
            )
            self._add_component(basket)
        self._init_sc_contents()
        AbstractSampleChanger.SampleChanger.init(self)
        self.log_filename = self.get_property("log_filename")
        self.mount_action = Mount()

    def get_log_filename(self):
        return self.log_filename

    def convert_to_sc_value(self, basket, sample):
        return ((int(basket) - 1) * 16) + int(sample)

    def load(self, sample, wait=False):  # noqa: FBT002, ARG002
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", True)  # noqa: FBT003
        previous_sample = self.get_loaded_sample()
        self._set_state(AbstractSampleChanger.SampleChangerState.Loading)
        self._reset_loaded_sample()
        if isinstance(sample, tuple):
            basket, sample = sample
        else:
            basket, sample = sample.split(":")
        self._selected_basket = basket = int(basket)
        self._selected_sample = sample = int(sample)
        msg = f"Loading sample {basket}:{sample}"
        logging.getLogger("user_level_log").info(
            f"Sample changer: {msg}. Please wait..."
        )
        self.emit("progressInit", (msg, 100))
        msg = {
            "signal": "loadingSample",
            "location": f"{basket}:{sample}",
            "message": "Please wait, loading sample",
        }
        self.frontend_application.server.emit("sc", msg, namespace="/hwr")
        set_loop_value = self.convert_to_sc_value(basket, sample)
        self.mount_action.mount(int(set_loop_value))
        if HWR.beamline.queue_manager.centring_method == CENTRING_METHOD.LOOP:
            self._bluesky_api.execute_plan(plan_name="automatic_alignment")
        self.emit("progressStep", 100)
        mounted_sample = self.get_component_by_address(
            Container.Pin.get_sample_address(basket, sample)
        )
        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)
        if mounted_sample is not previous_sample:
            self._trigger_loaded_sample_changed_event(mounted_sample)
        self.update_info()
        logging.getLogger("user_level_log").info("Sample changer: Sample loaded")
        self.emit("progressStop", ())
        self.emit("fsmConditionChanged", "sample_is_loaded", True)  # noqa: FBT003
        self.emit("fsmConditionChanged", "sample_mounting_sample_changer", False)  # noqa: FBT003
        return self.get_loaded_sample()

    def unload(self, sample_slot=None, wait=None):  # noqa: ARG002
        logging.getLogger("user_level_log").info("Unloading sample")
        sample = self.get_loaded_sample()
        self._set_state(AbstractSampleChanger.SampleChangerState.Unloading)
        self.mount_action.unmount()
        sample._set_loaded(False, True)  # noqa: SLF001, FBT003
        self._selected_basket = -1
        self._selected_sample = -1
        self._trigger_loaded_sample_changed_event(self.get_loaded_sample())
        self.emit("fsmConditionChanged", "sample_is_loaded", False)  # noqa: FBT003
        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)

    def index_to_sample_puck(self, index):
        sample = (index - 1) % 16 + 1
        puck = (index - 1) // 16 + 1
        self._selected_basket = puck
        self._selected_sample = sample

    def get_loaded_sample(self):
        get_loop = int(self.sc_channels["get_loop"].get_value())
        sample_present = self.sc_channels["sample_present"].get_value()
        if get_loop and sample_present and (1 <= get_loop <= 48):
            self.index_to_sample_puck(get_loop)
        else:
            self._selected_basket = -1
            self._selected_sample = -1
        value = self.get_component_by_address(
            Container.Pin.get_sample_address(
                self._selected_basket, self._selected_sample
            )
        )
        if get_loop != self.previous_get_loop_value:
            self.previous_get_loop_value = get_loop
            self._trigger_loaded_sample_changed_event(value)
        return value

    def get_name_from_address(self, address):
        puck = address.split(":")[0]
        name = self.sc_channels[f"puck_id_{puck}"].get_value()
        if name == "None":
            return None
        return f"{name}-{address}"

    def configure_baskets(self):
        for basket_index in range(self.no_of_baskets):
            basket = self.get_components()[basket_index]
            datamatrix = None
            present = (
                self.sc_channels[f"puck_id_{basket_index + 1}"].get_value() != "None"
            )
            scanned = False
            basket._set_info(present, datamatrix, scanned)  # noqa: SLF001

    def configure_samples(self):
        sample_list = []
        for basket_index in range(self.no_of_baskets):
            if self.sc_channels[f"puck_id_{basket_index + 1}"].get_value() == "None":
                continue
            for sample_index in range(self.no_of_samples_in_basket):
                sample_list.extend(
                    [
                        (
                            "",
                            basket_index + 1,
                            sample_index + 1,
                            1,
                            Container.Pin.STD_HOLDERLENGTH,
                        )
                    ]
                )
        for spl in sample_list:
            address = Container.Pin.get_sample_address(spl[1], spl[2])
            sample = self.get_component_by_address(address)
            sample_name = self.get_name_from_address(address)
            if sample_name is not None:
                sample._name = sample_name  # noqa: SLF001
            datamatrix = f"matr{spl[1]}_{spl[2]}"
            present = scanned = loaded = has_been_loaded = False
            sample._set_info(present, datamatrix, scanned)  # noqa: SLF001
            sample._set_loaded(loaded, has_been_loaded)  # noqa: SLF001
            sample._set_holder_length(spl[4])  # noqa: SLF001

    def _init_sc_contents(self):
        self.configure_baskets()
        self.configure_samples()
        self._set_state(AbstractSampleChanger.SampleChangerState.Ready)

    def get_sample_list(self):
        self.configure_baskets()
        self.configure_samples()
        return super().get_sample_list()
