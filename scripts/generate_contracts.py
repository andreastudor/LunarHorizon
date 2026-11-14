"""Generează schema JSON comună și vectorii de test Python ↔ TypeScript.

Rulare din rădăcina repository-ului, cu Python-ul mediului virtual al backendului:
    backend\\.venv\\Scripts\\python scripts\\generate_contracts.py           (scrie fișierele)
    backend\\.venv\\Scripts\\python scripts\\generate_contracts.py --check   (verifică, nu scrie)

După regenerarea schemei, tipurile TypeScript se regenerează din frontend/ cu
`npm run contracts:generate`.
"""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from lunarhorizon.contracts.export import build_schema, dumps  # noqa: E402
from lunarhorizon.core.reference_vectors import build_reference_vectors  # noqa: E402

OUTPUTS: dict[Path, Callable[[], Any]] = {
    ROOT / "data" / "schemas" / "lunarhorizon.schema.json": build_schema,
    ROOT / "tests" / "vectors" / "conventions.json": build_reference_vectors,
}


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generează schema JSON și vectorii de test.")
    parser.add_argument("--check", action="store_true", help="nu scrie; ieșire 1 dacă e învechit")
    args = parser.parse_args()

    stale: list[Path] = []
    for path, build in OUTPUTS.items():
        expected = dumps(build())
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current is not None and _normalized(current) == expected:
            continue
        stale.append(path)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8", newline="\n")
            print(f"scris: {path.relative_to(ROOT)}")

    if args.check and stale:
        for path in stale:
            print(f"învechit: {path.relative_to(ROOT)} (rulați scripts/generate_contracts.py)")
        return 1
    if not stale:
        print("Schema și vectorii sunt la zi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
