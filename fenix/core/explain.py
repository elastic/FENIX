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
"""Human-readable technique walkthroughs for lab learning (on by default)."""

from __future__ import annotations

import sys
from typing import Any, Callable

CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
NC = "\033[0m"

ExplainFn = Callable[[dict[str, Any]], list[str]]


def _g(key: str, opts: dict[str, Any], default: str = "") -> str:
    v = opts.get(key)
    if v is None or v is False:
        return default
    return str(v)


def _lines(title: str, leverage: str, steps: list[str], detect: list[str], payload_note: str) -> list[str]:
    out = [
        "",
        f"{CYAN}{BOLD}━━━ {title} ━━━{NC}",
        "",
        f"{BOLD}Technique leveraged{NC}",
        f"  {leverage}",
        "",
        f"{BOLD}Step-by-step (this run){NC}",
    ]
    for i, step in enumerate(steps, 1):
        out.append(f"  {DIM}{i}.{NC} {step}")
    out.extend(["", f"{BOLD}Detection / telemetry focus{NC}"])
    for item in detect:
        out.append(f"  {YELLOW}•{NC} {item}")
    out.extend(["", f"{BOLD}Expected payload output{NC}", f"  {payload_note}", ""])
    return out


def _explain_memfd_exec(opts: dict[str, Any]) -> list[str]:
    method = _g("method", opts, "procfs-fd")
    payload = _g("payload", opts, "payloads/hello_elf/hello")
    name = _g("name", opts, "fenix_payload")
    ingest = _g("ingest", opts, "write")
    fchmod = opts.get("fchmod")
    noexec = opts.get("noexec_seal") or opts.get("noexec-seal")

    ingest_step = (
        f"{GREEN}sendfile(2){NC} — copy ELF from open fd into memfd (different audit trail than write)"
        if ingest == "sendfile"
        else f"{GREEN}write(2){NC} — copy ELF bytes into memfd"
    )
    extra: list[str] = []
    if fchmod:
        extra.append(f"{GREEN}fchmod(2){NC} — set mode 0755 on memfd before exec (sympy-dev-style)")
    if noexec:
        extra.append(
            f"{GREEN}memfd_create(MFD_NOEXEC_SEAL){NC} — non-exec memfd lab; "
            f"fchmod attempts bypass for hardened-kernel testing"
        )

    if method == "fexecve":
        exec_step = (
            f"{GREEN}fexecve(2){NC} — execute directly from memfd fd "
            f"(no /proc/self/fd path passed to execve)"
        )
        method_note = "Distinct from procfs-fd: no /proc/self/fd/<N> string in the exec syscall."
    elif method == "execveat":
        exec_step = (
            f"{GREEN}execveat(2){NC} — AT_EMPTY_PATH + memfd fd "
            f"(QLNX-style; pathname is empty)"
        )
        method_note = "Distinct from procfs-fd: uses execveat(2) instead of execve(path)."
    else:
        exec_step = (
            f"{GREEN}execve(2){NC} — path {DIM}/proc/self/fd/<N>{NC} "
            f"points at memfd-backed inode"
        )
        method_note = "Classic fileless pattern: process exe links to memfd: name."

    steps = [
        f"{GREEN}open(2){NC} — read benign ELF from {payload}",
        f"{GREEN}memfd_create(2){NC} — anonymous RAM file {DIM}{name}{NC}",
        ingest_step,
        *extra,
        exec_step,
    ]
    detect = [
        f"Syscall chain: memfd_create → {'sendfile' if ingest == 'sendfile' else 'write'} → {method}",
        "Process /proc/<pid>/exe often shows memfd:<name> (may include (deleted))",
        method_note,
    ]
    if fchmod:
        detect.append("fchmod on memfd fd before exec — watch for seal bypass attempts")
    if noexec and fchmod:
        payload_note = (
            "often fails with fchmod: Operation not permitted — that is the expected hardened-kernel outcome "
            "(not fixed by sudo; root is not required for this lab)"
        )
    else:
        payload_note = "stdout: hello from fenix (from payloads/hello_elf/hello)"
    return _lines(
        f"memfd-exec · method={method}"
        + (f" · ingest={ingest}" if ingest != "write" else "")
        + (" · fchmod" if fchmod else "")
        + (" · noexec-seal" if noexec else ""),
        "Load an ELF into anonymous kernel memory and replace the process with that image — "
        "payload never needs a persistent disk path for execution.",
        steps,
        detect,
        payload_note,
    )


