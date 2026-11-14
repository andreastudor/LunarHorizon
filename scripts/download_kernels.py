"""Descarcă și verifică kernelurile SPICE din data/manifests/kernels.json.

Rulare din rădăcina repository-ului, cu Python-ul mediului virtual al backendului:
    backend\\.venv\\Scripts\\python scripts\\download_kernels.py            (descarcă ce lipsește)
    backend\\.venv\\Scripts\\python scripts\\download_kernels.py --verify   (fără rețea: verifică)

Pentru fiecare fișier: calculează SHA-256, MD5 și mărimea; le compară cu toate sumele așteptate din
manifest (publicate de sursă sau dintr-o descărcare independentă anterioară); dacă manifestul are
deja un SHA-256, fișierul descărcat trebuie să fie identic. Orice nepotrivire oprește scriptul
fără a modifica manifestul. Apoi calculează acoperirea fiecărui SPK, a fiecărui PCK binar și a
fiecărui profil. Fișierele se salvează în data/kernels/ (exclus din Git). Cu --verify, scriptul
nu folosește rețeaua și nu scrie nimic.
"""

import argparse
import json
import os
import sys
import tempfile
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import spiceypy  # noqa: E402

from lunarhorizon.astro.kernels import (  # noqa: E402
    DEFAULT_KERNEL_DIR,
    DEFAULT_MANIFEST_PATH,
    SPICE_LOCK,
    file_digests,
    pck_coverage,
    pck_frame_class_id,
    spk_coverage,
)
from lunarhorizon.contracts.export import dumps  # noqa: E402
from lunarhorizon.contracts.manifests import KernelManifest  # noqa: E402
from lunarhorizon.core.utc import canonical_utc, format_utc  # noqa: E402

USER_AGENT = "LunarHorizon-kernel-downloader/0.1"


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=300) as response:
        if response.status != 200:
            raise RuntimeError(f"{url}: HTTP {response.status}")
        handle, temporary = tempfile.mkstemp(dir=destination.parent, suffix=".part")
        try:
            with os.fdopen(handle, "wb") as stream:
                while block := response.read(1 << 20):
                    stream.write(block)
            os.replace(temporary, destination)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise


def _check(entry: dict[str, Any], sha256: str, md5: str) -> list[str]:
    problems = []
    if entry["sha256"] is not None and entry["sha256"] != sha256:
        problems.append(f"SHA-256 {sha256} diferă de manifest {entry['sha256']}")
    for expected in entry["expected_checksums"]:
        actual = sha256 if expected["algorithm"] == "sha256" else md5
        if actual != expected["value"]:
            problems.append(
                f"{expected['algorithm']} {actual} diferă de valoarea așteptată "
                f"{expected['value']} "
                f"({expected['kind']}: {expected['source']})"
            )
    return problems


def _iso_utc(et: float) -> str:
    return canonical_utc(f"{spiceypy.et2utc(et, 'ISOC', 3)}Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarcă și verifică kernelurile SPICE.")
    parser.add_argument("--verify", action="store_true", help="fără rețea; numai verificare")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--kernel-dir", type=Path, default=DEFAULT_KERNEL_DIR)
    args = parser.parse_args()

    manifest: dict[str, Any] = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries_by_name: dict[str, list[dict[str, Any]]] = {}
    for profile in manifest["profiles"]:
        for entry in profile["files"]:
            entries_by_name.setdefault(entry["filename"], []).append(entry)

    failures: list[str] = []
    for filename, entries in entries_by_name.items():
        first = entries[0]
        path = args.kernel_dir / filename
        if any(e["url"] != first["url"] for e in entries):
            failures.append(f"{filename}: URL-uri diferite în profiluri")
            continue
        local = file_digests(path) if path.is_file() else None
        downloaded = False
        if local is None or (first["sha256"] is not None and local[0] != first["sha256"]):
            if args.verify:
                failures.append(f"{filename}: lipsește local sau diferă de manifest")
                continue
            print(f"descarc {first['url']}")
            _download(first["url"], path)
            local = file_digests(path)
            downloaded = True
        sha256, md5, size = local
        problems = [p for e in entries for p in _check(e, sha256, md5)]
        if problems:
            failures.extend(f"{filename}: {p}" for p in dict.fromkeys(problems))
            continue
        checks = (
            ", ".join(f"{c['algorithm']} {c['kind']}" for c in first["expected_checksums"])
            or "nicio sumă de referință disponibilă"
        )
        print(f"ok {filename}: {size} octeți, sha256 {sha256[:16]}…; verificat față de: {checks}")
        for entry in entries:
            entry.update(sha256=sha256, md5=md5, size_bytes=size)
            if downloaded or entry["retrieved_at_utc"] is None:
                entry["retrieved_at_utc"] = format_utc(datetime.now(UTC))

    if failures:
        print("\nEȘEC — manifestul nu a fost modificat:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    with SPICE_LOCK:
        for profile in manifest["profiles"]:
            paths = [args.kernel_dir / e["filename"] for e in profile["files"]]
            spiceypy.kclear()
            for path in paths:
                spiceypy.furnsh(str(path))
            class_id = pck_frame_class_id(profile["pa_frame_id"])
            windows = []
            for entry, path in zip(profile["files"], paths, strict=True):
                if entry["role"] == "spk":
                    window = spk_coverage(path)
                elif entry["role"] == "binary_pck":
                    window = pck_coverage(path, class_id)
                else:
                    continue
                entry["coverage_start_utc"], entry["coverage_end_utc"] = map(_iso_utc, window)
                windows.append(window)
            start = max(w[0] for w in windows)
            end = min(w[1] for w in windows)
            profile["coverage_start_utc"], profile["coverage_end_utc"] = (
                _iso_utc(start),
                _iso_utc(end),
            )
            print(
                f"profil {profile['profile_id']}: acoperire "
                f"{profile['coverage_start_utc']} - {profile['coverage_end_utc']}"
            )
        spiceypy.kclear()

    validated = KernelManifest.model_validate_json(json.dumps(manifest))
    if args.verify:
        print("verificare reușită; manifestul nu a fost modificat")
        return 0
    args.manifest.write_text(
        dumps(validated.model_dump(mode="json")), encoding="utf-8", newline="\n"
    )
    print(f"manifest actualizat: {args.manifest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
