"""Download staged payloads via different userland fetchers (lab telemetry)."""

from __future__ import annotations

import subprocess
import sys
from typing import Literal

from fenix.core.staging import DEFAULT_TIMEOUT, fetch_url

FetchMethod = Literal["requests", "curl", "wget", "python"]

VALID_FETCH_METHODS: tuple[str, ...] = ("requests", "curl", "wget", "python")


def fetch_remote_bytes(url: str, *, method: str = "requests", timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Fetch URL bytes using the chosen download implementation."""
    key = (method or "requests").lower().strip()
    if key not in VALID_FETCH_METHODS:
        known = ", ".join(VALID_FETCH_METHODS)
        raise ValueError(f"Unknown remote-fetch '{method}'. Choose: {known}")

    if key == "requests":
        return fetch_url(url, timeout=timeout)
    if key == "curl":
        return _fetch_subprocess(["curl", "-fsSL", url], timeout=timeout)
    if key == "wget":
        return _fetch_subprocess(["wget", "-qO-", url], timeout=timeout)
    return _fetch_python_urllib(url, timeout=timeout)


def _fetch_subprocess(argv: list[str], *, timeout: int) -> bytes:
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Fetcher not found on PATH: {argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Timed out fetching URL ({timeout}s): {argv[-1]}") from exc

    if completed.returncode != 0:
        err = (completed.stderr or b"").decode(errors="replace").strip()
        raise RuntimeError(f"{argv[0]} failed (exit {completed.returncode}): {err or 'no stderr'}")
    return completed.stdout


def _fetch_python_urllib(url: str, *, timeout: int) -> bytes:
    code = (
        "import sys, urllib.request; "
        f"sys.stdout.buffer.write(urllib.request.urlopen({url!r}, timeout={timeout}).read())"
    )
    return _fetch_subprocess([sys.executable, "-c", code], timeout=timeout)