def _explain_memfd_script(opts: dict[str, Any]) -> list[str]:
    method = _g("method", opts, "shebang")
    script = _g("script", opts) or _g("script_file", opts) or "(inline --code)"
    interpreter = _g("interpreter", opts, "(from shebang or --interpreter)")
    name = _g("name", opts, "fenix_script")

    if method == "shebang":
        steps = [
            f"{GREEN}read{NC} — load script bytes from {script}",
            f"{GREEN}memfd_create(2){NC} — inheritable memfd {DIM}{name}{NC} (no CLOEXEC — shebang must reopen fd)",
            f"{GREEN}write(2){NC} — script content into memfd",
            f"{GREEN}execve(2){NC} — kernel reads shebang → spawns {interpreter} with script fd",
        ]
        detect = [
            "memfd_create → write → execve on /proc/self/fd/N",
            "Child becomes interpreter (e.g. bash) with script backed by memfd",
        ]
        script_lower = str(script).lower()
        if "hello.awk" in script_lower:
            out_msg = (
                "stdout: hello from fenix awk — shebang needs /usr/bin/awk (or gawk) installed; "
                "if missing, use --method interpreter-procfs --interpreter awk"
            )
        elif "hello.js" in script_lower:
            out_msg = "stdout: hello from fenix node"
        elif "hello_shebang" in script_lower or script_lower.endswith(".sh"):
            out_msg = "stdout: hello from fenix shebang script"
        else:
            out_msg = "stdout: output from script per its #! line (interpreter must exist on host)"
    elif method == "fexecve-interpreter":
        steps = [
            f"Script into memfd as above",
            f"{GREEN}fexecve(2){NC} — {interpreter} executed using memfd fd directly",
        ]
        detect = ["memfd_create → write → fexecve with interpreter binary"]
        out_msg = "Interpreter runs script from memfd fd"
    else:
        awk_note = (
            f" (awk uses {DIM}-f{NC} — plain {DIM}awk /proc/self/fd/N{NC} waits on stdin)"
            if "awk" in interpreter.lower()
            else ""
        )
        steps = [
            f"Script into memfd",
            f"{GREEN}execve(2){NC} — {interpreter} "
            f"{DIM}-f /proc/self/fd/N{NC} or script path as argument{awk_note}",
        ]
        detect = [
            "memfd_create → write → execve(interpreter, [-f] /proc/self/fd/N)",
            "Two-process pattern: interpreter + memfd-backed script path",
        ]
        script_lower = str(script).lower()
        if "hello_shebang" in script_lower or script_lower.endswith(".sh"):
            out_msg = (
                "Use --interpreter sh or bash, or --method shebang. "
                "Other interpreters need matching payloads (hello.py, hello.awk, …)"
            )
        elif "hello.py" in script_lower:
            out_msg = 'stdout: hello from fenix memfd script (python)'
        elif "hello.awk" in script_lower:
            out_msg = "stdout: hello from fenix awk"
        elif "hello.lua" in script_lower:
            out_msg = "stdout: hello from fenix lua"
        elif "hello.rb" in script_lower:
            out_msg = "stdout: hello from fenix ruby"
        elif "hello.js" in script_lower:
            out_msg = "stdout: hello from fenix node (prefer --method shebang for node)"
        else:
            out_msg = "stdout: output from the script matching --interpreter"

    return _lines(
        f"memfd-script-exec · method={method}",
        "Execute script bytes from memfd instead of a on-disk script path.",
        steps,
        detect,
        out_msg,
    )


