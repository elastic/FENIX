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
"""deleted-file-exec — Execute payload then unlink path on disk."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload
from fenix.techniques import register


@register("deleted-file-exec", "Execute from disk and unlink the backing file")
def run_deleted_file_exec(options: dict[str, Any]) -> int:
    payload = options.get("payload")
    target_path = options.get("path")
    if not payload or not target_path:
        raise ValueError("deleted-file-exec requires --payload and --path")

    path = resolve_payload(payload)
    extra_args = options.get("args")
    wait = options.get("wait", True)
    if options.get("no_wait"):
        wait = False

    args = [
        "--payload",
        str(path),
        "--path",
        str(target_path),
    ]

    if extra_args is not None:
        args.extend(["--args", str(extra_args)])

    args.append("--wait" if wait else "--no-wait")

    from fenix.core import cleanup

    cleanup.note_artifact("deleted-file-exec", "path", str(target_path))
    return run_helper("deleted-exec", args)
