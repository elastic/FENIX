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
"""Payload path validation."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def _resolve_file(path: str | Path, *, label: str = "file") -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{label} not found: {resolved}")
    if not os.access(resolved, os.R_OK):
        raise PermissionError(f"{label} is not readable: {resolved}")
    if not stat.S_ISREG(resolved.stat().st_mode):
        raise ValueError(f"{label} is not a regular file: {resolved}")
    return resolved


def resolve_payload(path: str | Path) -> Path:
    """Validate that an ELF payload path exists and is readable."""
    return _resolve_file(path, label="Payload")


def resolve_script(path: str | Path) -> Path:
    """Validate that a script path exists and is readable."""
    return _resolve_file(path, label="Script")


def resolve_shared_library(path: str | Path) -> Path:
    """Validate a shared library (.so) path for dlopen techniques."""
    resolved = _resolve_file(path, label="Shared library")
    if not (resolved.suffix == ".so" or resolved.name.endswith(".so")):
        raise ValueError(f"Expected a .so shared library: {resolved}")
    return resolved


def resolve_module(path: str | Path) -> Path:
    """Validate a kernel module (.ko) path for lkm-load."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Module not found: {resolved}")
    if resolved.suffix != ".ko" and not resolved.name.endswith(".ko"):
        raise ValueError(f"Expected a .ko kernel module: {resolved}")
    return resolved
