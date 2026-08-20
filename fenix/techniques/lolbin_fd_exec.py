"""lolbin-fd-exec — memfd payload executed via LoLbin + /proc/self/fd/N."""

from __future__ import annotations

from typing import Any

from fenix.core.helpers import run_helper
from fenix.core.payload import resolve_payload, resolve_script
from fenix.lolbins.registry import get_lolbin, resolve_lolbin_binary
from fenix.techniques import register


@register("lolbin-fd-exec", "Execute via LoLbin and /proc/self/fd/N (ld-linux, busybox, …)")
def run_lolbin_fd_exec(options: dict[str, Any]) -> int:
    lolbin_id = options.get("lolbin")
    if not lolbin_id:
        raise ValueError("lolbin-fd-exec requires --lolbin (ld-linux, busybox, julia, erlang)")

    spec = get_lolbin(str(lolbin_id))
    payload = options.get("payload")
    if not payload:
        payload = spec.default_payload

    if spec.payload_kind == "elf":
        path = resolve_payload(payload)
    else:
        path = resolve_script(payload)

    name = options.get("name") or "fenix_lolbin"
    binary = options.get("bin") or options.get("linker")
    try:
        bin_path = str(binary) if binary else resolve_lolbin_binary(spec)
    except FileNotFoundError as exc:
        raise ValueError(str(exc)) from exc

    args = [
        "--payload",
        str(path),
        "--name",
        str(name),
        "--lolbin",
        spec.id,
        "--bin",
        bin_path,
    ]
    return run_helper("lolbin-fd-exec", args)
