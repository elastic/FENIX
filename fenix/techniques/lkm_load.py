"""lkm-load — Load benign kernel module via init_module / finit_module."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_module
from fenix.techniques import register

VALID_METHODS = (
    "init_module",
    "memfd-init-module",
    "memfd-init-module-fork",
    "finit_module",
    "memfd-finit-module",
    "embedded-init-module",
)

_INIT_MODULE_METHODS = frozenset(
    ("init_module", "memfd-init-module", "memfd-init-module-fork")
)


def _kmod_name(module: str | None, method: str) -> str:
    if method == "embedded-init-module" or not module:
        return "hello_lkm"
    path = Path(module)
    stem = path.stem
    if stem.endswith(".ko"):
        return stem[:-3]
    return stem


def _should_keep_loaded(options: dict[str, Any]) -> bool:
    return bool(options.get("keep_loaded") or options.get("keep-loaded"))


def _lab_rmmod(name: str, *, phase: str) -> None:
    from fenix.core.cleanup import rmmod_module

    ok, detail = rmmod_module(name)
    if detail == "unloaded":
        print(f"fenix: rmmod {name} ({phase})", file=sys.stderr)
    elif not ok:
        print(f"fenix: rmmod {name} failed ({phase}): {detail}", file=sys.stderr)


@register("lkm-load", "Load kernel module from memory or fd (root, lab only)")
def run_lkm_load(options: dict[str, Any]) -> int:
    if sys.platform != "linux":
        raise OSError("lkm-load requires Linux.")

    if os.geteuid() != 0:
        raise PermissionError("lkm-load must be run as root (effective UID 0).")

    if not options.get("i_understand_this_loads_kernel_code") and not options.get(
        "i-understand-this-loads-kernel-code"
    ):
        raise PermissionError(
            "Refusing to load kernel module without "
            "--i-understand-this-loads-kernel-code"
        )

    method = options.get("method") or "init_module"

    if method not in VALID_METHODS:
        raise ValueError(f"Invalid method '{method}'. Choose: {', '.join(VALID_METHODS)}")

    keep_loaded = _should_keep_loaded(options)
    kmod_name = _kmod_name(options.get("module"), method)

    if not keep_loaded:
        _lab_rmmod(kmod_name, phase="pre-load")

    from fenix.core import cleanup

    if keep_loaded:
        cleanup.note_artifact("lkm-load", "kmod", kmod_name)

    if method == "embedded-init-module":
        rc = run_helper("embedded-init-module", [])
    else:
        module = options.get("module")
        if not module:
            raise ValueError("lkm-load requires --module")

        module_path = resolve_module(module)

        if method in _INIT_MODULE_METHODS:
            rc = run_helper(
                "init-module",
                ["--module", str(module_path), "--method", method],
            )
        else:
            finit_method = (
                "memfd-finit-module" if method == "memfd-finit-module" else "finit_module"
            )
            rc = run_helper(
                "finit-module",
                ["--module", str(module_path), "--method", finit_method],
            )

    if rc == 0 and not keep_loaded:
        _lab_rmmod(kmod_name, phase="post-run cleanup")

    return rc