def _explain_memfd_self_reexec(opts: dict[str, Any]) -> list[str]:
    method = _g("method", opts, "execveat")
    name = _g("name", opts, "fenix_self")
    no_unlink = opts.get("no_unlink")
    return _lines(
        f"memfd-self-reexec · method={method}",
        "QLNX-style: copy the running binary from /proc/self/exe into memfd, "
        "optionally unlink the on-disk file, then re-execute from memory.",
        [
            f"{GREEN}read(2){NC} — stream {DIM}/proc/self/exe{NC} (this helper binary) into buffer",
            f"{GREEN}memfd_create(2){NC} — {name}",
            f"{GREEN}write(2){NC} — copy image into memfd",
            "Clear FD_CLOEXEC on memfd so the next exec can use the fd",
            *([] if no_unlink else [f"{GREEN}unlink(2){NC} — remove on-disk helper path"]),
            f"Set {DIM}FENIX_MFD_RE=1{NC} guard env",
            f"{GREEN}{'execveat' if method == 'execveat' else 'execve'}{NC} — "
            f"second stage runs from memfd; guard exits cleanly on re-entry",
        ],
        [
            "read /proc/self/exe → memfd_create → write → unlink? → execveat",
            "Second invocation sees FENIX_MFD_RE and exits (no infinite loop)",
            "mimics malware that deletes its dropper after copying to memfd",
        ],
        "stderr: fenix-memfd-self-reexec: re-exec from memfd complete (/memfd:fenix_self (deleted)) — "
        "not hello_elf; --payload is ignored (re-execs this helper only).",
    )


def _explain_memfd_so(opts: dict[str, Any]) -> list[str]:
    symbol = _g("symbol", opts, "fenix_hello")
    module = _g("module", opts, "payloads/hello_so/hello_so.so")
    return _lines(
        "memfd-so-load",
        "Reflective shared-object load: .so lives in memfd, then dlopen via /proc/self/fd/N — "
        "no dlopen path under /tmp or /dev/shm.",
        [
            f"{GREEN}open/read{NC} — .so file {module}",
            f"{GREEN}memfd_create(2){NC} — anonymous backing for library",
            f"{GREEN}write(2){NC} — copy .so image",
            f"{GREEN}dlopen(3){NC} — {DIM}/proc/self/fd/N{NC}",
            f"{GREEN}dlsym(3){NC} + call — invoke {symbol}()",
        ],
        [
            "memfd_create → write → dlopen(/proc/self/fd/N)",
            "No new executable process — loads in current process (here: helper exits after call)",
            "Maps to QLNX reflective .so pattern (userland, not kernel module)",
        ],
        f'stderr: success message; {symbol} prints: hello from fenix shared object (memfd dlopen)',
    )


def _explain_shm_exec(opts: dict[str, Any]) -> list[str]:
    method = _g("method", opts, "procfs-fd")
    ingest = _g("ingest", opts, "write")
    payload = _g("payload", opts, "payloads/hello_elf/hello")
    name = _g("name", opts, "fenix_shm_payload")
    if method == "fexecve":
        exec_step = f"{GREEN}fexecve(2){NC} — exec from shm fd"
    else:
        exec_step = (
            f"{GREEN}execve(2){NC} — {DIM}/proc/self/fd/N{NC} "
            f"(shm object at /dev/shm/{name}; avoids noexec on /dev/shm)"
        )
    return _lines(
        f"shm-exec · method={method} · ingest={ingest}",
        "POSIX shared memory on tmpfs (/dev/shm) — no memfd_create syscall; "
        "still a fileless-style path on many systems.",
        [
            f"{GREEN}open/read{NC} — ELF {payload}",
            f"{GREEN}shm_open(3){NC} + {GREEN}ftruncate{NC} — object {DIM}/{name}{NC} under /dev/shm",
            f"{GREEN}{'sendfile' if ingest == 'sendfile' else 'write'}{NC} — copy ELF into shm object",
            exec_step,
        ],
        [
            "Syscall chain: shm_open → ftruncate → write/sendfile → execve|fexecve",
            "No memfd_create — hunts keyed only on memfd will miss this",
            "Visible file /dev/shm/<name> unless unlinked before exec",
        ],
        "stdout: hello from fenix",
    )


def _explain_shm_so(opts: dict[str, Any]) -> list[str]:
    symbol = _g("symbol", opts, "fenix_hello")
    module = _g("module", opts, "payloads/hello_so/hello_so.so")
    return _lines(
        "shm-so-load",
        "dlopen from /dev/shm path instead of memfd — SilentLoader / pre-3.17 style path.",
        [
            f"Read .so from {module}",
            f"{GREEN}shm_open{NC} → write → {GREEN}dlopen(/dev/shm/...){NC}",
            f"{GREEN}dlsym{NC} → {symbol}()",
            f"{GREEN}shm_unlink{NC} — cleanup",
        ],
        ["shm_open → dlopen (no memfd_create)", "File briefly visible under /dev/shm"],
        f"{symbol} message on stderr/stdout path",
    )


