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
"""Technique catalog: help text, examples, and option validation for the CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from fenix.core.helpers import project_root


@dataclass(frozen=True)
class TechniqueHelp:
    id: str
    summary: str
    telemetry: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    example_cli: str
    example_config: str | None = None
    notes: str | None = None


TECHNIQUES: dict[str, TechniqueHelp] = {
    "memfd-exec": TechniqueHelp(
        id="memfd-exec",
        summary="Execute an ELF from an anonymous memfd.",
        telemetry="memfd_create, write payload, exec via /proc/self/fd, fexecve, or execveat",
        required=("payload",),
        optional=("name", "method", "argv0", "keep_fd_open", "fchmod", "ingest", "noexec_seal"),
        example_cli=(
            "fenix run memfd-exec --payload payloads/hello_elf/hello "
            "--method procfs-fd --name fenix_payload"
        ),
        example_config="examples/memfd_exec.yaml",
        notes=(
            "Methods: procfs-fd (default), fexecve, execveat. "
            "ingest: write (default) | sendfile. "
            "--fchmod for sympy-dev-style runs; --noexec-seal for vm.memfd_noexec lab (see docs/MEMFD_NOEXEC_LAB.md)."
        ),
    ),
    "memfd-script-exec": TechniqueHelp(
        id="memfd-script-exec",
        summary="Execute a script from an anonymous memfd.",
        telemetry="memfd_create with script bytes; shebang or interpreter + /proc/self/fd/N",
        required=(),  # script OR code
        optional=("script", "code", "interpreter", "method", "name"),
        example_cli=(
            "fenix run memfd-script-exec --script payloads/scripts/hello_shebang.sh "
            "--method shebang"
        ),
        example_config="examples/memfd_script_shebang.yaml",
        notes=(
            "Requires --script or --code. Methods: shebang, interpreter-procfs, fexecve-interpreter. "
            "interpreter-procfs needs a script for that language (e.g. hello.py for python3, hello.awk for awk); "
            "hello_shebang.sh is for shebang or sh/bash only. Awk needs -f (helper adds it). "
            "Node: use shebang + hello.js (not interpreter-procfs)."
        ),
    ),
    "memfd-self-reexec": TechniqueHelp(
        id="memfd-self-reexec",
        summary="Copy /proc/self/exe to memfd, unlink disk binary, re-execute (QLNX-style).",
        telemetry="read /proc/self/exe, memfd_create, unlink, execveat or procfs re-exec",
        required=(),
        optional=("name", "method", "argv0", "no_unlink"),
        example_cli="fenix run memfd-self-reexec --method execveat",
        example_config="examples/memfd_self_reexec.yaml",
        notes=(
            "No --payload: copies fenix-memfd-self-reexec from /proc/self/exe into memfd, then re-execs. "
            "Default unlinks that helper; restore with make helpers. "
            "fenix run-all passes --no-unlink so a following sudo --full still finds the binary. "
            "Success = stderr line re-exec from memfd complete (/memfd:...)."
        ),
    ),
    "memfd-so-load": TechniqueHelp(
        id="memfd-so-load",
        summary="Load a shared library from memfd via dlopen (reflective .so PoC).",
        telemetry="memfd_create, dlopen(/proc/self/fd/N), dlsym, benign symbol call",
        required=("module",),
        optional=("symbol", "name"),
        example_cli=(
            "fenix run memfd-so-load --module payloads/hello_so/hello_so.so "
            "--symbol fenix_hello"
        ),
        example_config="examples/memfd_so_load.yaml",
    ),
    "shm-exec": TechniqueHelp(
        id="shm-exec",
        summary="Execute ELF via shm_open on tmpfs (/dev/shm), not memfd_create.",
        telemetry="shm_open, ftruncate, write/sendfile, execve or fexecve on /dev/shm path",
        required=("payload",),
        optional=("name", "method", "ingest", "unlink"),
        example_cli=(
            "fenix run shm-exec --payload payloads/hello_elf/hello "
            "--method fexecve --ingest sendfile"
        ),
        example_config="examples/shm_exec.yaml",
        notes=(
            "Methods: procfs-fd, fexecve. Useful on older kernels and noexec /dev/shm. "
            "Without --unlink the object stays under /dev/shm; a later root shm_open can "
            "fail with Permission denied (sticky dir). Use --unlink or fenix cleanup."
        ),
    ),
    "shm-so-load": TechniqueHelp(
        id="shm-so-load",
        summary="dlopen a .so from POSIX shared memory (/dev/shm).",
        telemetry="shm_open, dlopen(/dev/shm/...), dlsym — no memfd_create",
        required=("module",),
        optional=("symbol", "name"),
        example_cli=(
            "fenix run shm-so-load --module payloads/hello_so/hello_so.so "
            "--symbol fenix_hello"
        ),
        example_config="examples/shm_so_load.yaml",
    ),
    "stdin-memexec": TechniqueHelp(
        id="stdin-memexec",
        summary="Read ELF from stdin (or --payload file) into memfd and execute.",
        telemetry="read stdin, memfd_create, write, execveat/fexecve (memexec-style)",
        required=(),
        optional=("payload", "name", "method", "fchmod"),
        example_cli=(
            "cat payloads/hello_elf/hello | fenix run stdin-memexec --method execveat"
        ),
        example_config="examples/stdin_memexec.yaml",
        notes="Default method execveat. Pipe a benign ELF or pass --payload for file-backed lab runs.",
    ),
    "fileless-staging": TechniqueHelp(
        id="fileless-staging",
        summary="Fetch, transform, and execute a payload (memfd ELF or interpreter).",
        telemetry="HTTP/file read, decode/decompress, temp file under /tmp/fenix-*, backend exec",
        required=(),  # source_file OR source_url
        optional=(
            "source_file",
            "source_url",
            "lab_remote",
            "remote",
            "remote_backend",
            "remote_upload_url",
            "remote_download_url",
            "remote_fetch",
            "remote_encode",
            "decode",
            "decompress",
            "xor_key",
            "tar_member",
            "execute",
            "method",
            "interpreter",
            "mode",
            "fchmod",
            "ingest",
            "noexec_seal",
        ),
        example_cli=(
            "fenix run fileless-staging --source-file payloads/hello_elf/hello "
            "--remote --remote-backend put --remote-upload-url https://your-lab-host/hello --execute memfd --method procfs-fd"
        ),
        example_config="examples/fileless_staging_http_b64.yaml",
        notes=(
            "decode: none|base64|xor. decompress: none|gzip|tar (tar needs --tar-member). "
            "Remote: --source-url, --lab-remote, or opt-in --remote with --remote-backend "
            "(put/post + --remote-upload-url, or a named adapter). No default public host. "
            "--remote-fetch: requests|curl|wget|python. fenix staging-presets. docs/STAGING_REMOTE.md"
        ),
    ),
    "pipe-exec": TechniqueHelp(
        id="pipe-exec",
        summary="Execute an ELF via pipe+fexecve, or feed a script to an interpreter on stdin.",
        telemetry="pipe(), write payload, fexecve (elf) or interpreter stdin (script)",
        required=("type",),
        optional=("payload", "interpreter", "script", "code"),
        example_cli="fenix run pipe-exec --type elf --payload payloads/hello_elf/hello",
        example_config="examples/pipe_exec_elf.yaml",
        notes=(
            "type=elf needs --payload. fexecve from pipe often EPERM on Linux 5.x+ (syscall lab still valid). "
            "type=script feeds interpreter on stdin — usually works."
        ),
    ),
    "proc-fd-exec": TechniqueHelp(
        id="proc-fd-exec",
        summary="Execute via open file descriptor (not memfd_create).",
        telemetry="open payload, optional unlink, execve /proc/self/fd or fexecve",
        required=("payload",),
        optional=("method", "argv0", "unlink_after_open"),
        example_cli=(
            "fenix run proc-fd-exec --payload payloads/hello_elf/hello "
            "--method fexecve --unlink-after-open"
        ),
        example_config="examples/proc_fd_exec.yaml",
        notes="Methods: procfs-fd, fexecve, execveat.",
    ),
    "deleted-file-exec": TechniqueHelp(
        id="deleted-file-exec",
        summary="Copy payload to a path, execute, unlink backing file while process runs.",
        telemetry="write path, fork, open+unlink+fexecve in child, deleted path on disk",
        required=("payload", "path"),
        optional=("args", "wait", "no_wait"),
        example_cli=(
            "fenix run deleted-file-exec --payload payloads/sleep_elf/sleep "
            "--path /tmp/fenix_sleep --args 5 --wait"
        ),
        example_config="examples/deleted_file_exec.yaml",
    ),
    "interpreter-exec": TechniqueHelp(
        id="interpreter-exec",
        summary="Run code through an installed interpreter (no ELF payload).",
        telemetry="python3/bash/perl/etc. subprocess; one-liner, stdin, or script-file mode",
        required=("interpreter", "mode"),
        optional=("code", "script"),
        example_cli=(
            'fenix run interpreter-exec --interpreter python3 --mode one-liner '
            '--code \'print("hello from fenix")\''
        ),
        example_config="examples/interpreter_oneliner.yaml",
        notes="Modes: one-liner, stdin, script-file. Run 'fenix list interpreters' for PATH status.",
    ),
    "interpreter-memfd-exec": TechniqueHelp(
        id="interpreter-memfd-exec",
        summary="Interpreter memfd loader: -e/-c one-liner or memfd_payload.* script file.",
        telemetry=(
            "python3 -c / perl -e / php -r with memfd+syscall in argv; or "
            "python3 …/memfd_payload.py; memfd_create; exec /proc/self/fd/N"
        ),
        required=("interpreter",),
        optional=("mode", "payload", "argv0", "script"),
        example_cli=(
            "fenix run interpreter-memfd-exec --interpreter perl --mode one-liner"
        ),
        example_config="examples/interpreter_memfd_perl_oneliner.yaml",
        notes=(
            "Modes: one-liner (default) | script-file. Templates: payloads/memfd_oneliners/memfd_payload.* "
            "Interpreters: perl, python3, ruby, php. Docs: docs/INTERPRETER_MEMFD.md"
        ),
    ),
    "lolbin-fd-exec": TechniqueHelp(
        id="lolbin-fd-exec",
        summary="Run ELF or script from memfd via LoLbin + /proc/self/fd/N.",
        telemetry="memfd_create, write, execve(ld-linux|busybox|julia|escript, /proc/self/fd/N)",
        required=("lolbin",),
        optional=("payload", "name", "bin", "linker"),
        example_cli=(
            "fenix run lolbin-fd-exec --lolbin ld-linux "
            "--payload payloads/hello_elf/hello"
        ),
        example_config="examples/lolbin_ld_linux.yaml",
        notes=(
            "lolbin: ld-linux, busybox, julia, erlang (escript). "
            "Default payloads per lolbin if --payload omitted. Install: docs/LOLBINS_INSTALL.md "
            "(erlang apt package, not escript; julia often via snap). "
            "Detection: process.name is often the LoLbin, args contain /proc/self/fd/N."
        ),
    ),
    "lkm-load": TechniqueHelp(
        id="lkm-load",
        summary="Load benign test kernel module from memory or fd (root only).",
        telemetry="init_module, finit_module, memfd+mmap, fork+init_module, embedded buffer",
        required=("i_understand_this_loads_kernel_code",),
        optional=("module", "method", "keep_loaded"),
        example_cli=(
            "sudo env FENIX_BIN_DIR=$PWD/bin $PWD/.venv/bin/fenix run lkm-load "
            "--module payloads/hello_lkm/hello_lkm.ko --method finit_module "
            "--i-understand-this-loads-kernel-code"
        ),
        example_config="examples/lkm_load_finit.yaml",
        notes=(
            "Methods: init_module (heap), memfd-init-module, memfd-init-module-fork, "
            "finit_module, memfd-finit-module, embedded-init-module. "
            "By default rmmod before/after each run; "
            "--keep-loaded skips auto-unload (then fenix cleanup -t lkm-load)"
        ),
    ),
}


def get_technique_help(technique_id: str) -> TechniqueHelp:
    if technique_id not in TECHNIQUES:
        known = ", ".join(sorted(TECHNIQUES))
        raise ValueError(f"Unknown technique '{technique_id}'. Available: {known}")
    return TECHNIQUES[technique_id]


def list_technique_help() -> list[TechniqueHelp]:
    return [TECHNIQUES[k] for k in sorted(TECHNIQUES)]


def assert_catalog_in_sync() -> None:
    """Ensure catalog metadata matches registered technique modules."""
    from fenix.techniques import list_techniques

    registered = {tid for tid, _ in list_techniques()}
    catalog_ids = set(TECHNIQUES.keys())
    if registered != catalog_ids:
        missing_reg = catalog_ids - registered
        missing_cat = registered - catalog_ids
        parts = []
        if missing_reg:
            parts.append(f"missing modules: {', '.join(sorted(missing_reg))}")
        if missing_cat:
            parts.append(f"missing catalog: {', '.join(sorted(missing_cat))}")
        raise RuntimeError("FENIX catalog/registry mismatch (" + "; ".join(parts) + ")")


def validate_options(technique_id: str, options: dict[str, Any]) -> list[str]:
    """Return list of validation error messages (empty if OK)."""
    meta = get_technique_help(technique_id)
    errors: list[str] = []

    def has(*keys: str) -> bool:
        return any(options.get(k) is not None and options.get(k) is not False for k in keys)

    if technique_id == "memfd-script-exec":
        if not has("script", "script_file", "code", "content"):
            errors.append("Provide --script or --code.")
    elif technique_id == "fileless-staging":
        if not has("source_file", "source_url", "lab_remote", "remote"):
            errors.append("Provide --source-file, --source-url, --lab-remote, or --remote.")
        if has("remote") and not has("source_file"):
            errors.append("--remote requires --source-file (payload to upload).")
        if has("remote") and not (
            has("remote_backend", "remote_upload_url")
            or os.environ.get("FENIX_REMOTE_BACKEND")
            or os.environ.get("FENIX_REMOTE_UPLOAD_URL")
        ):
            errors.append(
                "--remote requires --remote-backend or --remote-upload-url "
                "(FENIX does not pick a public host). See docs/STAGING_REMOTE.md."
            )
        if options.get("decode") == "xor" and not has("xor_key"):
            errors.append("XOR decode requires --xor-key.")
        if options.get("decompress") == "tar" and not has("tar_member"):
            errors.append("Tar extract requires --tar-member.")
        if options.get("execute") == "interpreter" and not has("interpreter"):
            errors.append("execute=interpreter requires --interpreter.")
    elif technique_id == "pipe-exec":
        t = options.get("type")
        if not t:
            errors.append("Provide --type elf or --type script.")
        elif t == "elf" and not has("payload"):
            errors.append("type=elf requires --payload.")
        elif t == "script":
            if not has("interpreter"):
                errors.append("type=script requires --interpreter.")
            if not has("code", "content", "script", "script_file"):
                errors.append("type=script requires --code or --script.")
    elif technique_id == "lolbin-fd-exec":
        if not has("lolbin"):
            errors.append("Provide --lolbin (ld-linux, busybox, julia, erlang).")
    elif technique_id == "interpreter-exec":
        mode = options.get("mode")
        if mode == "script-file" and not has("script"):
            errors.append("mode=script-file requires --script.")
        elif mode in ("one-liner", "stdin") and not has("code"):
            errors.append(f"mode={mode} requires --code.")
    elif technique_id == "interpreter-memfd-exec":
        if not has("interpreter"):
            errors.append("Provide --interpreter (perl, python3, ruby, php).")
        mode = options.get("mode") or "one-liner"
        if mode == "script-file" and options.get("script"):
            pass  # optional override of template path
        elif mode not in ("one-liner", "script-file"):
            errors.append("mode must be one-liner or script-file.")
    elif technique_id == "lkm-load":
        method = options.get("method") or "init_module"
        if method != "embedded-init-module" and not has("module"):
            errors.append("Missing required option: --module (not needed for embedded-init-module)")

    for req in meta.required:
        if req == "i_understand_this_loads_kernel_code":
            if not options.get(req) and not options.get("i-understand-this-loads-kernel-code"):
                errors.append("lkm-load requires --i-understand-this-loads-kernel-code")
        elif not has(req):
            errors.append(f"Missing required option: --{req.replace('_', '-')}")

    return errors


def format_technique_info(meta: TechniqueHelp) -> str:
    lines = [
        f"Technique: {meta.id}",
        f"Summary:   {meta.summary}",
        f"Telemetry: {meta.telemetry}",
        "",
        "Required options:",
    ]
    if meta.required:
        for r in meta.required:
            lines.append(f"  --{r.replace('_', '-')}")
    else:
        lines.append("  (see notes — conditional requirements)")

    lines.append("")
    lines.append("Common options:")
    for o in meta.optional:
        lines.append(f"  --{o.replace('_', '-')}")

    lines.append("")
    lines.append("Example:")
    lines.append(f"  {meta.example_cli}")
    if meta.example_config:
        cfg = meta.example_config
        lines.append("")
        lines.append("Config file:")
        lines.append(f"  fenix run -c {cfg}")

    if meta.notes:
        lines.append("")
        lines.append(f"Notes: {meta.notes}")

    lines.append("")
    lines.append("Learning: syscall walkthrough prints by default; use --no-explain to skip")
    lines.append("")
    lines.append("More: fenix examples | fenix list techniques")
    return "\n".join(lines)


QUICKSTART = """
FENIX — Fileless Execution for NIX (Linux lab PoC)

