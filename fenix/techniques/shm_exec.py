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
"""shm-exec — Execute ELF via POSIX shm_open on tmpfs (/dev/shm)."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload
from fenix.techniques import register

VALID_METHODS = ("procfs-fd", "fexecve")
VALID_INGEST = ("write", "sendfile")


@register("shm-exec", "Execute ELF via shm_open on tmpfs (pre-memfd / noexec lab path)")
def run_shm_exec(options: dict[str, Any]) -> int:
    payload = options.get("payload")
    if not payload:
        raise ValueError("shm-exec requires --payload")

    path = resolve_payload(payload)
    method = options.get("method") or "procfs-fd"
    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    ingest = options.get("ingest") or "write"
    if ingest not in VALID_INGEST:
        raise ValueError(f"Invalid ingest '{ingest}'. Choose: {', '.join(VALID_INGEST)}")

    shm_name = str(options.get("name") or "fenix_shm_payload")
    args = [
        "--payload",
        str(path),
        "--name",
        shm_name,
        "--method",
        str(method),
        "--ingest",
        str(ingest),
    ]
    if options.get("unlink"):
        args.append("--unlink")

    from fenix.core import cleanup

    cleanup.note_artifact("shm-exec", "shm", shm_name.lstrip("/"))
    return run_helper("shm-exec", args)
