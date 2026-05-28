import logging
from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractMultiCollect import AbstractMultiCollect


class LNLSMultiCollect(AbstractMultiCollect, HardwareObject):
    def __init__(self, name):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self._centring_status = None
        self.ready_event = None
        self.actual_frame_num = 0
        self.collection_id = None
        self.xds_directory = ""

    def init(self):
        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))

    def flyscan_procedure(self, owner, data_collect_parameters):
        data_collect_parameters["status"] = "Data collection successful"
        file_parameters = data_collect_parameters["fileinfo"]
        file_name = "%(prefix)s_%(run_number)04d" % file_parameters
        start = float(
            data_collect_parameters["oscillation_sequence"][0]["start"]
        )  # omega start pos
        step_size = float(data_collect_parameters["oscillation_sequence"][0]["range"])
        num_of_points = int(
            data_collect_parameters["oscillation_sequence"][0]["number_of_images"]
        )
        end = start + step_size * num_of_points
        acquire_time = float(
            data_collect_parameters["oscillation_sequence"][0]["exposure_time"]
        )
        self._bluesky_api.execute_plan(
            plan_name="flyscan",
            kwargs={
                "start": start,
                "end": end,
                "file_path": file_parameters["directory"],
                "file_name": file_name,
                "angle_increment": step_size,
                "acquire_time": acquire_time,
                "num_images": num_of_points,
                "snapshot_num": self.number_of_snapshots
            },
        )

    def get_grid_start_by_axis(self, selected_grid, axis):
        diff_from_beam = selected_grid["screen_coord"][axis] - selected_grid["beam_pos"][axis]
        pxpmm = selected_grid["pixels_per_mm"][axis]
        return (diff_from_beam / pxpmm)

    def get_grid_start_position(self, selected_grid):
        diffractometer = HWR.beamline.diffractometer
        sampx = diffractometer.sampx.get_value()
        samp_y = diffractometer.sampy.get_value()

        grid_x = self.get_grid_start_by_axis(selected_grid, 0)
        grid_y = -1 * self.get_grid_start_by_axis(selected_grid, 1)

        start_x = sampx - grid_x
        start_y = samp_y - grid_y

        return start_x, start_y

    def get_grid_scan_data(self):
        grid_list = HWR.beamline.sample_view.get_grids()
        selected_grid = None
        for grid in grid_list:
            grid_as_dict = grid.as_dict()
            if grid_as_dict["selected"]:
                grid_found_msg = "Found selected grid {}".format(grid_as_dict["name"])
                selected_grid = grid_as_dict
                break
            else:
                print("Ignoring grid {}".format(grid_as_dict["id"]))

        if selected_grid is None:
            grid_found_msg = "Found unselected grid {}".format(grid_as_dict["name"])
            logging.getLogger("HWR").info(grid_found_msg)
            selected_grid = grid_list[0].as_dict()
        start_x, start_y = self.get_grid_start_position(selected_grid)
        width = selected_grid["dx_mm"]
        height = selected_grid["dy_mm"]
        steps_x = selected_grid["steps_x"]
        steps_y = selected_grid["steps_y"]

        return start_x, start_y, width, height, steps_x, steps_y

    def gridscan_procedure(self, owner, data_collect_parameters):
        start_x, start_y, end_x, end_y, step_x, step_y = self.get_grid_scan_data()
        width = abs(round(end_x - start_x, 6))
        height = abs(round(end_y - start_y, 6))
        file_parameters = data_collect_parameters["fileinfo"]
        file_name = "%(prefix)s_%(run_number)04d" % file_parameters
        exp_time = float(
            data_collect_parameters["oscillation_sequence"][0]["exposure_time"]
        )
        start_angle = float(data_collect_parameters["oscillation_sequence"][0]["start"])
        angle_increment = float(
            data_collect_parameters["oscillation_sequence"][0]["range"]
        )
        self._bluesky_api.execute_plan(
            plan_name="complete_grid_scan",
            kwargs={
                "start_x": start_x,
                "start_y": start_y,
                "width": width,
                "height": height,
                "num_rows": step_x,
                "num_cols": step_y,
                "file_path": file_parameters["directory"],
                "file_name": file_name,
                "start_angle": start_angle,
                "angle_increment": angle_increment,
                "acquire_time": exp_time,
                "num_images": 1  # One image per grid, because there is no oscillation at gridscan
            },
        )

    def do_collect(self, owner, data_collect_parameters):
        if data_collect_parameters["experiment_type"] == "OSC":
            self.flyscan_procedure(owner, data_collect_parameters)
        elif data_collect_parameters["experiment_type"] == "Mesh":
            self.gridscan_procedure(owner, data_collect_parameters)