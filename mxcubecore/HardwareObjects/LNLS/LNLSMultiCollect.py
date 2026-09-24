import ast
import datetime
import json
import logging
import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor

import requests
from mxcubeweb.core.util.convertutils import to_camel
from prefect.artifacts import Artifact

from mxcubecore import HardwareRepository as HWR
from mxcubecore.BaseHardwareObjects import HardwareObject
from mxcubecore.HardwareObjects.abstract.AbstractMultiCollect import (
    AbstractMultiCollect,
)


class LNLSMultiCollect(AbstractMultiCollect, HardwareObject):
    """
    Class for data collection at LNLS.

    YAML Example
    ------------

    %YAML 1.2
    ---
    class: LNLS.LNLSMultiCollect.LNLSMultiCollect
    epics:
        "MNC:B:PILATUS4_4M:cam1:":
            channels:
            full_file_name:
                suffix: "FullFileName_RBV"
    configuration:
        auto_processing:
            program: []
    """

    def __init__(self, name):
        AbstractMultiCollect.__init__(self)
        HardwareObject.__init__(self, name)
        self._bluesky_api = HWR.beamline.get_object_by_role("bluesky")
        self.wavelength = HWR.beamline.get_object_by_role("wavelength")
        self.machine_info = HWR.beamline.get_object_by_role("machine_info")
        self.detector_distance = HWR.beamline.get_object_by_role("detector_distance")
        self._centring_status = None
        self.ready_event = None
        self.actual_frame_num = 0
        self.collection_id = None
        self.xds_directory = ""

    def init(self):
        self.emit("collectConnected", (True,))
        self.emit("collectReady", (True,))
        self.mx_collect_channels = self._CommandContainer__channels

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
        acquire_time = float(
            data_collect_parameters["oscillation_sequence"][0]["exposure_time"]
        )
        self._bluesky_api.execute_plan(
            plan_name="flyscan",
            kwargs={
                "start": start,
                "file_path": file_parameters["directory"],
                "file_name": file_name,
                "angle_increment": step_size,
                "acquire_time": acquire_time,
                "num_images": num_of_points,
                "snapshot_num": self.number_of_snapshots,
                "debug": True,
            },
        )

    def get_pxpmm(self):
        diffractometer = HWR.beamline.diffractometer
        zoom_enum = diffractometer.zoom.get_value()
        current_zoom = zoom_enum.name
        mm_per_pixel_x = diffractometer.zoom.get_property("mm_per_pixel_x")[
            current_zoom
        ]
        mm_per_pixel_y = diffractometer.zoom.get_property("mm_per_pixel_y")[
            current_zoom
        ]
        pixel_per_mm_x = round(1 / mm_per_pixel_x, 6)
        pixel_per_mm_y = round(1 / mm_per_pixel_y, 6)
        return [pixel_per_mm_x, pixel_per_mm_y]

    def get_grid_start_by_axis(self, selected_grid_dict, axis):
        diff_from_beam = (
            selected_grid_dict["screen_coord"][axis]
            - selected_grid_dict["beam_pos"][axis]
        )
        pxpmm = self.get_pxpmm()[axis]
        return diff_from_beam / pxpmm

    def get_grid_start_position(self, selected_grid_dict):
        diffractometer = HWR.beamline.diffractometer
        sampx = diffractometer.sampx.get_value()
        samp_y = diffractometer.sampy.get_value()

        grid_x = self.get_grid_start_by_axis(selected_grid_dict, 0)
        grid_y = -1 * self.get_grid_start_by_axis(selected_grid_dict, 1)

        start_x = sampx - grid_x
        start_y = samp_y - grid_y

        return start_x, start_y

    def get_grid_scan_data(self):
        grid_list = HWR.beamline.sample_view.get_grids()
        selected_grid_dict = None
        for grid in grid_list:
            grid_as_dict = grid.as_dict()
            if grid_as_dict["selected"]:
                grid_found_msg = "Found selected grid {}".format(grid_as_dict["name"])
                selected_grid_dict = grid_as_dict
                selected_grid = grid
                break
            else:
                print("Ignoring grid {}".format(grid_as_dict["id"]))

        if selected_grid_dict is None:
            grid_found_msg = "Found unselected grid {}".format(grid_as_dict["name"])
            logging.getLogger("HWR").info(grid_found_msg)
            selected_grid_dict = grid_list[0].as_dict()
            selected_grid = grid_list[0]

        start_x, start_y = self.get_grid_start_position(selected_grid_dict)
        width = selected_grid_dict["dx_mm"]
        height = selected_grid_dict["dy_mm"]
        steps_x = selected_grid_dict["steps_x"]
        steps_y = selected_grid_dict["steps_y"]

        return start_x, start_y, width, height, steps_x, steps_y, selected_grid

    def get_latest_artifact(self):
        os.environ["PREFECT_API_URL"] = "http://10.39.50.93:4200/api/"
        artifact = Artifact.get(key="dozor-output")
        return artifact.data

    def get_dozor_output():
    url = "http://10.31.71.16:5000/read_dozor_output"
    try:
        response = requests.get(url)
        response.raise_for_status()
        payload = response.json()
        data = payload.get('data')
        print("--- Dozor Output ---")
        print(data)
        return data
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch dozor output: {e}")
        return None

    def return_gridscan_processing_results(self, grid, start_x, start_y, width, height):
        num_cols = grid.num_cols
        num_rows = grid.num_rows
        step_size = round(width / num_cols, 3)
        grid_result = {"heatmap": {}}
        grid_result_x_ray_scanning = {"heatmap": {}}
        artifact_data = get_dozor_output()
        for row in range(num_rows):
            for col in range(num_cols):
                if row % 2 == 0:
                    frame = row * num_cols + col + 1
                    flat_index = frame - 1
                    print(
                        "row: ",
                        row,
                        ", col: ",
                        col,
                        ", frame: ",
                        frame,
                        "flat_index: ",
                        flat_index,
                    )
                else:
                    frame = (row + 1) * num_cols - col
                    flat_index = frame - 1
                    print(
                        "row: ",
                        row,
                        ", col: ",
                        col,
                        ", frame: ",
                        frame,
                        "flat_index: ",
                        flat_index,
                    )
                cell_id = str(row * num_cols + col + 1)
                score = 0
                normalized_score = 0
                if artifact_data[flat_index]:
                    if artifact_data[flat_index]["heat_map_intensity_norm"]:
                        normalized_score = artifact_data[flat_index][
                            "heat_map_intensity_norm"
                        ]
                        score = artifact_data[flat_index]["heat_map_intensity"]
                color = [normalized_score * 255, 0, 255 - normalized_score * 255]
                grid_result["heatmap"][cell_id] = [normalized_score, color]
                grid_result_x_ray_scanning["heatmap"][cell_id] = [
                    score,
                    normalized_score,
                ]
        shape = HWR.beamline.sample_view.get_shape(grid.id)
        shape.set_result(grid_result)
        shape.result_data_path = None
        shape_dict = to_camel(shape.as_dict())
        shape_dict["cellCountFun"] = "left-to-right"
        HWR.beamline.sample_view.emit("newGridResult", shape_dict)

    def gridscan_procedure(self, owner, data_collect_parameters):
        start_x, start_y, width, height, steps_x, steps_y, selected_grid = (
            self.get_grid_scan_data()
        )
        file_parameters = data_collect_parameters["fileinfo"]
        file_name = "%(prefix)s_%(run_number)04d" % file_parameters
        exp_time = float(
            data_collect_parameters["oscillation_sequence"][0]["exposure_time"]
        )
        start_angle = float(data_collect_parameters["oscillation_sequence"][0]["start"])
        oscillation_range = float(
            data_collect_parameters["oscillation_sequence"][0]["range"]
        )
        self._bluesky_api.execute_plan(
            plan_name="complete_grid_scan",
            kwargs={
                "start_x": start_x,
                "start_y": start_y,
                "width": width,
                "height": height,
                "num_rows": steps_y,
                "num_cols": steps_x,
                "file_path": file_parameters["directory"],
                "file_name": file_name,
                "start_angle": start_angle,
                "oscillation_range": oscillation_range,
                "acquire_time": exp_time,
                "debug": True,
                "processing_mode": "dozor",
            },
        )
        self.return_gridscan_processing_results(
            selected_grid, start_x, start_y, width, height
        )

    def helical_scan_procedure(self, owner, data_collect_parameters):
        cplist = []
        points = HWR.beamline.sample_view.get_points()
        for point in points:
            print(dir(point))
            cp = point.get_centred_positions()[0].as_dict()
            cplist.append(cp)
        logging.getLogger("HWR").info(f"\n{cplist}\n")
        logging.getLogger("HWR").info(f"\n{data_collect_parameters}\n")

    def get_master_full_file_name(self):
        encoded_value = self.mx_collect_channels["full_file_name"].get_value()
        full_file_name = encoded_value.astype(np.uint8).tobytes().decode('utf-8').rstrip('\x00')
        if not full_file_name.endswith("_master.h5"):
            full_file_name = '_data_'.join(full_file_name.split('_data_')[0:-1]) + "_master.h5"
        return full_file_name

    def perform_xlsx_request(self, data_collect_parameters):
        try:
            wl = round(self.wavelength.get_value(), 6)
            dd = round(self.detector_distance.get_value(), 6)
            bc = round(self.machine_info.get_current(), 6)
            cb = int(data_collect_parameters["fileinfo"]["run_number"])
            cb = f"{cb:04d}"
            file_abs_path = self.get_master_full_file_name()
            logging.getLogger("HWR").info(f"filename is {file_abs_path}")
            timeout_seconds = 3
            dataFromMxcube = data_collect_parameters
            additionalData = {
                "Collection Batch": cb,
                "Wavelength": wl,
                "Detector distance (mm)": dd,
                "Electric Current (mA)": bc,
                "Loop image": "",
                "Absolute Path": file_abs_path,
            }
            proposalId = (
                data_collect_parameters["fileinfo"]["directory"]
                .split("/proposals/")[1]
                .split("/")[0]
            )
            url = "http://10.39.50.105:5000/turn-mxcube-data-in-dict-to-proposal-xlsx"
            payload = {
                "proposalId": proposalId,
                "dataFromMxcube": dataFromMxcube,
                "additionalData": additionalData,
            }
            response = requests.post(url, json=payload, timeout=timeout_seconds)
            logging.getLogger("HWR").info(str(response.status_code))
            logging.getLogger("HWR").info(str(response.text))
            logging.getLogger("HWR").info(str(response.json()))
        except requests.exceptions.Timeout:
            logging.getLogger("HWR").info(
                "XLSX data saving timed out (collection will still happen)"
            )
        except Exception as e:
            logging.getLogger("HWR").info(f"Error trying to send info: {e}")
            logging.getLogger("HWR").info("Collection will still happen")

    def notify_adxv_server(self):
        file_abs_path = self.get_master_full_file_name()
        try:
            timeout_seconds = 2
            url = "http://10.31.74.56:5005/open"
            payload = {"path": file_abs_path}
            response = requests.post(url, json=payload, timeout=timeout_seconds)  # noqa: F841
        except requests.exceptions.Timeout:
            logging.getLogger("HWR").info(
                "adxv server notification timed out (collection will still happen)"
            )
        except Exception as e:
            logging.getLogger("HWR").info(f"Error trying to notify adxv server: {e}")

    def do_collect(self, owner, data_collect_parameters):
        experiment_type = data_collect_parameters["experiment_type"]
        if experiment_type == "OSC":
            self.flyscan_procedure(owner, data_collect_parameters)
            self.perform_xlsx_request(data_collect_parameters)
            self.notify_adxv_server()
        elif experiment_type == "Mesh":
            self.gridscan_procedure(owner, data_collect_parameters)
            self.notify_adxv_server()
        elif experiment_type == "Helical":
            self.helical_scan_procedure(owner, data_collect_parameters)
