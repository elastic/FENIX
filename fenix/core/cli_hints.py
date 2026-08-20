"""Copy-paste CLI hints (venv path, sudo) for lab docs and run-all."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from fenix.core.helpers import project_root


def resolve_fenix_cli_command() -> str:
    """Best-effort path to re-invoke this fenix install (for docs and hints)."""
    argv0 = Path(sys.argv[0])
    if argv0.is_file() or argv0.suffix:
        resolved = argv0.resolve()
        if resolved.is_file():
            return str(resolved)

    which = shutil.which("fenix")
    if which:
        return which

    for candidate in (
        project_root() / ".venv" / "bin" / "fenix",
        Path(os.environ.get("VIRTUAL_ENV", "")) / "bin" / "fenix",
    ):
        if candidate.is_file():
            return str(candidate.resolve())

    return "fenix"


def sudo_fenix_example(subcommand: str) -> str:
    """Example line for sudo + FENIX_BIN_DIR + venv fenix."""
    fenix = resolve_fenix_cli_command()
    return f"sudo env FENIX_BIN_DIR=$PWD/bin {fenix} {subcommand}"
