"""Profilurile de kerneluri SPICE: verificarea fișierelor, încărcarea și acoperirea temporală.

Un profil (data/manifests/kernels.json) se încarcă integral, în ordinea din manifest, după `kclear`.
Înaintea încărcării, fiecare fișier trebuie să existe local și să aibă SHA-256-ul din manifest.
Acoperirea profilului este intersecția acoperirilor SPK, pentru corpurile din lanțul de efemeride,
și PCK, pentru cadrul orientării lunare. Kernelul de secunde intercalare nu are acoperire proprie;
pentru momente viitoare, SPICE presupune că nu se adaugă secunde intercalare după ultima din kernel.
"""

import hashlib
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import spiceypy
from spiceypy.utils.support_types import SpiceCell

from lunarhorizon.contracts.manifests import KernelFile, KernelManifest, KernelProfile
from lunarhorizon.core.errors import ErrorCode, LunarHorizonError

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_PATH: Final = REPO_ROOT / "data" / "manifests" / "kernels.json"
DEFAULT_KERNEL_DIR: Final = REPO_ROOT / "data" / "kernels"

# SPICE (CSPICE) nu este sigur pentru fire de execuție: toate apelurile trec prin acest lacăt.
SPICE_LOCK: Final = threading.RLock()

# Lanțul de efemeride: Soare (10), baricentrul Pământ-Lună (3), Pământ (399), Lună (301).
SPK_BODIES: Final[tuple[int, ...]] = (10, 3, 399, 301)

_active_profile: "LoadedProfile | None" = None


@dataclass(frozen=True)
class LoadedProfile:
    profile_id: str
    frame_id: str
    pa_frame_id: str
    paths: tuple[Path, ...]
    sha256: tuple[str, ...]
    coverage_start_et: float
    coverage_end_et: float
    coverage_start_utc: str
    coverage_end_utc: str


def read_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> KernelManifest:
    return KernelManifest.model_validate_json(path.read_text(encoding="utf-8"))


def find_profile(manifest: KernelManifest, profile_id: str | None) -> KernelProfile:
    wanted = profile_id or manifest.default_profile
    for profile in manifest.profiles:
        if profile.profile_id == wanted:
            return profile
    raise LunarHorizonError(ErrorCode.KERNEL_MISSING, f"profilul {wanted!r} nu este în manifest")


def file_digests(path: Path) -> tuple[str, str, int]:
    """(sha256, md5, mărime în octeți), calculate pe conținutul fișierului."""
    sha256, md5, size = hashlib.sha256(), hashlib.md5(usedforsecurity=False), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            sha256.update(block)
            md5.update(block)
            size += len(block)
    return sha256.hexdigest(), md5.hexdigest(), size


def checked_path(kernel_file: KernelFile, kernel_dir: Path) -> Path:
    """Calea locală a unui kernel, după verificarea existenței și a SHA-256 din manifest."""
    path = kernel_dir / kernel_file.filename
    hint = "rulați scripts/download_kernels.py"
    if not path.is_file():
        raise LunarHorizonError(
            ErrorCode.KERNEL_MISSING, f"lipsește {kernel_file.filename} în {kernel_dir}; {hint}"
        )
    if kernel_file.sha256 is None:
        raise LunarHorizonError(
            ErrorCode.KERNEL_MISSING,
            f"manifestul nu are SHA-256 pentru {kernel_file.filename}; {hint}",
        )
    actual, _, _ = file_digests(path)
    if actual != kernel_file.sha256:
        raise LunarHorizonError(
            ErrorCode.KERNEL_MISSING,
            f"{kernel_file.filename}: SHA-256 local {actual} "
            f"diferă de manifest {kernel_file.sha256}",
        )
    return path


