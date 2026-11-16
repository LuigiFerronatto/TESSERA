"""Original invented fixture; no official content, captions or model output."""

import binascii
import hashlib
from pathlib import Path
import struct
import zlib

from .contracts import UnsupportedProtocol


def image_bytes() -> bytes:
    """Make an original one-pixel RGB PNG using only the standard library."""
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", binascii.crc32(kind + payload) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\x24\x68\xac"))
            + chunk(b"IEND", b""))


def synthetic_image_validator(path: str) -> str:
    file = Path(path)
    if not file.is_file():
        raise ValueError("missing image: synthetic asset does not exist")
    expected = image_bytes()
    with file.open("rb") as stream:
        data = stream.read(len(expected) + 1)
    if data != expected:
        raise UnsupportedProtocol("image_unverified: only the exact generated synthetic PNG is supported")
    return hashlib.sha256(data).hexdigest()


def synthetic_context_cost(items) -> int:
    """Fixed test weights, NOT tokens: text=7, image=11, nonempty overhead=2."""
    return 0 if not items else 2 + sum(7 if item["type"] == "text" else 11 for item in items)


def trajectories():
    def state(index, tree, action=None):
        return {"state_index": index, "step": index + 3,
                "url": "https://example.invalid/workshop", "action": action,
                "thought": None, "accessibility_tree": tree,
                "screenshot": f"screenshots/workshop/{index}.png"}
    return [{"id": "workshop", "domain": "web", "environment": "invented-workshop",
             "goal": "Locate the blue toolkit.", "outcome": "success",
             "start_url": "https://example.invalid/workshop",
             "states": [state(0, "The blue toolkit is beside the north door."),
                        state(1, "The copper key is inside the green drawer.", "open drawer")]},
            {"id": "stockroom", "domain": "enterprise", "environment": "invented-stockroom",
             "goal": "Locate the silver lantern.", "outcome": "success",
             "start_url": "https://example.invalid/stockroom",
             "states": [{**state(0, "The silver lantern is on the west shelf."),
                         "screenshot": "screenshots/stockroom/0.png"}]}]


def write_assets(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=False)
    paths = [s["screenshot"] for t in trajectories() for s in t["states"]]
    for relative in paths + ["question_screenshots/synthetic.png"]:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes())
