"""Transmission control for MANACA using Beer-Lambert law."""

import argparse
from epics import PV
import math
import time


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e",
        "--energy",
        required=True,
        type=float,
        help="Energy of the x-ray beam [keV]",
    )
    return parser.parse_args()


def calculate_mu(energy):
    """Calculate MU for each material based on energy."""
    return {
        "Al": (78657.01011 * math.exp(-energy / 0.65969))
        + (6406.36151 * math.exp(-energy / 1.63268))
        + (492.29999 * math.exp(-energy / 4.42554))
        + 3.2588,
        "Ti": (28062.17632 * math.exp(-energy / 1.88062))
        + (6354120 * math.exp(-energy / 0.49973))
        + (2257.91488 * math.exp(-energy / 5.28296))
        + 17.4342,
        "Cu": (1147850000 * math.exp(-energy / 0.56933))
        + (2582.7593 * math.exp(-energy / 8.40671))
        + (30628.08291 * math.exp(-energy / 2.98937))
        + 22.4187,
        "Au": (42783.04258 * math.exp(-energy / 5.39244)) + 399.59714,
        "Zr": (11143.28458 * math.exp(-energy / 5.87029)) + 102.27474,
    }


def read_foils(mu_values):
    """Define foils properties and PVs."""
    return {
        "F1_Al": (
            8,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi11"),
            PV("MNC:B:RIO01:9425A:bi12"),
        ),
        "F2_Al": (
            10,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi10"),
            PV("MNC:B:RIO01:9425A:bi13"),
        ),
        "F3_Al": (
            20,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi9"),
            PV("MNC:B:RIO01:9425A:bi14"),
        ),
        "F4_Al": (
            80,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi8"),
            PV("MNC:B:RIO01:9425A:bi15"),
        ),
        "F5_Al": (
            160,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi7"),
            PV("MNC:B:RIO01:9425A:bi16"),
        ),
        "F6_Al": (
            320,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi6"),
            PV("MNC:B:RIO01:9425A:bi17"),
        ),
        "F7_Al": (
            800,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi5"),
            PV("MNC:B:RIO01:9425A:bi18"),
        ),
        "F8_Al": (
            1500,
            mu_values["Al"],
            PV("MNC:B:RIO01:9425A:bi4"),
            PV("MNC:B:RIO01:9425A:bi19"),
        ),
        "F9_Ti": (
            8,
            mu_values["Ti"],
            PV("MNC:B:RIO01:9425A:bi3"),
            PV("MNC:B:RIO01:9425A:bi20"),
        ),
        "F10_Cu": (
            10,
            mu_values["Cu"],
            PV("MNC:B:RIO01:9425A:bi2"),
            PV("MNC:B:RIO01:9425A:bi21"),
        ),
        "F11_Au": (
            5,
            mu_values["Au"],
            PV("MNC:B:RIO01:9425A:bi1"),
            PV("MNC:B:RIO01:9425A:bi22"),
        ),
        "F12_Zr": (
            25,
            mu_values["Zr"],
            PV("MNC:B:RIO01:9425A:bi0"),
            PV("MNC:B:RIO01:9425A:bi23"),
        ),
    }


def compute_transmission(energy):
    mu_values = calculate_mu(energy)
    foils = read_foils(mu_values)

    mu_x_total = 0.0
    status_flags = []

    for key, value in foils.items():
        thickness, mu, pv1, pv2 = value
        pv1_val = pv1.get()
        pv2_val = pv2.get()
        if key == "F7_Al":
            pv1_val = 1 - pv2_val

        status_flag = 0
        if pv1_val == 0 and pv2_val == 1:
            mu_x_total += (thickness * 1e-4) * mu
        elif pv1_val == pv2_val:
            status_flag = 1
            print(f"Error at {key}")
        status_flags.append(status_flag)

    transmission = math.exp(-mu_x_total)
    overall_status = 1 if any(status_flags) else 0

    return transmission, overall_status
