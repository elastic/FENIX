"""interpreter-exec — Run code via installed interpreters."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fenix.core.payload import resolve_script
from fenix.interpreters.registry import get_interpreter, resolve_binary
from fenix.techniques import register

VALID_MODES = ("one-liner", "stdin", "script-file")


@register("interpreter-exec", "Execute via sh/bash/python3/perl")
def run_interpreter_exec(options: dict[str, Any]) -> int:
    interpreter_name = options.get("interpreter")
    mode = options.get("mode")
    if not interpreter_name or not mode:
        raise ValueError("interpreter-exec requires --interpreter and --mode")

    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Choose: {', '.join(VALID_MODES)}")

    spec = get_interpreter(str(interpreter_name))
    binary = resolve_binary(spec)

    code = options.get("code")
    script = options.get("script")

    if mode == "script-file":
        if not script:
            raise ValueError("script-file mode requires --script")
        script_path = resolve_script(script)
        result = subprocess.run([binary, str(script_path)], check=False)
        return int(result.returncode)

    if not code:
        raise ValueError(f"{mode} mode requires --code")

    if mode == "one-liner":
        result = subprocess.run([binary, spec.oneliner_flag, str(code)], check=False)
        return int(result.returncode)

    if mode == "stdin":
        if not spec.supports_stdin:
            raise ValueError(f"Interpreter '{spec.name}' does not support stdin mode")
        result = subprocess.run([binary], input=str(code).encode(), check=False)
        return int(result.returncode)

    raise ValueError(f"Unhandled mode: {mode}")
