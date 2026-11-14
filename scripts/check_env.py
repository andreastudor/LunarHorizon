"""Verifică mediul de dezvoltare LunarHorizon și afișează versiunile.

Rulare (din rădăcina repository-ului, cu Python-ul din mediul virtual al backendului):
    backend\\.venv\\Scripts\\python scripts\\check_env.py      (Windows)
    backend/.venv/bin/python scripts/check_env.py           (Linux, macOS)

Codul de ieșire este 1 dacă lipsește o cerință obligatorie.
"""

import io
import shutil
import subprocess
import sys

REQUIRED_PYTHON = (3, 13)
REQUIRED_NODE_MAJOR = 26
# Drivere GDAL folosite la E05: GeoTIFF (PGDA), COG (rasterul de calcul), JPEG 2000 (LOLA GDR).
REQUIRED_RASTER_DRIVERS = ("GTiff", "COG", "JP2OpenJPEG")
INFO_RASTER_DRIVERS = ("PDS", "PDS4", "ISIS3")


def tool_version(name: str) -> str | None:
    path = shutil.which(name)
    if path is None:
        return None
    result = subprocess.run([path, "--version"], capture_output=True, text=True, check=False)
    return result.stdout.strip() or result.stderr.strip() or "?"


def main() -> int:
    # Consola Windows folosește adesea o pagină de cod fără „ș”/„ț”; nu lăsăm afișarea să oprească
    # verificarea. Cu PYTHONUTF8=1 sau o consolă UTF-8, diacriticele apar corect.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(errors="replace")
    problems: list[str] = []

    print(f"Python      {sys.version.split()[0]}  ({sys.executable})")
    if sys.version_info[:2] != REQUIRED_PYTHON:
        problems.append(f"Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} este necesar")

    try:
        import numpy
        import rasterio
        import spiceypy
    except ImportError as exc:
        problems.append(f"bibliotecă lipsă: {exc.name}")
    else:
        print(f"NumPy       {numpy.__version__}")
        print(f"SpiceyPy    {spiceypy.__version__}  (CSPICE {spiceypy.tkvrsn('TOOLKIT')})")
        print(
            f"Rasterio    {rasterio.__version__}  "
            f"(GDAL {rasterio.__gdal_version__}, PROJ {rasterio.__proj_version__})"
        )
        with rasterio.Env() as env:
            drivers = env.drivers()
        for name in REQUIRED_RASTER_DRIVERS + INFO_RASTER_DRIVERS:
            state = "da" if name in drivers else "nu"
            required = " (obligatoriu)" if name in REQUIRED_RASTER_DRIVERS else ""
            print(f"  driver {name:<12} {state}{required}")
            if name in REQUIRED_RASTER_DRIVERS and name not in drivers:
                problems.append(f"driverul GDAL {name} lipsește")

    node = tool_version("node")
    print(f"Node        {node or 'negăsit'}")
    if node is None:
        problems.append("Node.js nu este pe PATH")
    elif not node.lstrip("v").startswith(f"{REQUIRED_NODE_MAJOR}."):
        print(f"  atenție: proiectul folosește Node {REQUIRED_NODE_MAJOR} (vezi frontend/.nvmrc)")
    print(f"npm         {tool_version('npm') or 'negăsit'}")

    for name in ("gdalinfo", "docker", "gh"):
        print(f"{name:<11} {'prezent' if shutil.which(name) else 'absent'} (opțional)")

    if problems:
        print("\nProbleme:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nMediul îndeplinește cerințele etapei E01.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
