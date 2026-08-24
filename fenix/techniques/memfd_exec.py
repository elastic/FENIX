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
"""memfd-exec — Execute ELF payload from anonymous memfd."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from fenix.core.helpers import find_helper
from fenix.core.lab_hints import print_noexec_seal_lab_hints
from fenix.core.payload import resolve_payload
from fenix.techniques import register

VALID_METHODS = ("procfs-fd", "fexecve", "execveat")
VALID_INGEST = ("write", "sendfile")


@register("memfd-exec", "Execute ELF from anonymous memfd")
def run_memfd_exec(options: dict[str, Any]) -> int:
    payload = options.get("payload")
    if not payload:
        raise ValueError("memfd-exec requires --payload")

    path = resolve_payload(payload)
    name = options.get("name") or "fenix_payload"
    method = options.get("method") or "procfs-fd"

    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    args = [
        "--payload",
        str(path),
        "--name",
        str(name),
        "--method",
        str(method),
    ]

    argv0 = options.get("argv0")
    if argv0:
        args.extend(["--argv0", str(argv0)])

    if options.get("keep_fd_open"):
        args.append("--keep-fd-open")

    if options.get("fchmod"):
        args.append("--fchmod")

    ingest = options.get("ingest") or "write"
    if ingest not in VALID_INGEST:
        raise ValueError(f"Invalid ingest '{ingest}'. Choose: {', '.join(VALID_INGEST)}")
    if ingest != "write":
        args.extend(["--ingest", str(ingest)])

    noexec_seal = bool(options.get("noexec_seal") or options.get("noexec-seal"))
    fchmod = bool(options.get("fchmod"))
    if noexec_seal:
        args.append("--noexec-seal")

    binary = find_helper("memfd-exec")
    result = subprocess.run(
        [str(binary), *args],
        check=False,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.stderr:
        sys.stderr.write(result.stderr)
        if not result.stderr.endswith("\n"):
            sys.stderr.write("\n")

    rc = int(result.returncode)
    # Expected lab outcome on modern kernels (works with old helpers that exit 1 + perror)
    if noexec_seal and fchmod and rc != 0:
        print_noexec_seal_lab_hints()
        return 1
    return rc
