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
"""Built-in remote staging presets (GitHub raw / Pastebin-style lab URLs)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LabStagingPreset:
    id: str
    summary: str
    path: str  # under FENIX_LAB_STAGING_BASE
    decode: str = "none"
    decompress: str = "none"
    execute: str = "memfd"
    method: str = "procfs-fd"
    xor_key: str | None = None
    interpreter: str | None = None
    mode: str | None = None


def lab_staging_base() -> str:
    """Base URL for raw artifacts (override for forks or self-hosted raw)."""
    return os.environ.get(
        "FENIX_LAB_STAGING_BASE",
        "https://raw.githubusercontent.com/elastic/fenix/main",
    ).rstrip("/")


def list_lab_preset_ids() -> list[str]:
    return sorted(LAB_STAGING_PRESETS.keys())


def get_lab_preset(preset_id: str) -> LabStagingPreset:
    key = preset_id.lower().replace("_", "-")
    if key not in LAB_STAGING_PRESETS:
        known = ", ".join(list_lab_preset_ids())
        raise ValueError(f"Unknown lab-remote preset '{preset_id}'. Choose: {known}")
    return LAB_STAGING_PRESETS[key]


def preset_url(preset: LabStagingPreset) -> str:
    return f"{lab_staging_base()}/{preset.path.lstrip('/')}"


def apply_lab_preset(options: dict[str, Any]) -> dict[str, Any]:
    """
    If options contain lab_remote / lab-remote, merge preset URL and defaults.
    Explicit CLI/YAML values win over preset defaults.
    """
    lab_id = options.get("lab_remote") or options.get("lab-remote")
    if not lab_id:
        return options

    preset = get_lab_preset(str(lab_id))
    merged = dict(options)
    merged["source_url"] = preset_url(preset)
    merged.pop("source_file", None)
    merged.pop("source-file", None)
    merged.pop("lab_remote", None)
    merged.pop("lab-remote", None)

    defaults: dict[str, Any] = {
        "decode": preset.decode,
        "decompress": preset.decompress,
        "execute": preset.execute,
        "method": preset.method,
    }
    if preset.xor_key:
        defaults["xor_key"] = preset.xor_key
    if preset.interpreter:
        defaults["interpreter"] = preset.interpreter
    if preset.mode:
        defaults["mode"] = preset.mode

    for key, value in defaults.items():
        alt = key.replace("_", "-")
        if merged.get(key) is None and merged.get(alt) is None:
            merged[key] = value

    return merged


LAB_STAGING_PRESETS: dict[str, LabStagingPreset] = {
    "hello-b64": LabStagingPreset(
        id="hello-b64",
        summary="hello_elf base64 → memfd exec (Pastebin/GitHub raw style)",
        path="payloads/staged/hello_elf.b64",
        decode="base64",
        execute="memfd",
        method="procfs-fd",
    ),
    "hello-xor": LabStagingPreset(
        id="hello-xor",
        summary="XOR-encoded hello_elf from raw URL → memfd fexecve",
        path="payloads/staged/hello_elf.xor",
        decode="xor",
        xor_key="fenix",
        execute="memfd",
        method="fexecve",
    ),
    "hello-py": LabStagingPreset(
        id="hello-py",
        summary="hello.py script from raw URL → python3 stdin",
        path="payloads/scripts/hello.py",
        decode="none",
        execute="interpreter",
        interpreter="python3",
        mode="stdin",
    ),
}
