# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch B.V. licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
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
