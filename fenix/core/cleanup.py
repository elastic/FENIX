"""Lab artifact cleanup: registered temps, persisted run state, and per-technique sweeps."""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Literal

from fenix.core.helpers import project_root

ArtifactKind = Literal["path", "shm", "kmod", "temp"]

# Orphan patterns from FENIX helpers / examples (avoid broad fenix-* — too greedy).
TMP_GLOB_PATTERNS = (
    "fenix-staged-*",
    "fenix-procfd-*",
    "fenix-memfd-*",
    "fenix_smoke*",
    "fenix_sleep*",
    "fenix_cleanup*",
)
SHM_GLOB_PATTERNS = ("fenix_shm_*", "fenix_shm_payload", "fenix_shm_module")
DEFAULT_KMOD_NAMES = ("hello_lkm",)

_registered: list[Path] = []
_registered_technique: list[str | None] = []

_artifacts: list[Artifact] = []

CleanupFn = Callable[[bool, str | None], list["CleanupAction"]]


@dataclass
class Artifact:
    technique: str
    kind: ArtifactKind
    value: str


@dataclass
class CleanupAction:
    scope: str  # technique id or "global"
    action: str
    target: str
    removed: bool
    detail: str = ""


@dataclass
class CleanupReport:
    actions: list[CleanupAction] = field(default_factory=list)

    @property
    def removed_count(self) -> int:
        return sum(1 for a in self.actions if a.removed)

    @property
    def failed_count(self) -> int:
        skips = ("dry-run", "not found", "not loaded")
        return sum(
            1
            for a in self.actions
            if not a.removed
            and a.detail
            and not any(s in a.detail.lower() for s in skips)
        )


def _state_file() -> Path:
    path = project_root() / ".fenix" / "artifacts.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_persisted() -> None:
    global _artifacts
    path = _state_file()
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        _artifacts = [Artifact(**item) for item in data.get("artifacts", [])]
    except (json.JSONDecodeError, TypeError, KeyError):
        _artifacts = []


def _save_persisted() -> None:
    path = _state_file()
    payload = {"artifacts": [asdict(a) for a in _artifacts]}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def note_artifact(technique: str, kind: ArtifactKind, value: str) -> None:
    """Record a lab artifact for later ``fenix cleanup`` (persisted under .fenix/)."""
    entry = Artifact(technique=technique, kind=kind, value=value)
    if not any(a.technique == entry.technique and a.kind == entry.kind and a.value == entry.value for a in _artifacts):
        _artifacts.append(entry)
        _save_persisted()


def clear_persisted_state() -> None:
    """Remove the persisted artifact registry file."""
    global _artifacts
    _artifacts = []
    path = _state_file()
    if path.is_file():
        path.unlink()


def temp_path(prefix: str = "fenix-", suffix: str = "", technique: str | None = None) -> Path:
    """Create a temp file under /tmp and register it for session cleanup."""
    fd, name = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir="/tmp")
    os.close(fd)
    path = Path(name)
    register(path, technique=technique)
    if technique:
        note_artifact(technique, "temp", str(path))
    return path


def register(path: Path, technique: str | None = None) -> None:
    if path not in _registered:
        _registered.append(path)
        _registered_technique.append(technique)


