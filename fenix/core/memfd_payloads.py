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
"""Memfd+stdin ELF loader templates for interpreter -e/-c and memfd_payload.* scripts."""

from __future__ import annotations

import platform
import tempfile
from pathlib import Path
from typing import Any

from fenix.core import cleanup
from fenix.core.helpers import project_root

_MEMFD_SYSCALL: dict[str, int] = {
    "x86_64": 319,
    "amd64": 319,
    "aarch64": 279,
    "arm64": 279,
}

# Stable script basenames for script-file detection (python memfd_payload.py, …).
INTERPRETER_MEMFD_PAYLOADS: dict[str, str] = {
    "perl": "memfd_payload.pl",
    "python3": "memfd_payload.py",
    "ruby": "memfd_payload.rb",
    "php": "memfd_payload.php",
}

VALID_MODES = ("one-liner", "script-file")


def list_memfd_interpreters() -> list[str]:
    return sorted(INTERPRETER_MEMFD_PAYLOADS.keys())


def memfd_syscall_number() -> int:
    machine = platform.machine().lower()
    if machine not in _MEMFD_SYSCALL:
        known = ", ".join(sorted(set(_MEMFD_SYSCALL)))
        raise RuntimeError(
            f"Unsupported architecture '{machine}' for interpreter memfd payloads. "
            f"Supported: {known}"
        )
    return _MEMFD_SYSCALL[machine]


def payload_dir() -> Path:
    return project_root() / "payloads" / "memfd_oneliners"


def resolve_template(interpreter: str) -> Path:
    key = interpreter.lower()
    if key not in INTERPRETER_MEMFD_PAYLOADS:
        known = ", ".join(list_memfd_interpreters())
        raise ValueError(
            f"No memfd payload for interpreter '{interpreter}'. Available: {known}"
        )
    path = payload_dir() / INTERPRETER_MEMFD_PAYLOADS[key]
    if not path.is_file():
        raise FileNotFoundError(f"Memfd payload template missing: {path}")
    return path


def load_memfd_source(interpreter: str, *, argv0: str) -> str:
    """Expanded loader source (script-file / template; includes <?php for .php files)."""
    text = resolve_template(interpreter).read_text(encoding="utf-8")
    text = text.replace("__FENIX_MEMFD_SYSCALL__", str(memfd_syscall_number()))
    text = text.replace("__FENIX_ARGV0__", argv0)
    return text


def php_inline_from_source(source: str) -> str:
    """php -r cannot parse <?php tags; pass inline body only."""
    text = source.strip()
    if text.startswith("<?php"):
        text = text[5:].lstrip("\r\n")
    elif text.startswith("<?"):
        text = text[2:].lstrip("\r\n")
    if text.endswith("?>"):
        text = text[:-2].rstrip()
    return text.strip()


def load_memfd_oneliner_source(interpreter: str, *, argv0: str) -> str:
    """Source passed to interpreter -e/-c/-r (PHP: inline body without tags)."""
    text = load_memfd_source(interpreter, argv0=argv0)
    if interpreter.lower() == "php":
        text = php_inline_from_source(text)
    return text


def materialize_memfd_script(
    interpreter: str,
    *,
    argv0: str,
    template_path: Path | None = None,
) -> Path:
    """
    Write expanded memfd_payload.<ext> under a temp dir for script-file runs.
    argv shows e.g. python3 /tmp/fenix-memfd-…/memfd_payload.py
    """
    key = interpreter.lower()
    basename = INTERPRETER_MEMFD_PAYLOADS[key]
    if template_path is not None:
        text = template_path.read_text(encoding="utf-8")
        text = text.replace("__FENIX_MEMFD_SYSCALL__", str(memfd_syscall_number()))
        text = text.replace("__FENIX_ARGV0__", argv0)
        content = text
    else:
        content = load_memfd_source(interpreter, argv0=argv0)
    tmp_dir = Path(tempfile.mkdtemp(prefix="fenix-memfd-"))
    script = tmp_dir / basename
    script.write_text(content, encoding="utf-8")
    script.chmod(0o755)
    cleanup.register(tmp_dir, technique="interpreter-memfd-exec")
    return script


def prepare_interpreter_memfd_exec(options: dict[str, Any]) -> dict[str, Any]:
    """
    Resolve launch command and payload source for explain + run (single materialize).
    Sets memfd_launch_display, memfd_payload_source, memfd_payload_kind; script path when needed.
    """
    from fenix.core.payload import resolve_script
    from fenix.interpreters.registry import get_interpreter, resolve_binary

    opts = dict(options)
    interpreter = str(opts.get("interpreter") or "")
    mode = opts.get("mode") or "one-liner"
    argv0 = str(opts.get("argv0") or "fenix_payload")

    spec = get_interpreter(interpreter)
    try:
        binary = resolve_binary(spec)
    except FileNotFoundError:
        binary = spec.binaries[0]

    if mode == "script-file":
        script_path = opts.get("memfd_script_path")
        if script_path:
            path = Path(script_path)
        else:
            script_opt = opts.get("script")
            template = resolve_script(script_opt) if script_opt else None
            path = materialize_memfd_script(
                spec.name, argv0=argv0, template_path=template
            )
            opts["memfd_script_path"] = str(path)
        source = path.read_text(encoding="utf-8")
        opts["memfd_payload_kind"] = "script-file"
        opts["memfd_launch_display"] = f"{binary} {path}"
        opts["memfd_payload_source"] = source
        tpl = resolve_template(interpreter)
        opts["memfd_template_path"] = str(tpl)
    else:
        full = load_memfd_source(spec.name, argv0=argv0)
        inline = load_memfd_oneliner_source(spec.name, argv0=argv0)
        opts["memfd_payload_kind"] = "one-liner"
        opts["memfd_launch_display"] = f"{binary} {spec.oneliner_flag} <see payload below>"
        opts["memfd_payload_source"] = inline
        opts["memfd_oneliner_code"] = inline
        if interpreter.lower() == "php":
            opts["memfd_payload_source_full"] = full
        tpl = resolve_template(interpreter)
        opts["memfd_template_path"] = str(tpl)

    return opts
