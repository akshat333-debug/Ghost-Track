#!/usr/bin/env python3
"""Fetch only EuRoC IMU + ground-truth CSVs (about 25 GB of zips would otherwise be needed).

Uses HTTP range reads: skips the .bag files, decompresses each inner sequence zip to a temp
file, extracts two CSVs, deletes the temp file. Bytes come from a Hugging Face copy because ETH
rate-limits bulk reads (HTTP 429); every member's CRC is first checked against the official ETH
directory, and zipfile verifies the CRC while reading, so the data is ETH's byte for byte.
"""
import pathlib
import shutil
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

ETH = "https://www.research-collection.ethz.ch/server/api/core/bitstreams/{}/content"
MIRROR = "https://huggingface.co/datasets/GlowBond/EuRoC_MAV_Dataset/resolve/main/{}.zip"
ARCHIVES = {
    "machine_hall": "7b2419c1-62b5-4714-b7f8-485e5fe3e5fe",
    "vicon_room1": "02ecda9a-298f-498b-970c-b7c44334d880",
    "vicon_room2": "ea12bc01-3677-4b4c-853d-87c7870b8c44",
}
WANTED = ("mav0/imu0/data.csv", "mav0/state_groundtruth_estimate0/data.csv")
ROOT = pathlib.Path(__file__).resolve().parent.parent / "research" / "data" / "euroc"
UA = {"User-Agent": "Mozilla/5.0 (research-dataset-fetch)"}
CHUNK = 32 << 20  # few large range requests: the ETH server rate-limits small ones


def get(url, start, end):
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                if r.status != 206:
                    raise RuntimeError(f"server ignored Range header (HTTP {r.status})")
                return r.read(), r.headers["Content-Range"]
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == 7:
                raise
            time.sleep(15 * (attempt + 1))
            print(f"  retry {attempt + 1}: {e}", flush=True)


class RangeFile:
    """Read-only seekable view of a URL, enough for zipfile."""

    def __init__(self, url):
        self.url, self.pos, self.buf, self.buf_at = url, 0, b"", 0
        self.size = int(get(url, 0, 0)[1].split("/")[1])

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def read(self, n=-1):
        n = self.size - self.pos if n is None or n < 0 else min(n, self.size - self.pos)
        if n <= 0:
            return b""
        at = self.pos - self.buf_at
        if not (0 <= at and at + n <= len(self.buf)):
            end = min(self.pos + max(n, CHUNK), self.size) - 1
            self.buf, _ = get(self.url, self.pos, end)
            self.buf_at, at = self.pos, 0
        self.pos += n
        return self.buf[at:at + n]


def fetch(archive, uuid):
    outer = zipfile.ZipFile(RangeFile(MIRROR.format(archive)))
    official = zipfile.ZipFile(RangeFile(ETH.format(uuid)))
    sig = lambda z: {i.filename: (i.CRC, i.file_size) for i in z.infolist() if i.filename.endswith(".zip")}
    if sig(outer) != sig(official):
        raise RuntimeError(f"{archive}: mirror does not match the official ETH archive")
    for info in outer.infolist():
        if not info.filename.endswith(".zip") or "/._" in info.filename:
            continue
        seq = pathlib.Path(info.filename).stem
        targets = [ROOT / seq / w for w in WANTED]
        if all(t.exists() and t.stat().st_size for t in targets):
            print(f"{seq}: already present", flush=True)
            continue
        print(f"{seq}: fetching {info.compress_size >> 20} MB", flush=True)
        with tempfile.NamedTemporaryFile(dir=ROOT, suffix=".tmp") as tmp:
            with outer.open(info) as src:  # CRC of the inner zip is checked on read
                shutil.copyfileobj(src, tmp, 1 << 20)
            tmp.flush()
            with zipfile.ZipFile(tmp.name) as inner:
                for w, t in zip(WANTED, targets):
                    t.parent.mkdir(parents=True, exist_ok=True)
                    t.write_bytes(inner.read(w))
        print(f"{seq}: done", flush=True)


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    for stale in ROOT.glob("*.tmp"):  # left behind if a previous run was killed
        stale.unlink()
    for name, uuid in ARCHIVES.items():
        fetch(name, uuid)
    found = sorted(p.name for p in ROOT.iterdir() if p.is_dir())
    assert len(found) == 11, found
    print("all 11 sequences:", found)
