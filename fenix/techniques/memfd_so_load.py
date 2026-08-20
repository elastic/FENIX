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
