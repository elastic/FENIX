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
"""stdin-memexec — Load ELF from stdin or file into memfd and exec (memexec-style)."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload
from fenix.techniques import register

VALID_METHODS = ("procfs-fd", "fexecve", "execveat")


@register("stdin-memexec", "Read ELF from stdin into memfd and execute")
def run_stdin_memexec(options: dict[str, Any]) -> int:
    method = options.get("method") or "execveat"
    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    args = [
        "--name",
        str(options.get("name") or "fenix_stdin_payload"),
        "--method",
        str(method),
    ]

    payload = options.get("payload")
    if payload:
        path = resolve_payload(payload)
        args.extend(["--payload", str(path)])

    if options.get("fchmod"):
        args.append("--fchmod")

    return run_helper("stdin-memexec", args)
