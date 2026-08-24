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
"""lolbin-fd-exec — memfd payload executed via LoLbin + /proc/self/fd/N."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload, resolve_script
from fenix.lolbins.registry import get_lolbin, resolve_lolbin_binary
from fenix.techniques import register


@register("lolbin-fd-exec", "Execute via LoLbin and /proc/self/fd/N (ld-linux, busybox, …)")
def run_lolbin_fd_exec(options: dict[str, Any]) -> int:
    lolbin_id = options.get("lolbin")
    if not lolbin_id:
        raise ValueError("lolbin-fd-exec requires --lolbin (ld-linux, busybox, julia, erlang)")

    spec = get_lolbin(str(lolbin_id))
    payload = options.get("payload")
    if not payload:
        payload = spec.default_payload

    if spec.payload_kind == "elf":
        path = resolve_payload(payload)
    else:
        path = resolve_script(payload)

    name = options.get("name") or "fenix_lolbin"
    binary = options.get("bin") or options.get("linker")
    try:
        bin_path = str(binary) if binary else resolve_lolbin_binary(spec)
    except FileNotFoundError as exc:
        raise ValueError(str(exc)) from exc

    args = [
        "--payload",
        str(path),
        "--name",
        str(name),
        "--lolbin",
        spec.id,
        "--bin",
        bin_path,
    ]
    return run_helper("lolbin-fd-exec", args)
