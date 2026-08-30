"""Atomic, checksum-pinned LongMemEval dataset preparation.

The downloaded object is treated as data only. No upstream repository code is
executed and no benchmark dependency is installed by this module.
"""

import argparse
import hashlib
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import DATASET_SHA256, DATASET_URL


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_dataset(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"infrastructure failure: dataset is unavailable at {path}")
    actual = sha256_file(path)
    if actual != DATASET_SHA256:
        raise RuntimeError(
            "infrastructure failure: dataset checksum mismatch: "
            f"expected {DATASET_SHA256}, got {actual}"
        )
    return actual


def prepare_dataset(path: Path, retries: int = 3) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    if path.exists():
        return verify_dataset(path)
    last_error = None
    try:
        for attempt in range(1, retries + 1):
            try:
                request = urllib.request.Request(
                    DATASET_URL, headers={"User-Agent": "TESSERA-benchmark/1"}
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    with temporary.open("wb") as handle:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            handle.write(chunk)
                verify_dataset(temporary)
                temporary.replace(path)
                return verify_dataset(path)
            except (OSError, urllib.error.URLError, RuntimeError) as exc:
                last_error = exc
                temporary.unlink(missing_ok=True)
                if attempt < retries:
                    time.sleep(attempt)
        raise RuntimeError(
            f"infrastructure failure: unable to acquire pinned dataset after {retries} attempts: "
            f"{last_error}"
        )
    finally:
        temporary.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--verify-only", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checksum = (
        verify_dataset(args.dataset_path)
        if args.verify_only
        else prepare_dataset(args.dataset_path)
    )
    print(f"{checksum}  {args.dataset_path}")


if __name__ == "__main__":
    main()
