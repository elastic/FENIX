# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch B.V. licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""FENIX command-line interface."""

from __future__ import annotations

import sys
from typing import Optional

import typer

from fenix import __version__
from fenix.core.banner import print_banner, should_show_banner
from fenix.core.catalog import (
    QUICKSTART,
    format_technique_info,
    get_technique_help,
    list_technique_help,
    project_root,
)
from fenix.core import cleanup
from fenix.core.helpers import EXPECTED_HELPERS, helper_bin_dir
from fenix.core.lab_matrix import LabTier, build_lab_cases, default_tiers_for_flags
from fenix.core.cli_hints import resolve_fenix_cli_command, sudo_fenix_example
from fenix.core.lab_runner import (
    format_lab_report,
    lab_exit_code,
    run_lab_matrix,
)
from fenix.core.runner import run_from_config, run_from_options
from fenix.interpreters.registry import discover_installed, list_interpreter_names
from fenix.techniques import list_techniques

app = typer.Typer(
    name="fenix",
    help="FENIX — Fileless Execution for NIX (Linux lab PoC framework)",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

list_app = typer.Typer(help="List techniques or interpreters.")
app.add_typer(list_app, name="list")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"fenix {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    quiet: bool = typer.Option(
        False,
        "-q",
        "--quiet",
        help="Suppress the FENIX banner.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Lab framework for Linux fileless-execution PoCs. Run [bold]fenix help[/bold] to get started."""
    if should_show_banner(quiet):
        print_banner()


@app.command("help")
def help_cmd() -> None:
    """Show quick-start guide and command overview."""
    typer.echo(QUICKSTART)


@app.command("check")
def check_cmd() -> None:
    """Verify helpers, payloads, and environment."""
    root = project_root()
    bin_dir = helper_bin_dir()
    issues = 0

    typer.echo("FENIX environment check\n")

    if sys.platform != "linux":
        typer.echo("[yellow]! OS[/]  Not Linux — C helpers will not run on this host.")
        issues += 1
    else:
        typer.echo("[green]OK[/]  Linux host")

    if bin_dir.is_dir():
        present = {p.name for p in bin_dir.glob("fenix-*") if p.is_file()}
        missing = [h for h in EXPECTED_HELPERS if h not in present]
        if present and not missing:
            typer.echo(f"[green]OK[/]  Helpers in {bin_dir} ({len(EXPECTED_HELPERS)} binaries)")
        elif present:
            typer.echo(f"[yellow]!  [/]  Helpers in {bin_dir} — missing: {', '.join(missing)}")
            typer.echo("       Run: make helpers")
            issues += 1
        else:
            typer.echo(f"[red]FAIL[/]  No helpers in {bin_dir} — run: make helpers")
            issues += 1
    else:
        typer.echo(f"[red]FAIL[/]  Missing {bin_dir} — run: make helpers")
        issues += 1

    samples = [
        root / "payloads/hello_elf/hello",
        root / "payloads/sleep_elf/sleep",
        root / "payloads/scripts/hello.py",
    ]
    for path in samples:
        if path.is_file():
            typer.echo(f"[green]OK[/]  {path.relative_to(root)}")
        else:
            typer.echo(f"[yellow]!  [/]  {path.relative_to(root)} (run: make payloads)")

    typer.echo("")
    typer.echo(f"Techniques: {len(list_techniques())} registered")
    typer.echo(f"Examples:   {root / 'examples'}")
    typer.echo("")
    if issues:
        typer.echo("Fix issues above, then: export FENIX_BIN_DIR=$PWD/bin")
        raise typer.Exit(code=1)
    typer.echo("Ready. Try: fenix info memfd-exec")


@app.command("info")
def info_cmd(
    technique: str = typer.Argument(..., help="Technique id (e.g. memfd-exec)"),
) -> None:
    """Show options, telemetry notes, and example commands for one technique."""
    try:
        meta = get_technique_help(technique)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        typer.echo("Run 'fenix list techniques' for valid ids.", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(format_technique_info(meta))


@app.command("cleanup")
def cleanup_cmd(
    technique: Optional[str] = typer.Option(
        None,
        "--technique",
        "-t",
        help="Cleanup one technique module only (default: all)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="Show what would be removed without deleting",
    ),
    build: bool = typer.Option(
        False,
        "--build",
        help="Also run make clean (bin/ and built payloads)",
    ),
    list_scopes: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List technique ids with dedicated cleanup handlers",
    ),
) -> None:
    """Remove FENIX lab artifacts (/tmp, /dev/shm, loaded test LKM, persisted state)."""
    if list_scopes:
        typer.echo("Cleanup scopes:")
        typer.echo("  global   — /tmp/fenix-*, /dev/shm/fenix_*")
        for scope in cleanup.list_cleanup_scopes():
            typer.echo(f"  {scope}")
        typer.echo("\nRun: fenix cleanup")
        typer.echo("      fenix cleanup --technique lkm-load")
        return

    if technique:
        try:
            from fenix.techniques import get_technique

            get_technique(technique)
        except ValueError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        report = cleanup.cleanup_technique(technique, dry_run=dry_run)
        title = f"Cleanup: {technique}"
    else:
        report = cleanup.cleanup_all(dry_run=dry_run, include_build=build)
        title = "Cleanup: all"

    typer.echo(f"{title}" + (" (dry-run)" if dry_run else ""))
    typer.echo("")

    if not report.actions:
        typer.echo("Nothing to clean.")
        return

    for act in report.actions:
        if act.removed:
            status = "[green]removed[/]"
        elif act.detail == "dry-run":
            status = "[yellow]would remove[/]"
        elif "not loaded" in act.detail or "not found" in act.detail:
            status = "[dim]skip[/]"
        else:
            status = "[red]failed[/]"
        detail = f" — {act.detail}" if act.detail and act.detail != "dry-run" else ""
        typer.echo(f"{status} [{act.scope}] {act.action}: {act.target}{detail}")

    typer.echo("")
    typer.echo(
        f"Summary: {report.removed_count} removed, "
        f"{len(report.actions)} actions"
        + (f", {report.failed_count} failed" if report.failed_count else "")
    )

    if report.failed_count and not dry_run:
        raise typer.Exit(code=1)


@app.command("examples")
def examples_cmd() -> None:
    """List example YAML configs in examples/."""
    ex_dir = project_root() / "examples"
    readme = ex_dir / "README.md"
    if readme.is_file():
        typer.echo(f"Index: {readme}\n")
    if not ex_dir.is_dir():
        typer.echo("No examples/ directory found.", err=True)
        raise typer.Exit(code=1)
    for path in sorted(ex_dir.glob("*.yaml")):
        typer.echo(f"  {path.name}")
    typer.echo("\nRun: fenix run -c examples/<file>.yaml")
    typer.echo(
        "NOTE: fileless_staging_remote*.yaml are TEMPLATES "
        "(YOUR-LAB-HOST). They will not run until you edit the URL "
        "or switch remote_backend. See docs/STAGING_REMOTE.md"
    )


@app.command("run-all")
def run_all_cmd(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="List planned runs without executing",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Core + extended + lolbin + lkm (lkm still needs root). Does not upload to the internet.",
    ),
    with_lkm: bool = typer.Option(
        False,
        "--with-lkm",
        help="Include all lkm-load methods (requires root)",
    ),
    with_remote: bool = typer.Option(
        False,
        "--with-remote",
        help="Include fileless-staging --remote (requires FENIX_REMOTE_BACKEND or FENIX_REMOTE_UPLOAD_URL)",
    ),
    with_lolbin: bool = typer.Option(
        False,
        "--with-lolbin",
        help="Include optional lolbin-fd-exec variants (busybox, julia, erlang)",
    ),
    technique: Optional[str] = typer.Option(
        None,
        "--technique",
        "-t",
        help="Run only cases for this technique id",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast",
        help="Stop on first non-optional failure",
    ),
    list_cases: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List matrix cases for the selected tiers and exit",
    ),
    do_cleanup: bool = typer.Option(
        False,
        "--cleanup",
        help="Run fenix cleanup after the matrix (same process; no sudo shell needed for temps)",
    ),
) -> None:
    """
    Run the lab coverage matrix (all techniques / detection surfaces).

    Default: core tier only (~19 detonations). Use --full on a Linux lab VM with
    sudo for extended + lolbin + lkm (no internet upload). Afterward: fenix cleanup
    """
    tiers = default_tiers_for_flags(
        full=full,
        with_lkm=with_lkm,
        with_remote=with_remote,
        with_lolbin=with_lolbin,
    )

    if list_cases or dry_run:
        cases = build_lab_cases(tiers=tiers, technique_filter=technique)
        typer.echo(f"Lab matrix ({len(cases)} cases, tiers: {', '.join(sorted(t.value for t in tiers))})")
        typer.echo(f"{'CASE':<36} {'TIER':<10} {'TECHNIQUE':<22} NOTE")
        typer.echo("-" * 90)
        for c in cases:
            note = (c.note or "")[:28]
            typer.echo(f"{c.case_id:<36} {c.tier.value:<10} {c.technique:<22} {note}")
        if dry_run and not list_cases:
            typer.echo("\nDry-run only — re-run without --dry-run to detonate.")
        raise typer.Exit(0)

    if sys.platform != "linux":
        typer.echo("run-all requires Linux.", err=True)
        raise typer.Exit(code=1)

    typer.echo(
        f"Starting FENIX lab matrix (tiers: {', '.join(sorted(t.value for t in tiers))})",
        err=True,
    )
    fenix_cmd = resolve_fenix_cli_command()
    if LabTier.LKM in tiers and __import__("os").geteuid() != 0:
        typer.echo(
            "Warning: lkm tier selected but not root — those cases will be skipped.",
            err=True,
        )
        typer.echo(f"  {sudo_fenix_example('run-all --with-lkm')}", err=True)

    results = run_lab_matrix(
        tiers=tiers,
        technique_filter=technique,
        continue_on_error=not fail_fast,
    )
    typer.echo(format_lab_report(results))
    rc = lab_exit_code(results)

    if do_cleanup and not dry_run:
        typer.echo("\n[cleanup] Running lab cleanup...", err=True)
        report = cleanup.cleanup_all(dry_run=False)
        typer.echo(f"Cleanup: {report.removed_count} removed, {len(report.actions)} actions")
        if report.failed_count:
            typer.echo(
                f"Some cleanup steps failed — retry: {fenix_cmd} cleanup "
                f"(LKM: {sudo_fenix_example('cleanup -t lkm-load')})",
                err=True,
            )

    if not dry_run:
        typer.echo("\nDone. Review alerts in your SIEM.", err=True)
        if not do_cleanup:
            typer.echo(f"Then: {fenix_cmd} cleanup", err=True)
            if LabTier.LKM in tiers:
                typer.echo(f"  (if module still loaded: {sudo_fenix_example('cleanup -t lkm-load')})", err=True)

    raise typer.Exit(code=rc)


