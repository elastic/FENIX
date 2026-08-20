"""Locate and invoke compiled FENIX C helpers."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

HELPER_NAMES = {
    "memfd-exec": "fenix-memfd-exec",
    "memfd-script-exec": "fenix-memfd-script-exec",
    "memfd-self-reexec": "fenix-memfd-self-reexec",
    "memfd-so-load": "fenix-memfd-so-load",
    "shm-exec": "fenix-shm-exec",
    "shm-so-load": "fenix-shm-so-load",
    "stdin-memexec": "fenix-stdin-memexec",
    "pipe-exec": "fenix-pipe-exec",
    "proc-fd-exec": "fenix-proc-fd-exec",
    "lolbin-fd-exec": "fenix-lolbin-fd-exec",
    "deleted-exec": "fenix-deleted-exec",
    "init-module": "fenix-init-module",
    "finit-module": "fenix-finit-module",
    "embedded-init-module": "fenix-embedded-init-module",
}


_REPO_MARKER = Path("payloads") / "memfd_oneliners" / "memfd_payload.pl"


def _is_fenix_repo_root(path: Path) -> bool:
    try:
        return (path / _REPO_MARKER).is_file()
    except OSError:
        return False


def project_root() -> Path:
    """
    Return the FENIX repository root (contains payloads/, bin/, examples/).

    When fenix is installed into site-packages (non-editable pip install),
    parents[2] from this file points at site-packages, not the clone. We walk
    upward from the package, cwd, and optional FENIX_ROOT until payloads exist.
    """
    env_root = os.environ.get("FENIX_ROOT")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        if _is_fenix_repo_root(root):
            return root
        raise FileNotFoundError(
            f"FENIX_ROOT={env_root!r} is not a FENIX repo root "
            f"(expected {_REPO_MARKER} under that directory)."
        )

    seen: set[Path] = set()
    anchors = [Path(__file__).resolve(), Path.cwd().resolve()]
    for anchor in anchors:
        for parent in (anchor, *anchor.parents):
            if parent in seen:
                continue
            seen.add(parent)
            if _is_fenix_repo_root(parent):
                return parent

    legacy = Path(__file__).resolve().parents[2]
    if _is_fenix_repo_root(legacy):
        return legacy

    raise FileNotFoundError(
        "Could not locate FENIX repository root (missing "
        f"{_REPO_MARKER}). Run from the cloned repo, set FENIX_ROOT=/path/to/FENIX, "
        "or reinstall with: pip install -e ."
    )


def helper_bin_dir() -> Path:
    env = os.environ.get("FENIX_BIN_DIR")
    if env:
        return Path(env)
    return project_root() / "bin"


def find_helper(name: str) -> Path:
    """Resolve a helper binary by logical name or executable basename."""
    basename = HELPER_NAMES.get(name, name)
    if not basename.startswith("fenix-"):
        basename = f"fenix-{basename}"

    candidates = [
        helper_bin_dir() / basename,
        project_root() / "bin" / basename,
        Path(shutil.which(basename) or ""),
    ]

    for path in candidates:
        if path and path.is_file() and os.access(path, os.X_OK):
            return path

    raise FileNotFoundError(
        f"Helper '{basename}' not found. Build with 'make helpers' or set FENIX_BIN_DIR."
    )


def run_helper(helper: str, args: list[str], *, env: dict[str, str] | None = None) -> int:
    """Run a compiled helper; return its exit code (raises on launch failure)."""
    if sys.platform != "linux":
        raise OSError("FENIX helpers require Linux.")

    binary = find_helper(helper)
    cmd = [str(binary), *args]
    result = subprocess.run(cmd, check=False, env=env)
    return int(result.returncode)


EXPECTED_HELPERS = (
    "fenix-memfd-exec",
    "fenix-memfd-script-exec",
    "fenix-memfd-self-reexec",
    "fenix-memfd-so-load",
    "fenix-shm-exec",
    "fenix-shm-so-load",
    "fenix-stdin-memexec",
    "fenix-pipe-exec",
    "fenix-proc-fd-exec",
    "fenix-lolbin-fd-exec",
    "fenix-deleted-exec",
    "fenix-init-module",
    "fenix-finit-module",
    "fenix-embedded-init-module",
)