Quick start
  1. make all && pip install -e .
  2. export FENIX_BIN_DIR=$PWD/bin
  3. fenix check
  4. fenix list techniques
  5. fenix info memfd-exec
  6. fenix run -c examples/memfd_exec.yaml
  7. fenix run-all            # optional: full-framework coverage (lab VM)
  8. fenix cleanup

Common commands
  fenix help              This guide
  fenix check             Verify build, helpers, and sample payloads
  fenix list techniques   All technique ids (15)
  fenix list interpreters Interpreters on PATH
  fenix list lolbins      LoLbin install status
  fenix info <technique>  Options, examples, telemetry for one technique
  fenix examples          Example YAML configs (examples/)
  fenix run <technique>   Run with CLI flags
  fenix run -c <file>     Run from YAML config
  fenix run-all           Core coverage matrix (~19 cases)
  fenix run-all --list    Preview matrix cases and tiers
  fenix run-all --full    Extended + lolbin + lkm (sudo + venv path; no internet upload)
  fenix run-all --cleanup Cleanup after matrix (in-process)
  fenix run ...           Syscall walkthrough before each run (default)
  fenix run ... --no-explain  Skip walkthrough
  fenix cleanup           Remove lab artifacts (/tmp, /dev/shm, test LKM)
  fenix cleanup -t lkm-load   Per-technique cleanup
  fenix -q run ...        Run without the banner

Docs: docs/README.md  |  Lab matrix: docs/LAB_MATRIX.md

Lab-only: use isolated VMs you own. See README.md.
""".strip()
