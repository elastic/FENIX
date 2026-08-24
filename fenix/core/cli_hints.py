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
"""Copy-paste CLI hints (venv path, sudo) for lab docs and run-all."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from fenix.core.helpers import project_root


def resolve_fenix_cli_command() -> str:
    """Best-effort path to re-invoke this fenix install (for docs and hints)."""
    argv0 = Path(sys.argv[0])
    if argv0.is_file() or argv0.suffix:
        resolved = argv0.resolve()
        if resolved.is_file():
            return str(resolved)

    which = shutil.which("fenix")
    if which:
        return which

    for candidate in (
        project_root() / ".venv" / "bin" / "fenix",
        Path(os.environ.get("VIRTUAL_ENV", "")) / "bin" / "fenix",
    ):
        if candidate.is_file():
            return str(candidate.resolve())

    return "fenix"


def sudo_fenix_example(subcommand: str) -> str:
    """Example line for sudo + FENIX_BIN_DIR + venv fenix."""
    fenix = resolve_fenix_cli_command()
    return f"sudo env FENIX_BIN_DIR=$PWD/bin {fenix} {subcommand}"
