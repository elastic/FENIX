"""pipe-exec — Execute ELF or script via pipe + fexecve / stdin."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from fenix.core.helpers import find_helper
from fenix.core.payload import resolve_payload, resolve_script
from fenix.interpreters.registry import get_interpreter, resolve_binary
from fenix.techniques import register


def _print_pipe_elf_denied_hint() -> None:
    print(
        "\n"
        "pipe-exec ELF: kernel blocked fexecve from pipe (EPERM). "
        "That is a common, expected outcome — the syscall chain is still the lab signal.\n"
        "  Working alternatives: memfd-exec --method fexecve, or pipe-exec --type script\n",
        file=sys.stderr,
    )


def _run_pipe_helper(args: list[str]) -> int:
    binary = find_helper("pipe-exec")
    result = subprocess.run([str(binary), *args], check=False, stderr=subprocess.PIPE, text=True)
    if result.stderr:
        sys.stderr.write(result.stderr)
        if not result.stderr.endswith("\n"):
            sys.stderr.write("\n")
    return int(result.returncode)


@register("pipe-exec", "Execute ELF or script through a pipe")
def run_pipe_exec(options: dict[str, Any]) -> int:
    exec_type = options.get("type") or "elf"

    if exec_type == "elf":
        payload = options.get("payload")
        if not payload:
            raise ValueError("pipe-exec type elf requires --payload")
        path = resolve_payload(payload)
        rc = _run_pipe_helper(["--type", "elf", "--payload", str(path)])
        if rc != 0:
            _print_pipe_elf_denied_hint()
        return rc

    if exec_type == "script":
        interpreter = options.get("interpreter")
        if not interpreter:
            raise ValueError("pipe-exec type script requires --interpreter")

        spec = get_interpreter(str(interpreter))
        binary = resolve_binary(spec)

        script_file = options.get("script") or options.get("script_file")
        code = options.get("code") or options.get("content")

        args = ["--type", "script", "--interpreter", binary]
        if script_file:
            path = resolve_script(script_file)
            args.extend(["--script-file", str(path)])
        elif code:
            args.extend(["--content", str(code)])
        else:
            raise ValueError("pipe-exec type script requires --script or --code")

        return _run_pipe_helper(args)

    raise ValueError(f"Invalid type '{exec_type}'. Choose: elf, script")
