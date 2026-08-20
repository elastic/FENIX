"""Fetch payloads from local files or HTTP(S) URLs."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import requests

DEFAULT_TIMEOUT = 30
# Some hosts (e.g. files.catbox.moe) reject python-requests' default User-Agent.
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FENIX-lab/1.0)"}


def fetch_bytes(*, source_file: str | Path | None = None, source_url: str | None = None) -> bytes:
    """Load raw bytes from a local file or remote URL."""
    if source_file and source_url:
        raise ValueError("Specify only one of source_file or source_url.")

    if source_file:
        path = Path(source_file).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Staging source not found: {path}")
        return path.read_bytes()

    if source_url:
        return fetch_url(source_url)

    raise ValueError("A staging source is required (source_file or source_url).")


def fetch_url(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """Download raw bytes from an HTTP/HTTPS URL (Pastebin-style raw URLs supported)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme (use http/https): {url}")

    try:
        response = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to fetch staging URL: {exc}") from exc

    return response.content
