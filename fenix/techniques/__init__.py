"""FENIX technique modules."""

from __future__ import annotations

from typing import Any, Callable

TechniqueFn = Callable[[dict[str, Any]], int]

_REGISTRY: dict[str, tuple[str, TechniqueFn]] = {}


def register(technique_id: str, description: str):
    def decorator(fn: TechniqueFn):
        _REGISTRY[technique_id] = (description, fn)
        return fn

    return decorator


def list_techniques() -> list[tuple[str, str]]:
    return sorted((tid, meta[0]) for tid, meta in _REGISTRY.items())


def get_technique(technique_id: str) -> TechniqueFn:
    if technique_id not in _REGISTRY:
        known = ", ".join(tid for tid, _ in list_techniques())
        raise ValueError(f"Unknown technique '{technique_id}'. Available: {known}")
    return _REGISTRY[technique_id][1]


def run_technique(technique_id: str, options: dict[str, Any]) -> int:
    fn = get_technique(technique_id)
    return fn(options)


# Register built-in techniques on import.
from fenix.techniques import (  # noqa: E402, F401
    deleted_file_exec,
    fileless_staging,
    interpreter_exec,
    interpreter_memfd_exec,
    lolbin_fd_exec,
    lkm_load,
    memfd_exec,
    memfd_script_exec,
    memfd_self_reexec,
    memfd_so_load,
    pipe_exec,
    proc_fd_exec,
    shm_exec,
    shm_so_load,
    stdin_memexec,
)
