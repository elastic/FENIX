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
"""Registry of supported script interpreters."""

from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class InterpreterSpec:
    name: str
    binaries: tuple[str, ...]
    oneliner_flag: str
    supports_stdin: bool = True


INTERPRETERS: dict[str, InterpreterSpec] = {
    "sh": InterpreterSpec("sh", ("sh", "dash"), "-c"),
    "bash": InterpreterSpec("bash", ("bash",), "-c"),
    "python3": InterpreterSpec("python3", ("python3", "python"), "-c"),
    "perl": InterpreterSpec("perl", ("perl",), "-e"),
    "php": InterpreterSpec("php", ("php", "php8.3", "php8.2"), "-r"),
    "ruby": InterpreterSpec("ruby", ("ruby",), "-e"),
    "node": InterpreterSpec("node", ("node", "nodejs"), "-e"),
    "awk": InterpreterSpec("awk", ("gawk", "awk", "mawk"), "-e"),
    "lua": InterpreterSpec("lua", ("lua", "lua5.4", "lua5.3"), "-e"),
}


def list_interpreter_names() -> list[str]:
    return sorted(INTERPRETERS.keys())


def get_interpreter(name: str) -> InterpreterSpec:
    key = name.lower()
    if key not in INTERPRETERS:
        known = ", ".join(list_interpreter_names())
        raise ValueError(f"Unknown interpreter '{name}'. Supported: {known}")
    return INTERPRETERS[key]


def resolve_binary(spec: InterpreterSpec) -> str:
    for candidate in spec.binaries:
        path = shutil.which(candidate)
        if path:
            return path
    raise FileNotFoundError(
        f"Interpreter '{spec.name}' not found on PATH (tried: {', '.join(spec.binaries)})"
    )


def discover_installed() -> list[tuple[str, str]]:
    """Return (logical_name, resolved_binary) for interpreters found on PATH."""
    found: list[tuple[str, str]] = []
    for name in list_interpreter_names():
        spec = get_interpreter(name)
        try:
            found.append((name, resolve_binary(spec)))
        except FileNotFoundError:
            continue
    return found
