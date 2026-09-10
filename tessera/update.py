"""Small, opt-out update check for the public TESSERA distribution."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

PROJECT = "tessera-agent-memory"
PYPI_URL = f"https://pypi.org/pypi/{PROJECT}/json"
CACHE_TTL_SECONDS = 24 * 60 * 60


def _version(value: str) -> Tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value))


def _cache_path() -> Path:
    root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "tessera" / "update-check.json"


def latest_version(*, timeout: float = 1.5) -> Optional[str]:
    """Return the latest PyPI version, or ``None`` when offline/unavailable."""
    request = urllib.request.Request(PYPI_URL, headers={"User-Agent": "tessera-update-check"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return str(json.load(response)["info"]["version"])
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        return None


def check_for_update(*, force: bool = False) -> Optional[Tuple[str, str]]:
    """Return ``(installed, latest)`` when an update exists.

    The result is cached for a day to keep normal CLI commands fast. Set
    ``TESSERA_NO_UPDATE_CHECK=1`` to opt out, or use ``force=True`` from the
    explicit ``tessera update`` command.
    """
    if os.environ.get("TESSERA_NO_UPDATE_CHECK"):
        return None
    from . import __version__

    cache = _cache_path()
    latest = None
    if not force:
        try:
            payload = json.loads(cache.read_text())
            if time.time() - float(payload["checked_at"]) < CACHE_TTL_SECONDS:
                latest = str(payload["latest"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
    if latest is None:
        latest = latest_version()
        if latest:
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps({"checked_at": time.time(), "latest": latest}) + "\n")
            except OSError:
                pass
    if latest and _version(latest) > _version(__version__):
        return __version__, latest
    return None


def install_latest() -> int:
    """Upgrade the current environment, preferring uv when available."""
    uv = shutil.which("uv")
    if uv:
        command = [uv, "pip", "install", "--python", sys.executable, "--upgrade", PROJECT]
    else:
        command = [sys.executable, "-m", "pip", "install", "--upgrade", PROJECT]
    return subprocess.call(command)
