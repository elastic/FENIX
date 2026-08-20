"""memfd-self-reexec — QLNX-style copy /proc/self/exe to memfd, unlink, re-exec."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.techniques import register

VALID_METHODS = ("execveat", "procfs-fd")


@register("memfd-self-reexec", "Re-execute own binary from memfd after unlinking disk copy")
def run_memfd_self_reexec(options: dict[str, Any]) -> int:
    if options.get("payload"):
        import sys

        print(
            "fenix: memfd-self-reexec ignores --payload; it re-execs fenix-memfd-self-reexec "
            "from /proc/self/exe, not hello_elf. Use memfd-exec for payloads/hello_elf/hello.",
            file=sys.stderr,
        )
    name = options.get("name") or "fenix_self"
    method = options.get("method") or "execveat"

    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    args = ["--name", str(name), "--method", str(method)]

    argv0 = options.get("argv0")
    if argv0:
        args.extend(["--argv0", str(argv0)])

    if options.get("no_unlink"):
        args.append("--no-unlink")

    return run_helper("memfd-self-reexec", args)