def _explain_stdin_memexec(opts: dict[str, Any]) -> list[str]:
    method = _g("method", opts, "execveat")
    payload = _g("payload", opts)
    src = f"stdin pipe" if not payload else f"file {payload}"
    return _lines(
        f"stdin-memexec · method={method}",
        "memexec-style: ELF bytes from stdin (or file) → memfd → exec without touching disk for the executable image.",
        [
            f"{GREEN}read(2){NC} — ELF from {src}",
            f"{GREEN}memfd_create(2){NC}",
            f"{GREEN}write(2){NC} — buffer into memfd",
            *(["fchmod(2) — executable mode on memfd"] if opts.get("fchmod") else []),
            f"{GREEN}{method}(2){NC} — run from memfd fd",
        ],
        [
            "memfd_create → write → execveat|fexecve",
            "Often chained: curl | fenix … (no disk artifact for ELF)",
        ],
        "stdout: hello from fenix",
    )


def _explain_fileless_staging(opts: dict[str, Any]) -> list[str]:
    src = (
        _g("remote_uploaded_url", opts)
        or _g("source_url", opts)
        or _g("source_file", opts)
        or "(source)"
    )
    remote_fetch = _g("remote_fetch", opts)
    decode = _g("decode", opts, "none")
    decompress = _g("decompress", opts, "none")
    execute = _g("execute", opts, "memfd")
    method = _g("method", opts, "procfs-fd")
    if opts.get("remote_uploaded_url"):
        backend = _g("remote_backend", opts, "(named host)")
        steps = [
            f"{GREEN}upload{NC} — operator-named host ({backend}); FENIX does not pick a public bin",
            f"{GREEN}fetch{NC} — download via {remote_fetch or 'requests'}: {src}",
        ]
    else:
        steps = [
            f"{GREEN}fetch{NC} — HTTP GET or local read: {src}",
        ]
    if decode != "none":
        steps.append(f"{GREEN}transform{NC} — decode={decode}" + (
            f" key={_g('xor_key', opts)}" if decode == "xor" else ""
        ))
    if decompress != "none":
        steps.append(f"{GREEN}transform{NC} — decompress={decompress}")
    interp = _g("interpreter", opts)
    mode = _g("mode", opts, "stdin")
    if execute == "interpreter":
        if mode == "stdin":
            steps.append(
                f"{GREEN}stdin{NC} — feed downloaded script to {interp} via subprocess "
                f"(input=pipe, no /tmp staging file)"
            )
        else:
            steps.append(
                f"Delegate to {GREEN}interpreter-exec{NC} — {interp} mode={mode}"
            )
        telemetry = [
            "Network or file read → optional decode → interpreter (in-memory; no fenix-staged temp file)",
        ]
        expected = f"Script output (e.g. hello from fenix {interp})"
    else:
        steps.append(f"{GREEN}temp file{NC} — brief write under /tmp/fenix-staged-* (memfd ingest only)")
        steps.append(f"Delegate to {GREEN}memfd-exec{NC} (method={method}) — see memfd-exec explain")
        telemetry = [
            "Network or file read → optional crypto → temp staging file → memfd exec",
            "Temp artifacts under /tmp/fenix-staged-* (clean with fenix cleanup)",
        ]
        expected = "hello from fenix when execute=memfd with hello_elf"
    return _lines(
        "fileless-staging",
        "Stage → optional decode/decompress → execute. "
        "Mimics remote droppers (Pastebin, XOR blobs, gzip layers).",
        steps,
        telemetry,
        expected,
    )


