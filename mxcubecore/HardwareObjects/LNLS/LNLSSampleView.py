import logging
import numpy as np
import gevent
import os
import glob
import cv2

from mxcubeweb.app import MXCUBEApplication as frontendApplication
from mxcubeweb.core.util.convertutils import to_camel

from mxcubecore import HardwareRepository as HWR
from mxcubecore.HardwareObjects.abstract.AbstractSampleChanger import SampleChangerState
from mxcubecore.HardwareObjects.SampleView import Grid, Point, SampleView, TwoDPoint


class LNLSSampleView(SampleView):
    def init(self):
        SampleView.init(self)
        self.user_level_log = logging.getLogger("user_level_log")
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.sc = HWR.beamline.get_object_by_role("sample_changer")
        self.READY_FOR_NEXT_CLICK = gevent.event.Event()
        self.x, self.y = None, None
        self.frontend_application = frontendApplication
        self.current_centring_method = None
        self.current_x_point = 540
        self.current_y_point = 612
        self.sc_channels = self._CommandContainer__channels
        self.crystal_detection_url = self.get_property("crystal_detection_url")

    def move_to_beam_bluesky(self, x, y, plan_name, step = -1):
        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        plan_kwargs = {
            "x_px": beam_pos[0] - x,
            "y_px": y - beam_pos[1],
        }
        if step != -1:
            plan_kwargs["step"] = step
        self._bluesky_api.execute_plan(
            plan_name=plan_name,
            kwargs=plan_kwargs
        )

    def move_to_beam(self, x, y):
        if self.sc.get_state() != SampleChangerState.Ready:
            return
        self.user_level_log.info("Moving to beam...")
        self.move_to_beam_bluesky(x, y, "move_to_beam")
        self.user_level_log.info("Move to beam has finished...")

    def start_centring(self, centring_method):
        self.current_centring_method = centring_method
        self.current_centring_procedure = centring_method
        self.emit("centringStarted", (centring_method))

    def finish_centring(self):
        self.centring_status["valid"] = True
        omega, phiy, phiz, sampx, sampy = self.get_current_diffractometer_positions()
        self.centring_status["motors"] = {
            "omega": omega,
            "phiy": phiy,
            "phiz": phiz,
            "sampx": sampx,
            "sampy": sampy,
        }
        self.emit("centringSuccessful", (self.current_centring_method, self.get_centring_status()))
        if self.current_centring_method == "Manual":
            self.shapes.clear()
            self.frontend_application.server.emit(
                "update_shapes", {"shapes": self.shapes}, namespace="/hwr"
            )
            self.frontend_application.server.emit("abort_centring", namespace="/hwr")
        self.current_centring_procedure = None
        self.current_centring_method = None

    def start_auto_centring(self):
        self.user_level_log.info("Initializing automatic sample alignment...")
        if self.current_centring_method is not None:
            self.user_level_log.info("Already centring")
            return
        self.start_centring("Automatic")
        self._bluesky_api.execute_plan(plan_name="automatic_alignment")
        self.user_level_log.info("Automatic sample alignment has finished...")
        self.finish_centring()

    def image_clicked(self, x, y):
        logging.getLogger("user_level_log").info(
            f"LNLS Centring click at x:{int(x)}, y:{int(y)}"
        )
        self.x = x
        self.y = y
        self.READY_FOR_NEXT_CLICK.set()

    def start_manual_centring(self, nb_click: int = 3):
        if self.sc.get_state() != SampleChangerState.Ready:
            return
        self.user_level_log.info("Initializing manual sample alignment...")
        if self.current_centring_method is not None:
            self.user_level_log.info("Already centring")
            return
        self.start_centring("Manual")
        for step in range(3):
            if self.current_centring_method is None:
                break
            self.READY_FOR_NEXT_CLICK.clear()
            self.READY_FOR_NEXT_CLICK.wait()
            if self.current_centring_method is None:
                break
            beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
            if (self.x is not None) and (self.y is not None):
                self.move_to_beam_bluesky(self.x, self.y, "manual_alignment", step)
                self.x = None
                self.y = None
        self.user_level_log.info("Manual sample alignment has finished...")
        self.frontend_application.server.emit("abort_centring", namespace="/hwr")
        self.finish_centring()

    def cancel_centring(self):
        if self.current_centring_procedure:
            self.current_centring_procedure = None
            self.READY_FOR_NEXT_CLICK.set()
        self.centring_failed()

    def reject_centring(self):
        self.centring_status["valid"] = False
        self.emit("centringAccepted", (False, self.get_centring_status()))

    def get_snapshot(self):
        return None

    def _wait_for_centring_finishes(self):
        return

    def get_current_diffractometer_positions(self):
        d = HWR.beamline.diffractometer
        omega = d.omega.get_value()
        phiy = d.phiy.get_value()
        phiz = d.phiz.get_value()
        sampx = d.sampx.get_value()
        sampy = d.sampy.get_value()
        return omega, phiy, phiz, sampx, sampy

    def get_current_mm_per_pixel(self):
        d = HWR.beamline.diffractometer
        zoom_enum = d.zoom.get_value()
        current_zoom = zoom_enum.name
        mm_per_pixel_x = d.zoom.get_property("mm_per_pixel_x")[current_zoom]
        mm_per_pixel_y = d.zoom.get_property("mm_per_pixel_y")[current_zoom]
        return mm_per_pixel_x, mm_per_pixel_y

    def get_centred_point_from_coord(self, x, y, return_by_names=None):
        omega, phiy, phiz, sampx, sampy = self.get_current_diffractometer_positions()

        beam_pos = HWR.beamline.beam.get_beam_position_on_screen()
        x_px = beam_pos[0] - x
        y_px = y - beam_pos[1]

        mm_per_pixel_x, mm_per_pixel_y = self.get_current_mm_per_pixel()

        sampx = sampx + x_px * mm_per_pixel_x
        sampy = sampy + y_px * mm_per_pixel_y

        return {
            "omega": omega,
            "phiy": phiy,
            "phiz": phiz,
            "sampx": sampx,
            "sampy": sampy,
        }

    def _update_shape_positions(self, *args, **kwargs):
        for shape in self.get_shapes():
            if (not isinstance(shape, Grid)) and (not isinstance(shape, Point)) and (not isinstance(shape, TwoDPoint)):
                shape.update_position(self.motor_positions_to_screen)
        self.emit("shapesChanged")

    def return_point_current_position(self, positions_dict: dict[str, float]) -> tuple[int, int]:
        return int(self.current_x_point), int(self.current_y_point)

    def update_points_from_beamline_action(self, *args, **kwargs):
        for shape in self.get_shapes():
            if isinstance(shape, Point):
                shape_dict = to_camel(shape.as_dict())
                current_point_position = shape_dict["screenCoord"]
                x = current_point_position[0]
                y = current_point_position[1]
                self.current_x_point = x
                self.current_y_point = y
                print("current_point_position: ", current_point_position)
                shape.update_position(self.return_point_current_position)
        self.emit("shapesChanged")

    def update_grid_positions(self, pixel_diff_x, pixel_diff_y):
        final_shape_dict = {}
        grid_list = self.get_grids()
        for grid in grid_list:
            shape = self.get_shape(grid.id)
            shape_dict = to_camel(shape.as_dict())
            previous_coord = shape_dict["screenCoord"]
            new_coord = [
                previous_coord[0] - pixel_diff_x,
                previous_coord[1] - pixel_diff_y,
            ]
            shape_dict["screenCoord"] = new_coord
            shape_dict["cellCountFun"] = "left-to-right"
            grid.update_from_dict({"screenCoord": new_coord})
            grid.screen_coord = new_coord
            final_shape_dict.update({grid.id: shape_dict})
            self.frontend_application.server.emit(
                "update_shapes", {"shapes": final_shape_dict}, namespace="/hwr"
            )
            self.emit("shapesChanged")

    def update_point_positions(self, pixel_diff_x, pixel_diff_y):
        points_list = self.get_points()
        for point in points_list:
            shape = self.get_shape(point.id)
            shape_dict = to_camel(shape.as_dict())
            previous_coord = shape_dict["screenCoord"]
            new_coord_tuple = (
                previous_coord[0] - pixel_diff_x,
                previous_coord[1] - pixel_diff_y,
            )
            shape.screen_coord = (new_coord_tuple)
        self.emit("shapesChanged")

    def get_raw_image(self):
        data = self.sc_channels["camera_raw_image"].get_value()
        data_np_array = np.array(data, dtype='uint8')
        height = self.camera.height
        width = self.camera.width
        shape = [height, width, 3]
        img = data_np_array.reshape(shape[0], shape[1], shape[2])
        img[:, :, [2, 0]] = img[:, :, [0, 2]]
        return img

    def _draw_labeled_marker(self, img, x, y, color, label, marker_size, font_scale, thickness):
        outline_color = (0, 0, 0)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.drawMarker(img, (x, y), outline_color, cv2.MARKER_CROSS,
                    marker_size, thickness + 2)
        cv2.drawMarker(img, (x, y), color, cv2.MARKER_CROSS,
                    marker_size, thickness)
        text_pos = (x + marker_size // 2 + 4, y - marker_size // 2)
        cv2.putText(img, label, text_pos, font, font_scale, outline_color,
                    thickness + 2, cv2.LINE_AA)
        cv2.putText(img, label, text_pos, font, font_scale, color,
                    thickness, cv2.LINE_AA)

    def save_png_with_point_labels(self, png_file_path, add_beam_center=False):
        raw_img = self.get_raw_image()
        img = raw_img.copy(order="C")
        h, w = img.shape[:2]
        point_color = (0, 255, 0)
        beam_color = (0, 0, 255)
        marker_size = max(12, w // 60)
        font_scale = max(0.5, w / 1600)
        thickness = max(1, w // 800)

        for point in self.get_points():
            shape = self.get_shape(point.id)
            shape_dict = to_camel(shape.as_dict())
            x, y = shape_dict["screenCoord"][:2]
            x, y = int(round(x)), int(round(y))
            point_number = int(shape_dict["id"].replace("2DP", ""))
            if not (0 <= x < w and 0 <= y < h):
                logging.getLogger("HWR").warning(
                    f"Point {point_number} at ({x}, {y}) is outside the image ({w}x{h})"
                )
                continue
            self._draw_labeled_marker(img, x, y, point_color, str(point_number),
                                    marker_size, font_scale, thickness)

        if add_beam_center:
            x, y = HWR.beamline.beam.get_beam_position_on_screen()
            self._draw_labeled_marker(img, x, y, beam_color, "beam", marker_size, font_scale, thickness)

        if not cv2.imwrite(png_file_path, img):
            raise IOError(f"Failed to write {png_file_path}")

    def save_points_and_snapshot_to_png(self):
        try:
            mxcollect = HWR.beamline.get_object_by_role('collect')
            session = HWR.beamline.get_object_by_role('session')
            sample_changer = HWR.beamline.get_object_by_role('sample_changer')

            base_image_directory = session.get_base_image_directory()
            multi_points_collections_dir = f"{base_image_directory}/multi_points_collections".replace("/data/", "/proc/")
            os.makedirs(multi_points_collections_dir, exist_ok=True)

            loaded_sample = sample_changer.get_loaded_sample()
            sample_name = loaded_sample.get_name()

            png_file_path_placeholder = f"{multi_points_collections_dir}/{sample_name}_run*"
            next_run_number = len(glob.glob(png_file_path_placeholder))
            run_folder = f"{multi_points_collections_dir}/{sample_name}_run{next_run_number}"
            os.makedirs(run_folder)

            points_snapshots_folder = f"{run_folder}/points_snapshots"
            os.makedirs(points_snapshots_folder)

            png_file_path = f"{run_folder}/{sample_name}.png"
            self.save_png_with_point_labels(png_file_path)

            json_file_path = f"{run_folder}/{sample_name}.json"

            return json_file_path, points_snapshots_folder

        except Exception:
            logging.getLogger("HWR").debug("save_points_and_snapshot_to_png failed", exc_info=True)
            return None, None
