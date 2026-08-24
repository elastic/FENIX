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
"""memfd-self-reexec — QLNX-style copy /proc/self/exe to memfd, unlink, re-exec."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.techniques import register

VALID_METHODS = ("execveat", "procfs-fd")


@register("memfd-self-reexec", "Re-execute own binary from memfd after unlinking disk copy")
def run_memfd_self_reexec(options: dict[str, Any]) -> int:
    if options.get("payload"):
        import sys

        print(
            "fenix: memfd-self-reexec ignores --payload; it re-execs fenix-memfd-self-reexec "
            "from /proc/self/exe, not hello_elf. Use memfd-exec for payloads/hello_elf/hello.",
            file=sys.stderr,
        )
    name = options.get("name") or "fenix_self"
    method = options.get("method") or "execveat"

    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    args = ["--name", str(name), "--method", str(method)]

    argv0 = options.get("argv0")
    if argv0:
        args.extend(["--argv0", str(argv0)])

    if options.get("no_unlink"):
        args.append("--no-unlink")

    return run_helper("memfd-self-reexec", args)
