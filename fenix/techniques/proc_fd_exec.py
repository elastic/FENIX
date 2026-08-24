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
"""proc-fd-exec — Execute payload via /proc/self/fd or fexecve on open fd."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fenix.core import cleanup
from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload
from fenix.techniques import register

VALID_METHODS = ("procfs-fd", "fexecve", "execveat")


@register("proc-fd-exec", "Execute via open file descriptor and /proc/self/fd")
def run_proc_fd_exec(options: dict[str, Any]) -> int:
    payload = options.get("payload")
    if not payload:
        raise ValueError("proc-fd-exec requires --payload")

    path = resolve_payload(payload)
    method = options.get("method") or "procfs-fd"
    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    exec_path = path
    if options.get("unlink_after_open") or options.get("unlink"):
        staging = cleanup.temp_path(
            prefix="fenix-procfd-",
            suffix=Path(path).name,
            technique="proc-fd-exec",
        )
        shutil.copy2(path, staging)
        exec_path = staging

    args = ["--payload", str(exec_path), "--method", str(method)]

    argv0 = options.get("argv0")
    if argv0:
        args.extend(["--argv0", str(argv0)])

    if options.get("unlink_after_open") or options.get("unlink"):
        args.append("--unlink-after-open")

    return run_helper("proc-fd-exec", args)
