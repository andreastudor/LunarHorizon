"""Inspect PGDA 78 GeoTIFF metadata and candidate pixels over HTTP (no full DEM download).

Run from the repository root with the backend Python environment. The report distinguishes
an extent hit from a valid data pixel; neither establishes horizon coverage or DEM accuracy.
"""

import hashlib
import json
import math
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.warp import transform
from rasterio.windows import Window

ROOT = Path(__file__).resolve().parents[1]
URL = "https://pgda.gsfc.nasa.gov/products/78"


def valid_elevation(pixel: Any) -> float | None:
    """Return a finite elevation only when the single pixel is unmasked."""
    if np.ma.getmaskarray(pixel)[0, 0]:
        return None
    value = float(pixel[0, 0])
    return value if math.isfinite(value) else None


def main() -> int:
    with urllib.request.urlopen(URL, timeout=45) as response:
        page = response.read()
    urls = sorted(set(re.findall(r'https[^"<> ]+surf\.tif', page.decode("utf-8"))))
    if not urls:
        raise ValueError("PGDA page contains no surface GeoTIFF links")
    catalog = json.loads((ROOT / "data/catalog/sites.json").read_text(encoding="utf-8"))
    candidates = [s for s in catalog["sites"] if s["id"] in ("im1_odysseus", "im2_athena")]
    if {s["id"] for s in candidates} != {"im1_odysseus", "im2_athena"} or len(candidates) != 2:
        raise ValueError("Catalog must contain both candidate sites exactly once")
    report: dict[str, Any] = {
        "checked_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_url": URL,
        "page_sha256": hashlib.sha256(page).hexdigest(),
        "catalog_sha256": hashlib.sha256(
            (ROOT / "data/catalog/sites.json").read_bytes()
        ).hexdigest(),
        "method": "GeoTIFF CRS, bounds and pixel read via HTTP Range; no full-file checksum",
        "frame_assumption": "Catalog lon/lat adopted in PGDA's MOON_ME DE421; no frame correction",
        "limitation": (
            "A valid point pixel does not prove sufficient terrain for a horizon calculation"
        ),
        "rasters": [],
    }
    failures = 0
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_TIMEOUT="30"):
        for url in urls:
            item: dict[str, Any] = {"url": url}
            try:
                with rasterio.open(url) as ds:
                    if ds.crs is None:
                        raise ValueError("Missing CRS")
                    item.update(
                        crs_wkt=ds.crs.to_wkt(),
                        bounds_m=list(ds.bounds),
                        resolution_m=list(ds.res),
                        width=ds.width,
                        height=ds.height,
                        nodata="NaN"
                        if ds.nodata is not None and math.isnan(ds.nodata)
                        else ds.nodata,
                        area_or_point=ds.tags().get("AREA_OR_POINT"),
                        candidates=[],
                    )
                    for site in candidates:
                        xs, ys = transform(
                            "+proj=longlat +R=1737400 +no_defs",
                            ds.crs,
                            [site["longitude_deg"]],
                            [site["latitude_deg"]],
                        )
                        row, col = ds.index(xs[0], ys[0])
                        inside = 0 <= row < ds.height and 0 <= col < ds.width
                        result: dict[str, Any] = {
                            "site_id": site["id"],
                            "x_m": xs[0],
                            "y_m": ys[0],
                            "inside_extent": inside,
                            "valid_pixel": None,
                            "elevation_m": None,
                        }
                        if inside:
                            pixel = ds.read(1, window=Window(col, row, 1, 1), masked=True)
                            elevation = valid_elevation(pixel)
                            result.update(valid_pixel=elevation is not None, elevation_m=elevation)
                        item["candidates"].append(result)
                print(url.split("/")[-2], item["candidates"], flush=True)
            except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
                item.pop("candidates", None)
                item["error"] = str(exc)
                failures += 1
                print(url, str(exc), flush=True)
            report["rasters"].append(item)
    report["failures"] = failures
    destination = ROOT / "data/catalog/pgda_coverage.json"
    destination.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
