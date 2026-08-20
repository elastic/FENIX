"""stdin-memexec — Load ELF from stdin or file into memfd and exec (memexec-style)."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload
from fenix.techniques import register

VALID_METHODS = ("procfs-fd", "fexecve", "execveat")


@register("stdin-memexec", "Read ELF from stdin into memfd and execute")
def run_stdin_memexec(options: dict[str, Any]) -> int:
    method = options.get("method") or "execveat"
    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    args = [
        "--name",
        str(options.get("name") or "fenix_stdin_payload"),
        "--method",
        str(method),
    ]

    payload = options.get("payload")
    if payload:
        path = resolve_payload(payload)
        args.extend(["--payload", str(path)])

    if options.get("fchmod"):
        args.append("--fchmod")

    return run_helper("stdin-memexec", args)
