"""Strict bilinear sampling of DEMs in their projected coordinate system."""

import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window


def sample_bilinear(path: Path, x_m: float, y_m: float) -> float | None:
    """Return None for edges, missing pixels or NaN; zero remains a valid height."""
    if not math.isfinite(x_m) or not math.isfinite(y_m):
        raise ValueError("Coordonate nefinite")
    with rasterio.open(path) as ds:
        col, row = ~ds.transform @ (x_m, y_m)
        col -= 0.5
        row -= 0.5
        c0, r0 = math.floor(col), math.floor(row)
        if c0 < 0 or r0 < 0 or c0 + 1 >= ds.width or r0 + 1 >= ds.height:
            return None
        values = ds.read(1, window=Window(c0, r0, 2, 2), masked=True)
        if np.ma.getmaskarray(values).any() or not np.isfinite(values.data).all():
            return None
        dx, dy = col - c0, row - r0
        result = (
            values.data[0, 0] * (1 - dx) * (1 - dy)
            + values.data[0, 1] * dx * (1 - dy)
            + values.data[1, 0] * (1 - dx) * dy
            + values.data[1, 1] * dx * dy
        )
        return float(result)