@list_app.command("techniques")
def list_techniques_cmd() -> None:
    """Show all techniques (use 'fenix info <id>' for details)."""
    typer.echo(f"{'TECHNIQUE':22} DESCRIPTION")
    typer.echo("-" * 60)
    for meta in list_technique_help():
        typer.echo(f"{meta.id:22} {meta.summary}")
    typer.echo("\nDetails: fenix info <technique>")


def _echo_staging_presets() -> None:
    from fenix.core.lab_staging import (
        get_lab_preset,
        lab_staging_base,
        list_lab_preset_ids,
        preset_url,
    )

    typer.echo(f"Base URL (FENIX_LAB_STAGING_BASE): {lab_staging_base()}")
    typer.echo("")
    typer.echo(f"{'PRESET':12} {'DECODE':8} {'EXECUTE':12} URL")
    typer.echo("-" * 72)
    for pid in list_lab_preset_ids():
        p = get_lab_preset(pid)
        typer.echo(f"{pid:12} {p.decode:8} {p.execute:12} {preset_url(p)}")
    typer.echo("")
    from fenix.core.remote_bin import list_remote_backends

    typer.echo("Remote upload is opt-in. FENIX does not pick a public host.")
    typer.echo("  backends: " + ", ".join(list_remote_backends()))
    typer.echo("  --remote --remote-backend put --remote-upload-url https://your-host/file")
    typer.echo("  --remote --remote-backend uguu   # only if you name a third-party adapter")
    typer.echo("  --lab-remote hello-b64           # download-only GitHub raw preset")
    typer.echo("Docs: docs/STAGING_REMOTE.md")


