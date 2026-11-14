"""Verify missing data and interpolation against a small synthetic raster."""

from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from lunarhorizon.terrain.sampling import sample_bilinear


def test_bilinear_nodata_zero_and_edges(tmp_path: Path) -> None:
    path = tmp_path / "synthetic_dem.tif"
    data = np.array([[0, 2, -9999], [4, 6, 8], [10, 12, np.nan]], dtype="float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=3,
        height=3,
        count=1,
        dtype="float32",
        nodata=-9999,
        transform=from_origin(0, 3, 1, 1),
    ) as ds:
        ds.write(data, 1)
    assert sample_bilinear(path, 0.5, 2.5) == 0.0
    assert sample_bilinear(path, 1.0, 2.0) == pytest.approx(3.0)
    assert sample_bilinear(path, 2.0, 2.0) is None
    assert sample_bilinear(path, 2.0, 1.0) is None
    assert sample_bilinear(path, 0.0, 3.0) is None
    assert sample_bilinear(path, -10.0, 1.0) is None
    with pytest.raises(ValueError):
        sample_bilinear(path, float("nan"), 1.0)
