"""interpreter-memfd-exec — memfd loader via -e/-c/-r or memfd_payload.* script file."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fenix.core.memfd_payloads import (
    VALID_MODES,
    list_memfd_interpreters,
    load_memfd_oneliner_source,
    materialize_memfd_script,
)
from fenix.core.payload import resolve_payload
from fenix.interpreters.registry import get_interpreter, resolve_binary
from fenix.techniques import register

SUPPORTED = frozenset(list_memfd_interpreters())


@register(
    "interpreter-memfd-exec",
    "Interpreter memfd loader: one-liner (-e/-c) or script-file (memfd_payload.*)",
)
def run_interpreter_memfd_exec(options: dict[str, Any]) -> int:
    interpreter_name = str(options.get("interpreter") or "")
    if interpreter_name.lower() not in SUPPORTED:
        known = ", ".join(sorted(SUPPORTED))
        raise ValueError(
            f"interpreter-memfd-exec requires --interpreter ({known})"
        )

    mode = options.get("mode") or "one-liner"
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Choose: {', '.join(VALID_MODES)}")

    payload_path = options.get("payload") or "payloads/hello_elf/hello"
    elf = resolve_payload(payload_path).read_bytes()
    argv0 = str(options.get("argv0") or "fenix_payload")

    spec = get_interpreter(interpreter_name)
    binary = resolve_binary(spec)

    if mode == "one-liner":
        code = options.get("memfd_oneliner_code") or load_memfd_oneliner_source(
            spec.name, argv0=argv0
        )
        cmd = [binary, spec.oneliner_flag, code]
    else:
        script_path = options.get("memfd_script_path")
        if not script_path:
            script_path = str(
                materialize_memfd_script(spec.name, argv0=argv0)
            )
        cmd = [binary, str(script_path)]

    result = subprocess.run(cmd, input=elf, check=False)
    return int(result.returncode)
