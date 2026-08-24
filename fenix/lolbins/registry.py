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
"""LoLbin registry for lolbin-fd-exec (memfd + /proc/self/fd/N)."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LolbinSpec:
    id: str
    summary: str
    payload_kind: str  # elf | script
    default_payload: str
    binaries: tuple[str, ...]
    ld_candidates: tuple[str, ...] = ()
    install_hint: str = ""


LOLBINS: dict[str, LolbinSpec] = {
    "ld-linux": LolbinSpec(
        id="ld-linux",
        summary="Dynamic linker executes ELF from /proc/self/fd/N",
        payload_kind="elf",
        default_payload="payloads/hello_elf/hello",
        binaries=(),
        ld_candidates=(
            "/lib64/ld-linux-x86-64.so.2",
            "/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2",
            "/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1",
            "/lib64/ld-linux-aarch64.so.1",
        ),
    ),
    "busybox": LolbinSpec(
        id="busybox",
        summary="busybox sh runs script from /proc/self/fd/N",
        payload_kind="script",
        default_payload="payloads/scripts/hello_shebang.sh",
        binaries=("busybox",),
        install_hint="sudo apt install -y busybox",
    ),
    "julia": LolbinSpec(
        id="julia",
        summary="julia runs script from /proc/self/fd/N",
        payload_kind="script",
        default_payload="payloads/scripts/hello.jl",
        binaries=("julia",),
        install_hint=(
            "Not in default apt on many Ubuntu releases. "
            "Try: sudo snap install julia --classic "
            "or https://julialang.org/downloads/"
        ),
    ),
    "erlang": LolbinSpec(
        id="erlang",
        summary="escript runs Erlang script from /proc/self/fd/N",
        payload_kind="script",
        default_payload="payloads/scripts/hello.escript",
        binaries=("escript",),
        install_hint="sudo apt install -y erlang   # provides /usr/bin/escript (not package 'escript')",
    ),
}


def list_lolbin_ids() -> list[str]:
    return sorted(LOLBINS.keys())


def get_lolbin(lolbin_id: str) -> LolbinSpec:
    key = lolbin_id.lower().replace("_", "-")
    aliases = {"ld.so": "ld-linux", "ld-linux-x86-64.so.2": "ld-linux"}
    key = aliases.get(key, key)
    if key not in LOLBINS:
        raise ValueError(
            f"Unknown lolbin '{lolbin_id}'. Supported: {', '.join(list_lolbin_ids())}"
        )
    return LOLBINS[key]


def resolve_lolbin_binary(spec: LolbinSpec) -> str:
    if spec.ld_candidates:
        for path in spec.ld_candidates:
            if Path(path).is_file() and Path(path).stat().st_mode & 0o111:
                return path
        raise FileNotFoundError(
            "ld-linux linker not found (tried: "
            + ", ".join(spec.ld_candidates)
            + "). Install libc or pass --bin."
        )
    for candidate in spec.binaries:
        found = shutil.which(candidate)
        if found:
            return found
    hint = f" Install: {spec.install_hint}" if spec.install_hint else ""
    raise FileNotFoundError(
        f"Lolbin '{spec.id}' not found on PATH (tried: {', '.join(spec.binaries)}).{hint}"
    )
