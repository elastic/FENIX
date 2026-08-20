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