def _explain_pipe(opts: dict[str, Any]) -> list[str]:
    typ = _g("type", opts, "elf")
    if typ == "script":
        return _lines(
            "pipe-exec · type=script",
            "Feed script source to interpreter on stdin via pipe — no memfd.",
            [
                f"{GREEN}pipe(2){NC}",
                f"{GREEN}fork{NC} + interpreter {_g('interpreter', opts)}",
                f"{GREEN}write(2){NC} — script bytes into pipe stdin",
            ],
            ["pipe → write → interpreter reads stdin", "No memfd_create"],
            "Script print output",
        )
    return _lines(
        "pipe-exec · type=elf",
        "ELF written to pipe then fexecve from read end — alternative to memfd.",
        [
            f"{GREEN}open/read{NC} — ELF {_g('payload', opts)}",
            f"{GREEN}pipe(2){NC}",
            f"{GREEN}write(2){NC} — ELF into pipe",
            f"{GREEN}fchmod(2){NC} — exec bit on pipe read fd (kernel-dependent)",
            f"{GREEN}fexecve(2){NC} — execute from pipe fd",
        ],
        [
            "pipe + write + fexecve (no memfd_create)",
            "Distinct syscall fingerprint from memfd-exec",
        ],
        "often EPERM on modern kernels (syscall lab OK); memfd-exec --method fexecve for hello output",
    )


def _explain_proc_fd(opts: dict[str, Any]) -> list[str]:
    method = _g("method", opts, "procfs-fd")
    unlink = opts.get("unlink_after_open") or opts.get("unlink")
    payload = _g("payload", opts)
    steps = [
        f"{GREEN}open(2){NC} — regular file fd for {payload}",
    ]
    if unlink:
        steps.append(f"{GREEN}unlink(2){NC} — remove directory entry; fd still open")
    if method == "fexecve":
        steps.append(f"{GREEN}fexecve(2){NC} — exec from open fd")
    else:
        steps.append(f"{GREEN}execve(2){NC} — /proc/self/fd/N")
    return _lines(
        f"proc-fd-exec · method={method}",
        "Execute via an open file descriptor — not memfd-backed (different inode / audit fields).",
        steps,
        [
            "open → [unlink] → execve|fexecve — no memfd_create",
            "Deleted file + proc fd exec pattern if unlink_after_open",
        ],
        "stdout: hello from fenix",
    )


def _explain_deleted(opts: dict[str, Any]) -> list[str]:
    path = _g("path", opts, "/tmp/fenix_sleep")
    wait = not opts.get("no_wait")
    return _lines(
        "deleted-file-exec",
        "Classic 'file on disk then deleted while running' — copy ELF to path, child opens, unlinks, fexecve.",
        [
            f"{GREEN}read/copy{NC} — payload to {path}",
            f"{GREEN}fork(2){NC}",
            f"Child: {GREEN}open{NC} → {GREEN}unlink(2){NC} → {GREEN}fexecve(2){NC}",
            "Parent waits" if wait else "Parent returns (--no-wait)",
        ],
        [
            f"File {path} appears then deleted; process keeps running",
            "ls shows missing file; /proc/pid/exe may show (deleted)",
        ],
        "hello from fenix (sleep runs in background if sleep_elf + no-wait)",
    )


def _explain_interpreter_memfd(opts: dict[str, Any]) -> list[str]:
    interp = _g("interpreter", opts)
    payload = _g("payload", opts) or "payloads/hello_elf/hello"
    argv0 = _g("argv0", opts, "fenix_payload")
    mode = _g("mode", opts, "one-liner")
    spec_flag = {"perl": "-e", "python3": "-c", "php": "-r", "ruby": "-e"}.get(
        interp, "-e"
    )
    ext = {"perl": "pl", "python3": "py", "php": "php", "ruby": "rb"}.get(
        interp, "ext"
    )
    memfd_script = f"memfd_payload.{ext}"
    launch_display = _g("memfd_launch_display", opts)
    if mode == "script-file":
        launch = f"{GREEN}subprocess{NC} — {launch_display or f'{interp} {memfd_script}'}"
    else:
        launch = f"{GREEN}subprocess{NC} — {launch_display or f'{interp} {spec_flag} …'}"
    steps = [
        launch,
        f"{GREEN}memfd_create(2){NC} — syscall or libc API inside interpreter",
        f"{GREEN}read stdin{NC} — ELF bytes piped by FENIX ({payload})",
        f"{GREEN}write(2){NC} — copy ELF into memfd fd",
        f"{GREEN}execve(2){NC} — {DIM}/proc/self/fd/N{NC} with argv[0]={argv0}",
    ]
    lines = _lines(
        f"interpreter-memfd-exec · {interp} · mode={mode}",
        "Two detection surfaces: interpreter one-liner (-e/-c/-r) vs memfd_payload.* script on disk.",
        steps,
        [
            f"one-liner: long {interp} {spec_flag} with memfd_create/syscall text in cmdline",
            f"script-file: {interp} + path ending in {memfd_script}",
            "stdin ELF ingest; exec via /proc/self/fd/N",
        ],
        "stdout: hello from fenix (hello_elf executed from memfd)",
    )
    source = opts.get("memfd_payload_source")
    if source:
        tpl = _g("memfd_template_path", opts)
        lines.extend(["", f"{BOLD}Interpreter payload ({mode}){NC}"])
        if tpl:
            lines.append(f"  {DIM}Template:{NC} {tpl}")
        if mode == "one-liner":
            if interp == "php":
                lines.append(
                    f"  {DIM}Argv shape:{NC} {interp} {spec_flag} '<inline body; no <?php tag>'"
                )
            else:
                lines.append(f"  {DIM}Argv shape:{NC} {interp} {spec_flag} '<expanded source>'")
        elif launch_display:
            lines.append(f"  {DIM}Script path:{NC} {launch_display}")
        lines.append(f"  {DIM}Expanded source:{NC}")
        for line in str(source).splitlines():
            lines.append(f"    {line}")
        lines.append("")
    return lines


