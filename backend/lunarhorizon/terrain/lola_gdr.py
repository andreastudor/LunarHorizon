"""Citirea produselor polare LOLA GDR (PDS3, `LDEM_*S_*M.IMG` + `.LBL`) ca nivel îndepărtat (E09).

Valorile vin din eticheta PDS, nu din presupuneri: dimensiuni, tip de eșantion, `SCALING_FACTOR`,
`OFFSET` (raza sferei de referință), `MAP_SCALE`, centrul proiecției și cadrul
(`COORDINATE_SYSTEM_NAME`). Geometria pixelilor urmează `DSMAP_POLAR.CAT` al setului
`LRO-L-LOLA-4-GDR-V1.0`:

    X = (I - N/2 - 0.5)·MAP_SCALE,   Y = (J - N/2 - 0.5)·MAP_SCALE·NS,   NS = -1 la sud,
    LON = atan2(X, Y)

cu `I` eșantionul și `J` linia, numărate de la 1. Pentru coloana 0 (I = 1) și rândul 0 (J = 1)
rezultă `x_first = (0.5 - N/2)·s` și `y_first = (N/2 - 0.5)·s`, adică aceeași convenție ca
`core.projection.SouthPolarStereographic`. Produsele nu au valoare NoData declarată.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np

from lunarhorizon.core.conventions import FRAME_ME_DE421
from lunarhorizon.terrain.horizon import HeightGrid, HorizonInputError

# Cadrul declarat de etichetă și identificatorul intern corespunzător (aceeași realizare DE421).
DECLARED_FRAMES: Final[dict[str, str]] = {"MEAN EARTH/POLAR AXIS OF DE421": FRAME_ME_DE421}
_ASSIGNMENT = re.compile(r"^\s*(\^?[A-Z_]+)\s*=\s*(.+?)\s*$")


@dataclass(frozen=True)
class PdsPolarLabel:
    lines: int
    line_samples: int
    sample_bits: int
    sample_type: str
    scaling_factor: float
    offset_m: float
    map_scale_m: float
    center_latitude_deg: float
    center_longitude_deg: float
    a_axis_radius_m: float
    line_projection_offset: float
    sample_projection_offset: float
    coordinate_system_name: str
    maximum_latitude_deg: float
    projection_type: str


def _number(text: str) -> float:
    return float(text.split("<")[0].strip().strip('"'))


def read_label(path: Path) -> PdsPolarLabel:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="ascii", errors="replace").splitlines():
        match = _ASSIGNMENT.match(line)
        if match and match.group(1) not in values:
            values[match.group(1)] = match.group(2)

    def text(key: str) -> str:
        if key not in values:
            raise HorizonInputError(f"{path.name}: cheia {key} lipsește din etichetă")
        return values[key].strip().strip('"')

    return PdsPolarLabel(
        lines=int(_number(text("LINES"))),
        line_samples=int(_number(text("LINE_SAMPLES"))),
        sample_bits=int(_number(text("SAMPLE_BITS"))),
        sample_type=text("SAMPLE_TYPE"),
        scaling_factor=_number(text("SCALING_FACTOR")),
        offset_m=_number(text("OFFSET")),
        map_scale_m=_number(text("MAP_SCALE")),
        center_latitude_deg=_number(text("CENTER_LATITUDE")),
        center_longitude_deg=_number(text("CENTER_LONGITUDE")),
        a_axis_radius_m=_number(text("A_AXIS_RADIUS")) * 1000.0,
        line_projection_offset=_number(text("LINE_PROJECTION_OFFSET")),
        sample_projection_offset=_number(text("SAMPLE_PROJECTION_OFFSET")),
        coordinate_system_name=text("COORDINATE_SYSTEM_NAME"),
        maximum_latitude_deg=_number(text("MAXIMUM_LATITUDE")),
        projection_type=text("MAP_PROJECTION_TYPE"),
    )


def load_lola_polar_grid(
    label_path: Path, image_path: Path, product_id: str, sha256: str | None
) -> HeightGrid:
    """Nivelul îndepărtat, citit prin `memmap` (fără încărcarea întregului fișier în memorie)."""
    label = read_label(label_path)
    if label.projection_type != "POLAR STEREOGRAPHIC" or label.center_latitude_deg != -90.0:
        raise HorizonInputError(f"{label_path.name}: nu este o proiecție stereografică polară sud")
    if label.center_longitude_deg != 0.0:
        raise HorizonInputError(f"{label_path.name}: meridianul central diferit de 0°")
    if label.sample_type != "LSB_INTEGER" or label.sample_bits != 16:
        raise HorizonInputError(f"{label_path.name}: tip de eșantion neașteptat")
    if label.lines != label.line_samples:
        raise HorizonInputError(f"{label_path.name}: imaginea nu este pătrată")
    if abs(label.offset_m - label.a_axis_radius_m) > 1e-3:
        raise HorizonInputError(
            f"{label_path.name}: OFFSET ({label.offset_m} m) diferă de raza proiecției"
        )
    frame = DECLARED_FRAMES.get(label.coordinate_system_name)
    if frame is None:
        raise HorizonInputError(
            f"{label_path.name}: cadrul {label.coordinate_system_name!r} nu este acceptat"
        )
    size = label.lines
    expected_offset = size / 2.0 - 0.5
    if (
        label.line_projection_offset != expected_offset
        or label.sample_projection_offset != expected_offset
    ):
        raise HorizonInputError(f"{label_path.name}: originea proiecției nu este în centru")
    expected_bytes = size * size * 2
    if image_path.stat().st_size != expected_bytes:
        raise HorizonInputError(
            f"{image_path.name}: {image_path.stat().st_size} octeți, așteptat {expected_bytes}"
        )
    heights = np.memmap(image_path, dtype="<i2", mode="r", shape=(size, size))
    scale = label.map_scale_m
    return HeightGrid(
        product_id=product_id,
        role="far",
        frame_id=frame,
        reference_radius_m=round(label.offset_m, 3),
        resolution_m=scale,
        x_first_m=(0.5 - size / 2.0) * scale,
        y_first_m=(size / 2.0 - 0.5) * scale,
        heights=heights,
        scale=label.scaling_factor,
        sha256=sha256,
    )
