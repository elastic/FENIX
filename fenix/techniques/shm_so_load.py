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
"""shm-so-load — dlopen a shared library from POSIX shared memory (/dev/shm)."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_shared_library
from fenix.techniques import register


@register("shm-so-load", "Load .so from shm_open tmpfs path via dlopen")
def run_shm_so_load(options: dict[str, Any]) -> int:
    module = options.get("module")
    if not module:
        raise ValueError("shm-so-load requires --module")

    module_path = resolve_shared_library(module)
    shm_name = str(options.get("name") or "fenix_shm_module")
    args = [
        "--module",
        str(module_path),
        "--symbol",
        str(options.get("symbol") or "fenix_hello"),
        "--name",
        shm_name,
    ]
    from fenix.core import cleanup

    cleanup.note_artifact("shm-so-load", "shm", shm_name.lstrip("/"))
    return run_helper("shm-so-load", args)