def _explain_interpreter(opts: dict[str, Any]) -> list[str]:
    mode = _g("mode", opts)
    interp = _g("interpreter", opts)
    if mode == "one-liner":
        steps = [f"{GREEN}subprocess{NC} — {interp} -c '<code>'"]
    elif mode == "script-file":
        steps = [f"{GREEN}subprocess{NC} — {interp} <script path>"]
    else:
        steps = [f"{GREEN}subprocess{NC} — {interp} with script on stdin"]
    return _lines(
        f"interpreter-exec · {mode}",
        "No ELF loader — OS interpreter executes source. Fileless in the sense of no custom ELF drop.",
        steps,
        [
            f"Process tree: fenix → {interp}",
            "No memfd_create unless combined with other techniques",
            "Distinct from memfd-script-exec (which uses memfd for script bytes)",
        ],
        "Interpreter stdout (print/echo)",
    )


def _explain_lolbin_fd_exec(opts: dict[str, Any]) -> list[str]:
    lolbin = _g("lolbin", opts, "ld-linux")
    payload = _g("payload", opts) or "(default for lolbin)"
    name = _g("name", opts, "fenix_lolbin")
    bin_path = _g("bin", opts) or _g("linker", opts, "(auto-detect)")

    if lolbin == "ld-linux":
        exec_step = (
            f"{GREEN}execve(2){NC} — {bin_path} {DIM}/proc/self/fd/N{NC} "
            f"(dynamic linker loads ELF from memfd path)"
        )
        detect = [
            "process.name often ld-linux-x86-64.so.2 or ld-linux-aarch64.so.1",
            "args: linker path + /proc/self/fd/N",
            "memfd_create → write → execve (distinct from python/bash LoLbins)",
        ]
        out_msg = "stdout: hello from fenix (hello_elf via ld-linux)"
    elif lolbin == "busybox":
        exec_step = (
            f"{GREEN}execve(2){NC} — busybox sh {DIM}/proc/self/fd/N{NC} "
            f"(applet runs shell script from memfd)"
        )
        detect = [
            "process.name busybox, args contain sh + /proc/self/fd/N",
            "memfd-backed script without on-disk path",
        ]
        out_msg = "stdout: hello from fenix shebang script"
    elif lolbin == "erlang":
        exec_step = (
            f"{GREEN}execve(2){NC} — escript {DIM}/proc/self/fd/N{NC}"
        )
        detect = ["process.name escript, args /proc/self/fd/N", "memfd_create → write → execve"]
        out_msg = "stdout: hello from fenix erlang"
    else:
        exec_step = (
            f"{GREEN}execve(2){NC} — {lolbin} {DIM}/proc/self/fd/N{NC}"
        )
        detect = [f"process.name {lolbin}, script path under /proc/self/fd/N"]
        out_msg = f"stdout: hello from fenix {lolbin}"

    steps = [
        f"{GREEN}read{NC} — payload {payload}",
        f"{GREEN}memfd_create(2){NC} — inheritable memfd {DIM}{name}{NC}",
        f"{GREEN}write(2){NC} — copy bytes into memfd",
        exec_step,
    ]
    return _lines(
        f"lolbin-fd-exec · lolbin={lolbin}",
        "Stage payload in memfd, then invoke a LoLbin with /proc/self/fd/N as the target "
        "(matches interpreter + fd path detection rules).",
        steps,
        detect,
        out_msg,
    )


