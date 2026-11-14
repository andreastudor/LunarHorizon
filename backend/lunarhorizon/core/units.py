"""Unități interne: grade, metri, secunde (docs/SPEC_FIZICA.md §1).

Conversiile de unghi sunt definite explicit (înmulțire cu o constantă), identic cu frontendul,
ca rezultatele să coincidă bit cu bit în cât mai multe cazuri.
"""

import math
from typing import Final

DEG_TO_RAD: Final = math.pi / 180.0
RAD_TO_DEG: Final = 180.0 / math.pi
M_PER_KM: Final = 1000.0


def deg_to_rad(angle_deg: float) -> float:
    return angle_deg * DEG_TO_RAD


def rad_to_deg(angle_rad: float) -> float:
    return angle_rad * RAD_TO_DEG


def km_to_m(length_km: float) -> float:
    return length_km * M_PER_KM


def m_to_km(length_m: float) -> float:
    return length_m / M_PER_KM