@app.command("staging-presets")
def staging_presets_cmd() -> None:
    """List fileless-staging --lab-remote presets and resolved URLs."""
    _echo_staging_presets()


@list_app.command("staging-presets")
def list_staging_presets_cmd() -> None:
    """Same as fenix staging-presets."""
    _echo_staging_presets()


@list_app.command("lolbins")
def list_lolbins_cmd() -> None:
    """Show LoLbins for lolbin-fd-exec and whether they are available."""
    from fenix.lolbins.registry import get_lolbin, list_lolbin_ids, resolve_lolbin_binary

    typer.echo(f"{'LOLBIN':10} KIND   DEFAULT PAYLOAD")
    typer.echo("-" * 56)
    for lid in list_lolbin_ids():
        spec = get_lolbin(lid)
        try:
            path = resolve_lolbin_binary(spec)
            status = path
        except FileNotFoundError:
            status = "(not installed)"
        typer.echo(f"{lid:10} {spec.payload_kind:5}  {spec.default_payload}")
        typer.echo(f"{'':10}        → {status}")
        if spec.install_hint and status == "(not installed)":
            typer.echo(f"{'':10}        install: {spec.install_hint}")
    typer.echo("\nMore: docs/LOLBINS_INSTALL.md")


@list_app.command("interpreters")
def list_interpreters_cmd() -> None:
    """Show interpreters and whether they are installed on PATH."""
    installed = {name: path for name, path in discover_installed()}
    typer.echo(f"{'NAME':10} PATH")
    typer.echo("-" * 40)
    for name in list_interpreter_names():
        if name in installed:
            typer.echo(f"{name:10} {installed[name]}")
        else:
            typer.echo(f"{name:10} (not on PATH)")