def _explain_lkm(opts: dict[str, Any]) -> list[str]:
    method = _g("method", opts, "init_module")
    module = _g("module", opts)
    if method == "embedded-init-module":
        steps = [
            f"{GREEN}embedded .ko buffer{NC} — compiled into helper (no runtime .ko read)",
            f"{GREEN}init_module(2){NC} — load image from static array",
        ]
        detect = [
            "init_module from .rodata/.data — no open() of .ko on disk",
            "embedded module image in the helper binary",
        ]
    elif method == "init_module":
        steps = [
            f"{GREEN}open/read{NC} — .ko {module}",
            f"{GREEN}malloc + init_module(2){NC} — heap buffer",
        ]
        detect = ["init_module syscall — full module in userspace heap", "requires root"]
    elif method == "memfd-init-module":
        steps = [
            f"Read .ko → {GREEN}memfd_create{NC} → write → {GREEN}mmap{NC}",
            f"{GREEN}init_module(2){NC} — mmap'd memfd image",
        ]
        detect = ["memfd_create → mmap → init_module", "no finit_module"]
    elif method == "memfd-init-module-fork":
        steps = [
            f"Read .ko → {GREEN}memfd_create{NC} → write",
            f"{GREEN}fork{NC} — child {GREEN}mmap{NC} memfd → {GREEN}init_module(2){NC}",
        ]
        detect = ["parent memfd_create; child init_module", "fork before module load"]
    elif method == "memfd-finit-module":
        steps = [
            f"Read .ko → {GREEN}memfd_create{NC} → write",
            f"{GREEN}finit_module(2){NC} — load from memfd fd",
        ]
        detect = ["memfd_create → finit_module", "kernel still loads hello_lkm"]
    else:
        steps = [
            f"{GREEN}open(2){NC} — .ko fd",
            f"{GREEN}finit_module(2){NC} — load from file descriptor",
        ]
        detect = ["finit_module from open .ko file"]
    return _lines(
        f"lkm-load · method={method}",
        "In-memory kernel module load (benign hello_lkm — logs only).",
        steps,
        detect
        + [
            "dmesg: hello_lkm: loaded / unloaded",
            "Default: rmmod before and after run (use --keep-loaded to leave module loaded)",
        ],
        "No userspace print — check dmesg",
    )


_EXPLAINERS: dict[str, ExplainFn] = {
    "memfd-exec": _explain_memfd_exec,
    "memfd-script-exec": _explain_memfd_script,
    "memfd-self-reexec": _explain_memfd_self_reexec,
    "memfd-so-load": _explain_memfd_so,
    "shm-exec": _explain_shm_exec,
    "shm-so-load": _explain_shm_so,
    "stdin-memexec": _explain_stdin_memexec,
    "fileless-staging": _explain_fileless_staging,
    "pipe-exec": _explain_pipe,
    "proc-fd-exec": _explain_proc_fd,
    "deleted-file-exec": _explain_deleted,
    "interpreter-exec": _explain_interpreter,
    "interpreter-memfd-exec": _explain_interpreter_memfd,
    "lolbin-fd-exec": _explain_lolbin_fd_exec,
    "lkm-load": _explain_lkm,
}


def format_technique_explain(technique_id: str, options: dict[str, Any]) -> str:
    fn = _EXPLAINERS.get(technique_id)
    if not fn:
        return f"(No explain text for '{technique_id}' yet.)\n"
    return "\n".join(fn(options))


def print_technique_explain(technique_id: str, options: dict[str, Any], *, file=None) -> None:
    """Print learning walkthrough for a technique run."""
    out = file if file is not None else sys.stdout
    text = format_technique_explain(technique_id, options)
    # Strip ANSI for non-tty if needed — keep color on tty
    print(text, file=out, flush=True)
