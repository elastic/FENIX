"""deleted-file-exec — Execute payload then unlink path on disk."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload
from fenix.techniques import register


@register("deleted-file-exec", "Execute from disk and unlink the backing file")
def run_deleted_file_exec(options: dict[str, Any]) -> int:
    payload = options.get("payload")
    target_path = options.get("path")
    if not payload or not target_path:
        raise ValueError("deleted-file-exec requires --payload and --path")

    path = resolve_payload(payload)
    extra_args = options.get("args")
    wait = options.get("wait", True)
    if options.get("no_wait"):
        wait = False

    args = [
        "--payload",
        str(path),
        "--path",
        str(target_path),
    ]

    if extra_args is not None:
        args.extend(["--args", str(extra_args)])

    args.append("--wait" if wait else "--no-wait")

    from fenix.core import cleanup

    cleanup.note_artifact("deleted-file-exec", "path", str(target_path))
    return run_helper("deleted-exec", args)