def _collect_run_options(**kwargs) -> dict:
    opts: dict = {}
    mapping = {
        "payload": kwargs.get("payload"),
        "name": kwargs.get("name"),
        "method": kwargs.get("method"),
        "argv0": kwargs.get("argv0"),
        "keep_fd_open": kwargs.get("keep_fd_open"),
        "source_file": kwargs.get("source_file"),
        "source_url": kwargs.get("source_url"),
        "lab_remote": kwargs.get("lab_remote"),
        "remote": kwargs.get("remote"),
        "remote_backend": kwargs.get("remote_backend"),
        "remote_upload_url": kwargs.get("remote_upload_url"),
        "remote_download_url": kwargs.get("remote_download_url"),
        "remote_fetch": kwargs.get("remote_fetch"),
        "remote_encode": kwargs.get("remote_encode"),
        "decode": kwargs.get("decode"),
        "decompress": kwargs.get("decompress"),
        "execute": kwargs.get("execute"),
        "path": kwargs.get("path"),
        "args": kwargs.get("args"),
        "interpreter": kwargs.get("interpreter"),
        "mode": kwargs.get("mode"),
        "code": kwargs.get("code"),
        "script": kwargs.get("script"),
        "module": kwargs.get("module"),
        "type": kwargs.get("exec_type"),
        "content": kwargs.get("content"),
        "unlink_after_open": kwargs.get("unlink_after_open"),
        "fchmod": kwargs.get("fchmod"),
        "ingest": kwargs.get("ingest"),
        "noexec_seal": kwargs.get("noexec_seal"),
        "unlink": kwargs.get("unlink"),
        "xor_key": kwargs.get("xor_key"),
        "tar_member": kwargs.get("tar_member"),
        "no_unlink": kwargs.get("no_unlink"),
        "symbol": kwargs.get("symbol"),
        "lolbin": kwargs.get("lolbin"),
        "bin": kwargs.get("bin"),
        "linker": kwargs.get("linker"),
        "keep_loaded": kwargs.get("keep_loaded"),
    }
    for key, value in mapping.items():
        if value is not None and value is not False:
            opts[key] = value
    if kwargs.get("no_explain"):
        opts["explain"] = False
    if kwargs.get("no_wait") or kwargs.get("wait") is False:
        opts["no_wait"] = True
    if kwargs.get("i_understand"):
        opts["i_understand_this_loads_kernel_code"] = True
    return opts