def _single_interval(window: SpiceCell, what: str) -> tuple[float, float]:
    count = spiceypy.wncard(window)
    if count != 1:
        raise LunarHorizonError(
            ErrorCode.KERNEL_MISSING,
            f"{what}: acoperirea are {count} intervale; este necesar exact un interval continuu",
        )
    start, end = spiceypy.wnfetd(window, 0)
    return float(start), float(end)


def spk_coverage(path: Path, bodies: tuple[int, ...] = SPK_BODIES) -> tuple[float, float]:
    """Intersecția acoperirilor SPK (ET) pentru corpurile cerute."""
    intervals = [
        _single_interval(spiceypy.spkcov(str(path), body), f"{path.name}, corp {body}")
        for body in bodies
    ]
    return max(i[0] for i in intervals), min(i[1] for i in intervals)


def pck_coverage(path: Path, frame_class_id: int) -> tuple[float, float]:
    return _single_interval(
        spiceypy.pckcov(str(path), frame_class_id), f"{path.name}, cadrul {frame_class_id}"
    )


def pck_frame_class_id(pa_frame_id: str) -> int:
    """ID-ul de clasă PCK al cadrului de orientare (de exemplu 31008 pentru MOON_PA_DE440)."""
    code = spiceypy.namfrm(pa_frame_id)
    if code == 0:
        raise LunarHorizonError(ErrorCode.KERNEL_MISSING, f"cadrul {pa_frame_id} nu este definit")
    _, frame_class, class_id = spiceypy.frinfo(code)[:3]
    if frame_class != 2:
        raise LunarHorizonError(ErrorCode.KERNEL_MISSING, f"{pa_frame_id} nu este un cadru PCK")
    return int(class_id)


def _furnsh_all(paths: tuple[Path, ...]) -> None:
    spiceypy.kclear()
    for path in paths:
        spiceypy.furnsh(str(path))


def load_profile(
    profile_id: str | None = None,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    kernel_dir: Path = DEFAULT_KERNEL_DIR,
) -> LoadedProfile:
    """Verifică și încarcă un profil; calculează acoperirea lui. Profilul devine cel activ."""
    global _active_profile
    profile = find_profile(read_manifest(manifest_path), profile_id)
    paths = tuple(checked_path(f, kernel_dir) for f in profile.files)
    with SPICE_LOCK:
        _furnsh_all(paths)
        if spiceypy.namfrm(profile.frame_id) == 0:
            raise LunarHorizonError(ErrorCode.KERNEL_MISSING, f"cadrul {profile.frame_id} lipsește")
        class_id = pck_frame_class_id(profile.pa_frame_id)
        windows = []
        for kernel_file, path in zip(profile.files, paths, strict=True):
            if kernel_file.role == "spk":
                windows.append(spk_coverage(path))
            elif kernel_file.role == "binary_pck":
                windows.append(pck_coverage(path, class_id))
        if not windows:
            raise LunarHorizonError(ErrorCode.KERNEL_MISSING, "profilul nu are SPK sau PCK binar")
        start, end = max(w[0] for w in windows), min(w[1] for w in windows)
        loaded = LoadedProfile(
            profile_id=profile.profile_id,
            frame_id=profile.frame_id,
            pa_frame_id=profile.pa_frame_id,
            paths=paths,
            sha256=tuple(f.sha256 or "" for f in profile.files),
            coverage_start_et=start,
            coverage_end_et=end,
            coverage_start_utc=_et_to_iso_utc(start),
            coverage_end_utc=_et_to_iso_utc(end),
        )
        _active_profile = loaded
    return loaded


def activate(profile: LoadedProfile) -> None:
    """Reîncarcă profilul dacă alt profil a fost încărcat între timp (fără a reverifica sumele)."""
    global _active_profile
    with SPICE_LOCK:
        if _active_profile is None or _active_profile.profile_id != profile.profile_id:
            _furnsh_all(profile.paths)
            _active_profile = profile


def _et_to_iso_utc(et: float) -> str:
    return f"{spiceypy.et2utc(et, 'ISOC', 3)}Z"
