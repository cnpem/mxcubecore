#
#  Project name: MXCuBE
#  https://github.com/mxcube
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#   You should have received a copy of the GNU Lesser General Public License
#  along with MXCuBE. If not, see <http://www.gnu.org/licenses/>.

import logging
import random
import time

from gevent.event import AsyncResult

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.GenericDiffractometer import GenericDiffractometer


class LNLSDiffractometer(GenericDiffractometer):
    """
    Descript. :
    """

    def __init__(self, name):
        """
        Descript. :
        """
        GenericDiffractometer.__init__(self, name)

        # child object slots
        self.backlight = None
        self.backlightswitch = None
        self.beamstop_distance = None
        self.focus = None
        self.frontlight = None
        self.frontlightswitch = None
        self.phi = None
        self.phiy = None
        self.phiz = None
        self.sampx = None
        self.sampy = None

    def init(self):
        """
        Descript. :
        """
        # self.image_width = 100
        # self.image_height = 100

        GenericDiffractometer.init(self)
        # Bzoom: 1.86 um/pixel (or 0.00186 mm/pixel) at minimum zoom
        self.x_calib = self.get_property("x_calib", "")
        self.y_calib = self.get_property("y_calib", "")
        self.last_centred_position = self.get_property("last_centred_position", "")

        self.pixels_per_mm_x = 1.0 / self.x_calib
        self.pixels_per_mm_y = 1.0 / self.y_calib
        self.beam_position = self.get_property("beam_position", "")

        self.current_phase = GenericDiffractometer.PHASE_CENTRING

        self.cancel_centring_methods = {}
        self.current_motor_positions = {
            "phiy": self.get_property("current_motor_positions_phiy", ""),
            "sampx": self.get_property("current_motor_positions_sampx", ""),
            "sampy": self.get_property("current_motor_positions_sampy", ""),
            "zoom": self.get_property("current_motor_positions_zoom", ""),
            "focus": self.get_property("current_motor_positions_focus", ""),
            "phiz": self.get_property("current_motor_positions_phiz", ""),
            "phi": self.get_property("current_motor_positions_phi", ""),
            "kappa": self.get_property("current_motor_positions_kappa", ""),
            "kappa_phi": self.get_property("current_motor_positions_kappa_phi", ""),
        }

        self.current_state_dict = {}
        self.centring_status = {"valid": False}
        self.centring_time = self.get_property("centring_time", "")

        self.mount_mode = self.get_property("sample_mount_mode")
        if self.mount_mode is None:
            self.mount_mode = "manual"

        self.equipment_ready()

        self.connect(self.motor_hwobj_dict["phi"], "valueChanged", self.phi_motor_moved)
        self.connect(
            self.motor_hwobj_dict["phiy"], "valueChanged", self.phiy_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["phiz"], "valueChanged", self.phiz_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa"], "valueChanged", self.kappa_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["kappa_phi"],
            "valueChanged",
            self.kappa_phi_motor_moved,
        )
        self.connect(
            self.motor_hwobj_dict["sampx"], "valueChanged", self.sampx_motor_moved
        )
        self.connect(
            self.motor_hwobj_dict["sampy"], "valueChanged", self.sampy_motor_moved
        )

    def is_ready(self) -> bool:
        """
        Descript. :
        """
        return True

    def motor_positions_to_screen(self, centred_positions_dict):
        """
        Descript. :
        """
        return self.last_centred_position[0], self.last_centred_position[1]

    def phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["phi"] = pos
        self.emit("phiMotorMoved", pos)

    def phiy_motor_moved(self, pos):
        self.current_motor_positions["phiy"] = pos

    def phiz_motor_moved(self, pos):
        self.current_motor_positions["phiz"] = pos

    def sampx_motor_moved(self, pos):
        self.current_motor_positions["sampx"] = pos

    def sampy_motor_moved(self, pos):
        self.current_motor_positions["sampy"] = pos

    def kappa_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaMotorMoved", pos)

    def kappa_phi_motor_moved(self, pos):
        """
        Descript. :
        """
        self.current_motor_positions["kappa_phi"] = pos
        if time.time() - self.centring_time > 1.0:
            self.invalidate_centring()
        self.emit_diffractometer_moved()
        self.emit("kappaPhiMotorMoved", pos)

    def manual_centring(self):
        """
        Descript. :
        """
        print("Iniciando centragem manual...")
        for click in range(3):
            print(f"Aguardando clique do usuário ({click+1}/3)...")
            self.user_clicked_event = AsyncResult()
            x, y = self.user_clicked_event.get()
            print(f"Usuário clicou nas coordenadas: x={x}, y={y}")

            # go to beam
            print("Movendo para o feixe com as coordenadas clicadas.")
            res = self.move_to_beam(x, y)  # wait before continue
            print(f"Resultado do movimento para o feixe: {res}")

            if click < 2:
                print(f"Executando rotação relativa do motor phi em 90 graus (click={click})...")
                self.motor_hwobj_dict["phi"].set_value_relative(90)

        print(f"Salvando última posição centrada: x={x}, y={y}")
        self.last_centred_position[0] = x
        self.last_centred_position[1] = y

        print("Centragem manual finalizada.")
        return {}

    def automatic_centring(self):
        """Automatic centring procedure"""
        print("Iniciando centragem automática...")
        
        centred_pos_dir = self._get_random_centring_position()
        print(f"Posição centrada gerada automaticamente: {centred_pos_dir}")

        self.emit("newAutomaticCentringPoint", centred_pos_dir)
        print("Sinal 'newAutomaticCentringPoint' emitido.")

        return centred_pos_dir

    def move_to_beam(self, x, y, omega=None):
        """
        Descript. : function to create a centring point based on all motors
                    positions.
        """
        logging.getLogger("HWR").info("Moving to beam...")
        self.print_log(
            level="debug",
            msg=f"Initializing beam centering with beam at x={x}, y={y}...",
        )

        centred_pos_dir = self.calculate_move_to_beam_pos(x, y)

        self.print_log(level="debug", msg="Moving to beam...")
        self.move_to_motors_positions(centred_pos_dir, wait=True)

        logging.getLogger("HWR").info("Move to beam has finished...")
        return centred_pos_dir