@app.command("run")
def run_cmd(
    technique: Optional[str] = typer.Argument(
        None,
        help="Technique id — run 'fenix list techniques' or 'fenix info <id>'",
    ),
    config: Optional[str] = typer.Option(
        None,
        "-c",
        "--config",
        help="YAML config file (alternative to technique + flags)",
    ),
    payload: Optional[str] = typer.Option(None, "--payload", help="[memfd/proc/pipe/deleted] ELF path"),
    name: Optional[str] = typer.Option(None, "--name", help="[memfd*] Anonymous file name"),
    method: Optional[str] = typer.Option(None, "--method", help="[memfd/proc/lkm] Execution or load method"),
    argv0: Optional[str] = typer.Option(
        None,
        "--argv0",
        help="[memfd/proc/interpreter-memfd] argv[0] masquerade (default fenix_payload)",
    ),
    keep_fd_open: bool = typer.Option(False, "--keep-fd-open", help="[memfd-exec] Keep memfd open"),
    source_file: Optional[str] = typer.Option(None, "--source-file", help="[staging] Local payload path"),
    source_url: Optional[str] = typer.Option(None, "--source-url", help="[staging] HTTP(S) raw URL (Pastebin raw, GitHub raw, …)"),
    lab_remote: Optional[str] = typer.Option(
        None,
        "--lab-remote",
        help="[fileless-staging] Pre-hosted URL preset: hello-b64 | hello-xor | hello-py",
    ),
    remote: bool = typer.Option(
        False,
        "--remote",
        help="[fileless-staging] Opt-in: upload --source-file, download it, then exec. Requires --remote-backend or --remote-upload-url.",
    ),
    remote_backend: Optional[str] = typer.Option(
        None,
        "--remote-backend",
        help="[fileless-staging] put | post | uguu | tmpfiles | catbox | pastebin (no default)",
    ),
    remote_upload_url: Optional[str] = typer.Option(
        None,
        "--remote-upload-url",
        help="[fileless-staging] URL for --remote-backend put/post (or FENIX_REMOTE_UPLOAD_URL)",
    ),
    remote_download_url: Optional[str] = typer.Option(
        None,
        "--remote-download-url",
        help="[fileless-staging] Override GET URL after upload (or FENIX_REMOTE_DOWNLOAD_URL)",
    ),
    remote_fetch: Optional[str] = typer.Option(
        None,
        "--remote-fetch",
        help="[fileless-staging] Download via: requests | curl | wget | python",
    ),
    remote_encode: Optional[str] = typer.Option(
        None,
        "--remote-encode",
        help="[fileless-staging] Upload encoding: auto | none | base64 (pastebin needs text)",
    ),
    decode: Optional[str] = typer.Option(None, "--decode", help="[staging] none | base64 | xor"),
    decompress: Optional[str] = typer.Option(
        None, "--decompress", help="[staging] none | gzip | tar"
    ),
    execute: Optional[str] = typer.Option(
        None, "--execute", help="[staging] memfd | interpreter"
    ),
    path: Optional[str] = typer.Option(None, "--path", help="[deleted-file-exec] Target path on disk"),
    args: Optional[str] = typer.Option(None, "--args", help="[deleted-file-exec] Payload arguments"),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="[deleted-file-exec] Wait for child"),
    interpreter: Optional[str] = typer.Option(
        None, "--interpreter", help="[interpreter|staging|pipe] Interpreter name"
    ),
    mode: Optional[str] = typer.Option(
        None,
        "--mode",
        help="[interpreter-exec] one-liner | stdin | script-file; "
        "[interpreter-memfd-exec] one-liner | script-file",
    ),
    code: Optional[str] = typer.Option(None, "--code", help="[interpreter|script] Inline code"),
    script: Optional[str] = typer.Option(None, "--script", help="[interpreter|memfd-script] Script path"),
    module: Optional[str] = typer.Option(None, "--module", help="[lkm-load] .ko module path"),
    i_understand: bool = typer.Option(
        False,
        "--i-understand-this-loads-kernel-code",
        help="[lkm-load] Required confirmation",
    ),
    keep_loaded: bool = typer.Option(
        False,
        "--keep-loaded",
        help="[lkm-load] Leave hello_lkm loaded after run (default: auto rmmod)",
    ),
    exec_type: Optional[str] = typer.Option(None, "--type", help="[pipe-exec] elf | script"),
    content: Optional[str] = typer.Option(
        None, "--content", help="[memfd-script|pipe] Inline script content"
    ),
    unlink_after_open: bool = typer.Option(
        False,
        "--unlink-after-open/--unlink",
        help="[proc-fd-exec] Unlink after open",
    ),
    fchmod: bool = typer.Option(False, "--fchmod", help="[memfd/stdin-memexec] fchmod 0755 before exec"),
    ingest: Optional[str] = typer.Option(
        None, "--ingest", help="[memfd-exec|shm-exec] write | sendfile"
    ),
    noexec_seal: bool = typer.Option(
        False,
        "--noexec-seal",
        help="[memfd-exec] Create memfd with MFD_NOEXEC_SEAL then attempt fchmod+exec (lab)",
    ),
    unlink: bool = typer.Option(
        False, "--unlink", help="[shm-exec] shm_unlink before exec (deleted shm path)"
    ),
    xor_key: Optional[str] = typer.Option(None, "--xor-key", help="[staging] XOR key"),
    tar_member: Optional[str] = typer.Option(None, "--tar-member", help="[staging] Tar member name"),
    no_unlink: bool = typer.Option(False, "--no-unlink", help="[memfd-self-reexec] Keep disk binary"),
    symbol: Optional[str] = typer.Option(None, "--symbol", help="[memfd-so-load] Symbol to call"),
    lolbin: Optional[str] = typer.Option(
        None,
        "--lolbin",
        help="[lolbin-fd-exec] ld-linux | busybox | julia | erlang",
    ),
    bin: Optional[str] = typer.Option(
        None,
        "--bin",
        help="[lolbin-fd-exec] Override LoLbin binary (e.g. /lib64/ld-linux-x86-64.so.2)",
    ),
    linker: Optional[str] = typer.Option(
        None,
        "--linker",
        help="[lolbin-fd-exec] Alias for --bin (ld-linux path)",
    ),
    no_explain: bool = typer.Option(
        False,
        "--no-explain",
        "--suppress-explain",
        help="Skip syscall walkthrough (printed by default before each run)",
    ),
) -> None:
    """
    Run a fileless-execution technique.

    [bold]Getting started[/bold]

      fenix info memfd-exec          Technique-specific help
      fenix run -c examples/memfd_exec.yaml
      fenix run memfd-exec --payload payloads/hello_elf/hello
      fenix run memfd-exec --payload payloads/hello_elf/hello --no-explain -q

    Use [bold]fenix help[/bold] for the full command list.
    """
    try:
        if config:
            if technique:
                typer.echo("Use either a technique name or -c/--config, not both.", err=True)
                raise typer.Exit(code=2)
            rc = run_from_config(config)
        else:
            if not technique:
                typer.echo("Provide a technique name or -c/--config.", err=True)
                typer.echo("", err=True)
                typer.echo("  fenix list techniques", err=True)
                typer.echo("  fenix info memfd-exec", err=True)
                typer.echo("  fenix run -c examples/memfd_exec.yaml", err=True)
                raise typer.Exit(code=2)

            opts = _collect_run_options(
                payload=payload,
                name=name,
                method=method,
                argv0=argv0,
                keep_fd_open=keep_fd_open,
                source_file=source_file,
                source_url=source_url,
                lab_remote=lab_remote,
                remote=remote,
                remote_backend=remote_backend,
                remote_upload_url=remote_upload_url,
                remote_download_url=remote_download_url,
                remote_fetch=remote_fetch,
                remote_encode=remote_encode,
                decode=decode,
                decompress=decompress,
                execute=execute,
                path=path,
                args=args,
                wait=wait,
                interpreter=interpreter,
                mode=mode,
                code=code,
                script=script,
                module=module,
                i_understand=i_understand,
                keep_loaded=keep_loaded,
                exec_type=exec_type,
                content=content,
                unlink_after_open=unlink_after_open,
                fchmod=fchmod,
                ingest=ingest,
                noexec_seal=noexec_seal,
                unlink=unlink,
                xor_key=xor_key,
                tar_member=tar_member,
                no_unlink=no_unlink,
                symbol=symbol,
                lolbin=lolbin,
                bin=bin,
                linker=linker,
                no_explain=no_explain,
            )

            rc = run_from_options(technique, opts)
    except typer.Exit:
        raise
    except ValueError as exc:
        typer.echo(f"Cannot run{f' {technique}' if technique else ''}:", err=True)
        for msg in str(exc).split("; "):
            typer.echo(f"  - {msg}", err=True)
        if technique and technique in {m.id for m in list_technique_help()}:
            typer.echo(f"\nTry: fenix info {technique}", err=True)
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        typer.echo(f"Error: {exc}", err=True)
        if technique and technique in {m.id for m in list_technique_help()}:
            typer.echo(f"Hint: fenix info {technique}", err=True)
        raise typer.Exit(code=1) from exc

    raise typer.Exit(code=rc)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
