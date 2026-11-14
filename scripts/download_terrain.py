"""Retrieve the published PGDA 104 elevation member using HTTP byte ranges.

The ZIP member's published-in-archive CRC is checked by zipfile; SHA-256 is pinned
separately after the first acquisition. This does not verify the full archive MD5.
"""

import argparse
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

URL = "https://zenodo.org/records/17954508/files/A3CLR22_10_Leibnitz_Beta_Plateau.zip?download=1"
SIZE = 1050441742
MEMBER = "A3CLR22_10_Leibnitz_Beta_Plateau/A310_GLDELEV_005.tif"
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/_raw/pgda104/A310_GLDELEV_005.tif"
EXPECTED_SHA256 = "55352520c0277a902a89fbd003f83956b238e4d0b4529494eaec1b5a51b1a4b1"


class RangeReader(io.RawIOBase):
    def __init__(self, url: str, size: int) -> None:
        self.url, self.size, self.position = url, size, 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = 0) -> int:
        self.position = (
            offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        )
        return self.position

    def read(self, size: int = -1) -> bytes:
        size = self.size - self.position if size < 0 else size
        if size == 0 or self.position >= self.size:
            return b""
        end = min(self.position + size, self.size) - 1
        request = urllib.request.Request(
            self.url, headers={"Range": f"bytes={self.position}-{end}"}
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 206:
                raise ValueError("Serverul nu a respectat cererea HTTP Range")
            if response.headers.get("Content-Range") != f"bytes {self.position}-{end}/{self.size}":
                raise ValueError("Content-Range nu corespunde cererii")
            data: bytes = response.read()
        if len(data) != end - self.position + 1:
            raise ValueError("Răspuns HTTP Range incomplet")
        self.position += len(data)
        return data


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.verify and not DEST.exists():
        DEST.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(RangeReader(URL, SIZE)) as archive:
            data = archive.read(MEMBER)  # CRC is verified before writing.
        digest = hashlib.sha256(data).hexdigest()
        if EXPECTED_SHA256 and digest != EXPECTED_SHA256:
            raise ValueError("SHA-256 diferit de referința locală")
        DEST.write_bytes(data)
    digest = sha256(DEST)
    print(f"{DEST}: SHA-256 {digest}")
    if EXPECTED_SHA256 and digest != EXPECTED_SHA256:
        raise ValueError("SHA-256 diferit de referința locală")


if __name__ == "__main__":
    main()
