"""Teste de fum (E01): mediul Python are bibliotecile și driverele cerute de etapele următoare."""

import sys

import numpy as np
import rasterio
import spiceypy

import lunarhorizon

# Drivere GDAL necesare la E05: GeoTIFF (PGDA), COG (raster de calcul), JPEG 2000 (LOLA GDR).
REQUIRED_RASTER_DRIVERS = ("GTiff", "COG", "JP2OpenJPEG")


def test_python_version_is_project_version() -> None:
    assert sys.version_info[:2] == (3, 13)


def test_package_version() -> None:
    assert lunarhorizon.__version__ == "0.1.0"


def test_numpy_uses_float64_by_default() -> None:
    assert np.zeros(1).dtype == np.float64


def test_spice_toolkit_available() -> None:
    # Nu încarcă niciun kernel; verifică doar că biblioteca CSPICE este legată.
    assert spiceypy.tkvrsn("TOOLKIT").startswith("CSPICE_")


def test_required_raster_drivers_available() -> None:
    with rasterio.Env() as env:
        drivers = env.drivers()
    missing = [name for name in REQUIRED_RASTER_DRIVERS if name not in drivers]
    assert not missing, f"Drivere GDAL lipsă: {missing}"