def remove(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
        removed = not path.exists()
    except OSError:
        removed = False
    if path in _registered:
        idx = _registered.index(path)
        _registered.pop(idx)
        _registered_technique.pop(idx)
    return removed


def _record(
    results: list[CleanupAction],
    scope: str,
    action: str,
    target: str,
    removed: bool,
    detail: str = "",
) -> None:
    results.append(
        CleanupAction(scope=scope, action=action, target=target, removed=removed, detail=detail)
    )


def _chmod_tree(path: Path) -> None:
    """Best-effort permission fix before removing lab temp trees."""
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            try:
                os.chmod(os.path.join(root, name), 0o700)
            except OSError:
                pass
        for name in dirs:
            try:
                os.chmod(os.path.join(root, name), 0o700)
            except OSError:
                pass
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _unlink_path(path: Path, dry_run: bool) -> bool:
    if not path.exists():
        return False
    if dry_run:
        return False
    try:
        if path.is_dir():
            _chmod_tree(path)
            shutil.rmtree(path)
        else:
            path.unlink()
        return not path.exists()
    except OSError:
        return False


def _shm_disk_path(name: str) -> Path:
    clean = name.lstrip("/")
    return Path("/dev/shm") / clean


def cleanup_registered(dry_run: bool = False, technique: str | None = None) -> list[CleanupAction]:
    """Remove paths registered via ``register`` / ``temp_path`` in this process."""
    results: list[CleanupAction] = []
    for path, tech in zip(list(_registered), list(_registered_technique)):
        if technique and tech != technique:
            continue
        scope = tech or "global"
        if dry_run:
            if path.exists():
                _record(results, scope, "unlink", str(path), False, "dry-run")
            continue
        removed = remove(path)
        _record(
            results,
            scope,
            "unlink",
            str(path),
            removed,
            "" if removed else "not found or failed",
        )
    return results


def cleanup_glob_orphans(dry_run: bool = False, technique: str | None = None) -> list[CleanupAction]:
    """Sweep known FENIX orphan paths under /tmp and /dev/shm."""
    if technique and technique not in ("global", "fileless-staging", "proc-fd-exec", "shm-exec", "shm-so-load"):
        return []

    results: list[CleanupAction] = []
    tmp_root = Path("/tmp")
    if tmp_root.is_dir():
        for pattern in TMP_GLOB_PATTERNS:
            for path in tmp_root.glob(pattern):
                if dry_run:
                    _record(results, "global", "glob-tmp", str(path), False, "dry-run")
                else:
                    _record(
                        results,
                        "global",
                        "glob-tmp",
                        str(path),
                        _unlink_path(path, dry_run=False),
                    )

    shm_root = Path("/dev/shm")
    if shm_root.is_dir():
        for pattern in SHM_GLOB_PATTERNS:
            for path in shm_root.glob(pattern):
                if dry_run:
                    _record(results, "global", "glob-shm", str(path), False, "dry-run")
                else:
                    _record(
                        results,
                        "global",
                        "glob-shm",
                        str(path),
                        _unlink_path(path, dry_run=False),
                    )
    return results


def record_run_artifacts(technique: str, options: dict) -> None:
    """Persist likely leftover paths from a technique run (for ``fenix cleanup``)."""
    path = options.get("path")
    if technique == "deleted-file-exec" and path:
        note_artifact(technique, "path", str(path))

    name = options.get("name")
    if technique in ("shm-exec", "shm-so-load") and name:
        note_artifact(technique, "shm", str(name).lstrip("/"))

    if technique == "lkm-load" and (
        options.get("keep_loaded") or options.get("keep-loaded")
    ):
        method = options.get("method") or "init_module"
        module = options.get("module")
        if method == "embedded-init-module" or not module:
            note_artifact(technique, "kmod", "hello_lkm")
        else:
            mod_path = Path(str(module))
            kmod = mod_path.stem
            if kmod.endswith(".ko"):
                kmod = kmod[:-3]
            note_artifact(technique, "kmod", kmod)


def cleanup_persisted_artifacts(dry_run: bool = False, technique: str | None = None) -> list[CleanupAction]:
    """Apply cleanup for artifacts saved from prior ``fenix run`` invocations."""
    global _artifacts
    _load_persisted()
    results: list[CleanupAction] = []
    remaining: list[Artifact] = []

    for art in _artifacts:
        if technique and art.technique != technique:
            remaining.append(art)
            continue

        if art.kind in ("path", "temp"):
            path = Path(art.value)
            if dry_run:
                if path.exists():
                    _record(results, art.technique, "artifact-path", str(path), False, "dry-run")
                continue
            removed = _unlink_path(path, dry_run=False)
            _record(
                results,
                art.technique,
                "artifact-path",
                str(path),
                removed,
                "" if removed else "not found",
            )
        elif art.kind == "shm":
            path = _shm_disk_path(art.value)
            if dry_run:
                if path.exists():
                    _record(results, art.technique, "artifact-shm", str(path), False, "dry-run")
                continue
            removed = _unlink_path(path, dry_run=False)
            _record(results, art.technique, "artifact-shm", str(path), removed, "")
        elif art.kind == "kmod":
            results.extend(_cleanup_kernel_modules(dry_run, art.technique, {art.value}))
        else:
            remaining.append(art)

    if not dry_run:
        if technique:
            _artifacts = remaining
            _save_persisted()
        else:
            clear_persisted_state()

    return results


def rmmod_module(name: str) -> tuple[bool, str]:
    """
    Try to unload a kernel module by name.
    Returns (True, reason) on success or if the module was not loaded.
    """
    try:
        proc = subprocess.run(
            ["rmmod", name],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "rmmod not found"

    if proc.returncode == 0:
        return True, "unloaded"

    err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
    lowered = err.lower()
    if "not found" in lowered or "not currently loaded" in lowered:
        return True, "not loaded"
    return False, err


def _cleanup_kernel_modules(
    dry_run: bool,
    scope: str,
    names: set[str] | None = None,
) -> list[CleanupAction]:
    results: list[CleanupAction] = []
    mod_names = set(names or ()) | set(DEFAULT_KMOD_NAMES)

    for name in sorted(mod_names):
        target = f"kernel module {name}"
        if dry_run:
            _record(results, scope, "rmmod", target, False, "dry-run")
            continue
        ok, detail = rmmod_module(name)
        if ok and detail == "unloaded":
            _record(results, scope, "rmmod", target, True, detail)
        elif ok:
            _record(results, scope, "rmmod", target, False, detail)
        else:
            _record(results, scope, "rmmod", target, False, detail)
    return results


def _handler_lkm_load(dry_run: bool, technique: str | None) -> list[CleanupAction]:
    if technique and technique != "lkm-load":
        return []
    names = {a.value for a in _artifacts if a.kind == "kmod" and a.technique == "lkm-load"}
    return _cleanup_kernel_modules(dry_run, "lkm-load", names)


def _handler_deleted_file_exec(dry_run: bool, technique: str | None) -> list[CleanupAction]:
    if technique and technique not in ("deleted-file-exec",):
        return []
    results: list[CleanupAction] = []
    candidates: set[Path] = set()

    for art in _artifacts:
        if art.technique == "deleted-file-exec" and art.kind == "path":
            candidates.add(Path(art.value))

    for pattern in ("fenix_sleep", "fenix_smoke_del", "fenix_*"):
        for path in Path("/tmp").glob(pattern):
            candidates.add(path)

    for path in sorted(candidates):
        if dry_run:
            if path.exists():
                _record(results, "deleted-file-exec", "path", str(path), False, "dry-run")
            continue
        _record(
            results,
            "deleted-file-exec",
            "path",
            str(path),
            _unlink_path(path, dry_run=False),
        )
    return results


def _handler_shm(dry_run: bool, technique: str | None) -> list[CleanupAction]:
    if technique and technique not in ("shm-exec", "shm-so-load", None):
        return []
    scope = technique or "shm-exec"
    results: list[CleanupAction] = []

    for art in _artifacts:
        if art.kind == "shm" and (not technique or art.technique == technique):
            path = _shm_disk_path(art.value)
            if dry_run:
                if path.exists():
                    _record(results, art.technique, "shm", str(path), False, "dry-run")
                continue
            _record(results, art.technique, "shm", str(path), _unlink_path(path, dry_run=False))

    return results


_TECHNIQUE_HANDLERS: dict[str, CleanupFn] = {
    "lkm-load": _handler_lkm_load,
    "deleted-file-exec": _handler_deleted_file_exec,
    "shm-exec": _handler_shm,
    "shm-so-load": _handler_shm,
}


def cleanup_build(dry_run: bool = False) -> list[CleanupAction]:
    """Run ``make clean`` in the project root (helpers + payload build artifacts)."""
    results: list[CleanupAction] = []
    root = project_root()
    makefile = root / "Makefile"
    if not makefile.is_file():
        _record(results, "global", "make-clean", str(root), False, "no Makefile")
        return results

    if dry_run:
        _record(results, "global", "make-clean", str(root), False, "dry-run")
        return results

    proc = subprocess.run(
        ["make", "clean"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    ok = proc.returncode == 0
    detail = (proc.stderr or proc.stdout or "").strip()[:200]
    _record(results, "global", "make-clean", str(root), ok, detail if not ok else "ok")
    return results


def cleanup_technique(technique_id: str, dry_run: bool = False) -> CleanupReport:
    """Cleanup artifacts for one technique module."""
    _load_persisted()
    report = CleanupReport()
    report.actions.extend(cleanup_registered(dry_run=dry_run, technique=technique_id))
    report.actions.extend(cleanup_persisted_artifacts(dry_run=dry_run, technique=technique_id))

    handler = _TECHNIQUE_HANDLERS.get(technique_id)
    if handler:
        report.actions.extend(handler(dry_run, technique_id))

    if technique_id in ("shm-exec", "shm-so-load"):
        report.actions.extend(cleanup_glob_orphans(dry_run=dry_run, technique=technique_id))
    if technique_id == "deleted-file-exec":
        for path in Path("/tmp").glob("fenix*"):
            if dry_run:
                report.actions.append(
                    CleanupAction("deleted-file-exec", "glob", str(path), False, "dry-run")
                )
            else:
                report.actions.append(
                    CleanupAction(
                        "deleted-file-exec",
                        "glob",
                        str(path),
                        _unlink_path(path, dry_run=False),
                    )
                )

    return report


def cleanup_all(
    dry_run: bool = False,
    include_build: bool = False,
    clear_state: bool = True,
) -> CleanupReport:
    """Full lab cleanup: registered temps, persisted artifacts, orphans, and kernel module."""
    _load_persisted()
    report = CleanupReport()

    report.actions.extend(cleanup_registered(dry_run=dry_run))
    report.actions.extend(cleanup_persisted_artifacts(dry_run=dry_run))
    report.actions.extend(cleanup_glob_orphans(dry_run=dry_run))

    for handler in _TECHNIQUE_HANDLERS.values():
        report.actions.extend(handler(dry_run, None))

    if include_build:
        report.actions.extend(cleanup_build(dry_run=dry_run))

    if not dry_run and clear_state:
        clear_persisted_state()

    return report


def cleanup_session() -> None:
    """Remove only in-process registered paths (called after each run)."""
    cleanup_registered(dry_run=False)


def list_cleanup_scopes() -> list[str]:
    """Technique ids with dedicated cleanup handlers, plus ``global``."""
    return sorted(set(_TECHNIQUE_HANDLERS.keys()) | {"global"})


atexit.register(cleanup_session)
