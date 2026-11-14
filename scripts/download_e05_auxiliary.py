"""Download only the selected PGDA quality members and NASA global texture."""

import hashlib
import urllib.request
import zipfile
from pathlib import Path

from download_terrain import ROOT, SIZE, URL, RangeReader

QUALITY = {
    "A310_GLDMASK_005.tif": "250776ca6d02497942d6b5f6a686057f0cdfa503f33855ce49011e7224aaaa09",
    "A310_GLDSIGM_005.tif": "ad03d88d10a8eaecc8a3a4ba8e4528bdd4a5c896b2aada6aec09f6e8017cfaa7",
    "A310_GLDSBCT_005.tif": "71b1e143a604434b9994caf7c01ef89c756f471dbde1b50f73e58599f904241d",
}
IMAGE_URL = "https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/lroc_color_2k.jpg"
IMAGE_SHA256 = "f7130a1822681fa7512d7dcfd40db8c10b9ba4f06777910348698260ed7a2170"


def verify_or_write(path: Path, data: bytes, expected: str) -> None:
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"Sumă incorectă: {path}")
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Fișier local diferit: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    quality_dir = ROOT / "data/_raw/pgda104"
    pending = [name for name in QUALITY if not (quality_dir / name).exists()]
    for name in QUALITY:
        path = quality_dir / name
        if path.exists():
            verify_or_write(path, path.read_bytes(), QUALITY[name])
    if pending:
        with zipfile.ZipFile(RangeReader(URL, SIZE)) as archive:
            for name in pending:
                member = "A3CLR22_10_Leibnitz_Beta_Plateau/" + name
                verify_or_write(quality_dir / name, archive.read(member), QUALITY[name])
    image = ROOT / "data/_raw/basemaps/lroc_color_2k.jpg"
    if image.exists():
        verify_or_write(image, image.read_bytes(), IMAGE_SHA256)
    else:
        with urllib.request.urlopen(IMAGE_URL, timeout=120) as response:
            verify_or_write(image, response.read(), IMAGE_SHA256)
    print("Produsele auxiliare și textura au SHA-256 verificat.")


if __name__ == "__main__":
    main()
