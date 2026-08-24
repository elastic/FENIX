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
"""memfd-so-load — Reflective shared-library load from memfd via dlopen."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_shared_library
from fenix.techniques import register


@register("memfd-so-load", "Load .so from memfd and invoke a symbol (dlopen lab PoC)")
def run_memfd_so_load(options: dict[str, Any]) -> int:
    module = options.get("module") or options.get("payload")
    if not module:
        raise ValueError("memfd-so-load requires --module")

    path = resolve_shared_library(module)
    args = ["--module", str(path)]
    if options.get("symbol"):
        args.extend(["--symbol", str(options["symbol"])])
    if options.get("name"):
        args.extend(["--name", str(options["name"])])

    return run_helper("memfd-so-load", args)
