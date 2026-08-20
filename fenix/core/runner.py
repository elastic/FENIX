"""Dispatch technique runs from CLI options or YAML config."""

from __future__ import annotations

import sys
from typing import Any

from fenix.core import cleanup
from fenix.core.catalog import assert_catalog_in_sync, validate_options
from fenix.core.explain import print_technique_explain
from fenix.core.config import config_get, load_config
import fenix.techniques  # noqa: F401 — register built-in techniques

from fenix.techniques import run_technique


def _resolve_explain(opts: dict[str, Any]) -> bool:
    """Walkthrough on by default; YAML/CLI can set explain: false or no_explain."""
    for key in ("no_explain", "no-explain", "suppress_explain", "suppress-explain"):
        if opts.pop(key, None):
            return False
    explain = opts.pop("explain", None)
    if explain is False:
        return False
    return True


def _normalize_options(options: dict[str, Any]) -> dict[str, Any]:
    """Normalize kebab-case keys from YAML to snake_case for Python code."""
    normalized: dict[str, Any] = {}
    for key, value in options.items():
        normalized[key.replace("-", "_")] = value
    return normalized


def run_from_config(config_path: str) -> int:
    data = load_config(config_path)
    technique = config_get(data, "technique")
    if not technique:
        raise ValueError("Config missing 'technique'")
    options = {k: v for k, v in data.items() if k != "technique"}
    return run_from_options(str(technique), _normalize_options(options))


def run_from_options(technique: str, options: dict[str, Any]) -> int:
    assert_catalog_in_sync()

    if sys.platform != "linux":
        print(
            "Warning: FENIX is designed for Linux. Helper execution may fail on this platform.",
            file=sys.stderr,
        )

    opts = _normalize_options(options)
    if technique == "fileless-staging":
        from fenix.core.lab_staging import apply_lab_preset
        from fenix.core.remote_bin import apply_remote_upload

        opts = apply_lab_preset(opts)
        opts = apply_remote_upload(opts)
    if technique == "interpreter-memfd-exec":
        from fenix.core.memfd_payloads import prepare_interpreter_memfd_exec

        opts = prepare_interpreter_memfd_exec(opts)
    errors = validate_options(technique, opts)
    if errors:
        raise ValueError("; ".join(errors))

    explain = _resolve_explain(opts)

    cleanup.record_run_artifacts(technique, opts)
    if explain:
        print_technique_explain(technique, opts)

    try:
        return run_technique(technique, opts)
    finally:
        cleanup.cleanup_session()
