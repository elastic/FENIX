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
"""Predefined lab runs for full-framework coverage / detection testing."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from fenix.core.helpers import helper_bin_dir, project_root
from fenix.lolbins.registry import resolve_lolbin_binary
from fenix.lolbins.registry import LOLBINS as LOLBIN_REGISTRY

SkipFn = Callable[[], str | None]


class LabTier(str, Enum):
    CORE = "core"
    EXTENDED = "extended"
    LKM = "lkm"
    REMOTE = "remote"
    LOLBIN = "lolbin"


@dataclass(frozen=True)
class LabCase:
    """One detonation step in the coverage matrix."""

    case_id: str
    technique: str
    options: dict[str, Any] = field(default_factory=dict)
    tier: LabTier = LabTier.CORE
    requires_root: bool = False
    optional: bool = False
    skip_if: SkipFn | None = None
    note: str | None = None


def _helper_missing(basename: str) -> SkipFn:
    def _check() -> str | None:
        path = helper_bin_dir() / basename
        if not path.is_file() or not os.access(path, os.X_OK):
            return f"missing {path} (run: make helpers)"
        return None

    return _check


def _path_missing(rel: str) -> SkipFn:
    def _check() -> str | None:
        if not (project_root() / rel).is_file():
            return f"missing {rel}"
        return None

    return _check


def _lolbin_missing(lolbin_id: str) -> SkipFn:
    def _check() -> str | None:
        spec = LOLBIN_REGISTRY.get(lolbin_id)
        if not spec:
            return f"unknown lolbin {lolbin_id}"
        try:
            resolve_lolbin_binary(spec)
        except FileNotFoundError as exc:
            return str(exc)
        return None

    return _check


def _cmd_missing(binary: str) -> SkipFn:
    def _check() -> str | None:
        if shutil.which(binary) is None:
            return f"{binary} not on PATH"
        return None

    return _check


def _not_linux() -> str | None:
    import sys

    if sys.platform != "linux":
        return "not Linux"
    return None


def _not_root() -> str | None:
    if os.geteuid() != 0:
        return "requires root (use sudo)"
    return None


def _remote_not_configured() -> str | None:
    backend = os.environ.get("FENIX_REMOTE_BACKEND", "").strip()
    upload = os.environ.get("FENIX_REMOTE_UPLOAD_URL", "").strip()
    if backend or upload:
        return None
    return (
        "remote upload is opt-in; set FENIX_REMOTE_BACKEND or FENIX_REMOTE_UPLOAD_URL"
    )


def build_lab_cases(
    *,
    tiers: set[LabTier] | None = None,
    technique_filter: str | None = None,
) -> list[LabCase]:
    """Return lab cases for the requested tiers (default: core only)."""
    hello = "payloads/hello_elf/hello"
    sleep = "payloads/sleep_elf/sleep"
    hello_so = "payloads/hello_so/hello_so.so"
    hello_ko = "payloads/hello_lkm/hello_lkm.ko"
    shebang = "payloads/scripts/hello_shebang.sh"
    hello_py = "payloads/scripts/hello.py"
    hello_pl = "payloads/scripts/hello.pl"
    hello_awk = "payloads/scripts/hello.awk"
    lkm_flag = {"i_understand_this_loads_kernel_code": True}
    no_explain = {"no_explain": True}

    cases: list[LabCase] = [
        # --- memfd-exec ---
        LabCase(
            "memfd-exec-procfs-fd",
            "memfd-exec",
            {**no_explain, "payload": hello, "method": "procfs-fd", "name": "fenix_lab"},
            tier=LabTier.CORE,
            note="Primary memfd + /proc/self/fd exec",
        ),
        LabCase(
            "memfd-exec-fexecve",
            "memfd-exec",
            {**no_explain, "payload": hello, "method": "fexecve", "name": "fenix_lab"},
            tier=LabTier.CORE,
        ),
        LabCase(
            "memfd-exec-execveat",
            "memfd-exec",
            {**no_explain, "payload": hello, "method": "execveat", "name": "fenix_lab"},
            tier=LabTier.EXTENDED,
        ),
        LabCase(
            "memfd-exec-sendfile",
            "memfd-exec",
            {
                **no_explain,
                "payload": hello,
                "method": "procfs-fd",
                "ingest": "sendfile",
                "name": "fenix_lab",
            },
            tier=LabTier.EXTENDED,
        ),
        # --- memfd-script ---
        LabCase(
            "memfd-script-shebang",
            "memfd-script-exec",
            {**no_explain, "script": shebang, "method": "shebang"},
            tier=LabTier.CORE,
        ),
        LabCase(
            "memfd-script-python-procfs",
            "memfd-script-exec",
            {
                **no_explain,
                "script": hello_py,
                "interpreter": "python3",
                "method": "interpreter-procfs",
            },
            tier=LabTier.CORE,
        ),
        LabCase(
            "memfd-script-awk",
            "memfd-script-exec",
            {
                **no_explain,
                "script": hello_awk,
                "interpreter": "awk",
                "method": "interpreter-procfs",
            },
            tier=LabTier.EXTENDED,
            skip_if=_path_missing(hello_awk),
        ),
        # --- memfd-self-reexec / so ---
        LabCase(
            "memfd-self-reexec",
            "memfd-self-reexec",
            {
                **no_explain,
                "method": "execveat",
                "name": "fenix_lab_self",
                # Keep bin/fenix-memfd-self-reexec so user run-all then sudo --full works.
                # Hand-run `fenix run memfd-self-reexec` still unlinks; then: make helpers
                "no_unlink": True,
            },
            tier=LabTier.CORE,
            skip_if=_helper_missing("fenix-memfd-self-reexec"),
            note="Re-execs fenix-memfd-self-reexec from memfd (--no-unlink in the matrix)",
        ),
        LabCase(
            "memfd-so-load",
            "memfd-so-load",
            {
                **no_explain,
                "module": hello_so,
                "symbol": "fenix_hello",
                "name": "fenix_lab_mod",
            },
            tier=LabTier.CORE,
            skip_if=_path_missing(hello_so),
        ),
        # --- shm / stdin ---
        LabCase(
            "shm-exec-procfs-fd",
            "shm-exec",
            {
                **no_explain,
                "payload": hello,
                "method": "procfs-fd",
                # Unlink before exec so a leftover user-owned /dev/shm object does not
                # make root shm_open fail (sticky /dev/shm + fs.protected_regular).
                "unlink": True,
            },
            tier=LabTier.CORE,
        ),
        LabCase(
            "shm-exec-fexecve",
            "shm-exec",
            {**no_explain, "payload": hello, "method": "fexecve", "unlink": True},
            tier=LabTier.EXTENDED,
            optional=True,
            note="fexecve on shm fd may fail on some kernels (like pipe-exec ELF)",
        ),
        LabCase(
            "shm-so-load",
            "shm-so-load",
            {**no_explain, "module": hello_so, "symbol": "fenix_hello"},
            tier=LabTier.CORE,
            skip_if=_path_missing(hello_so),
        ),
        LabCase(
            "stdin-memexec",
            "stdin-memexec",
            {
                **no_explain,
                "payload": hello,
                "method": "execveat",
                "fchmod": True,
            },
            tier=LabTier.CORE,
        ),
        # --- staging ---
        LabCase(
            "fileless-staging-local-memfd",
            "fileless-staging",
            {
                **no_explain,
                "source_file": hello,
                "execute": "memfd",
                "method": "procfs-fd",
            },
            tier=LabTier.CORE,
        ),
        LabCase(
            "fileless-staging-interpreter-stdin",
            "fileless-staging",
            {
                **no_explain,
                "source_file": hello_pl,
                "execute": "interpreter",
                "interpreter": "perl",
                "mode": "stdin",
            },
            tier=LabTier.CORE,
            skip_if=_path_missing(hello_pl),
        ),
        LabCase(
            "fileless-staging-xor",
            "fileless-staging",
            {
                **no_explain,
                "source_file": "payloads/staged/hello_elf.xor",
                "decode": "xor",
                "xor_key": "fenix",
                "execute": "memfd",
                "method": "procfs-fd",
            },
            tier=LabTier.EXTENDED,
            skip_if=_path_missing("payloads/staged/hello_elf.xor"),
        ),
        LabCase(
            "fileless-staging-remote-memfd",
            "fileless-staging",
            {
                **no_explain,
                "source_file": hello,
                "remote": True,
                "execute": "memfd",
                "method": "procfs-fd",
            },
            tier=LabTier.REMOTE,
            optional=True,
            skip_if=_remote_not_configured,
            note="Opt-in upload; set FENIX_REMOTE_BACKEND",
        ),
        # --- pipe / proc / deleted ---
        LabCase(
            "pipe-exec-script",
            "pipe-exec",
            {
                **no_explain,
                "type": "script",
                "interpreter": "python3",
                "code": 'print("fenix lab pipe")',
            },
            tier=LabTier.CORE,
        ),
        LabCase(
            "pipe-exec-elf",
            "pipe-exec",
            {**no_explain, "type": "elf", "payload": hello},
            tier=LabTier.EXTENDED,
            optional=True,
            note="Often fails on WSL2 (pipe fexecve); counted as skip if optional",
        ),
        LabCase(
            "proc-fd-exec-procfs",
            "proc-fd-exec",
            {**no_explain, "payload": hello, "method": "procfs-fd"},
            tier=LabTier.CORE,
        ),
        LabCase(
            "proc-fd-exec-unlink",
            "proc-fd-exec",
            {
                **no_explain,
                "payload": hello,
                "method": "procfs-fd",
                "unlink_after_open": True,
            },
            tier=LabTier.EXTENDED,
        ),
        LabCase(
            "deleted-file-exec",
            "deleted-file-exec",
            {
                **no_explain,
                "payload": hello,
                "path": "/tmp/fenix_lab_deleted",
                "no_wait": True,
            },
            tier=LabTier.CORE,
        ),
        # --- interpreters ---
        LabCase(
            "interpreter-exec-python",
            "interpreter-exec",
            {
                **no_explain,
                "interpreter": "python3",
                "mode": "one-liner",
                "code": 'print("fenix lab")',
            },
            tier=LabTier.CORE,
        ),
        LabCase(
            "interpreter-memfd-perl-oneliner",
            "interpreter-memfd-exec",
            {**no_explain, "interpreter": "perl", "mode": "one-liner"},
            tier=LabTier.CORE,
        ),
        LabCase(
            "interpreter-memfd-python-oneliner",
            "interpreter-memfd-exec",
            {**no_explain, "interpreter": "python3", "mode": "one-liner"},
            tier=LabTier.CORE,
        ),
        LabCase(
            "interpreter-memfd-php-oneliner",
            "interpreter-memfd-exec",
            {**no_explain, "interpreter": "php", "mode": "one-liner"},
            tier=LabTier.CORE,
        ),
        LabCase(
            "interpreter-memfd-perl-script",
            "interpreter-memfd-exec",
            {**no_explain, "interpreter": "perl", "mode": "script-file"},
            tier=LabTier.EXTENDED,
        ),
        LabCase(
            "interpreter-memfd-ruby-oneliner",
            "interpreter-memfd-exec",
            {**no_explain, "interpreter": "ruby", "mode": "one-liner"},
            tier=LabTier.EXTENDED,
            optional=True,
            skip_if=_cmd_missing("ruby"),
        ),
        # --- lolbin ---
        LabCase(
            "lolbin-ld-linux",
            "lolbin-fd-exec",
            {**no_explain, "lolbin": "ld-linux", "payload": hello},
            tier=LabTier.CORE,
            skip_if=_lolbin_missing("ld-linux"),
        ),
        LabCase(
            "lolbin-busybox",
            "lolbin-fd-exec",
            {**no_explain, "lolbin": "busybox", "payload": shebang},
            tier=LabTier.LOLBIN,
            optional=True,
            skip_if=_lolbin_missing("busybox"),
        ),
        LabCase(
            "lolbin-julia",
            "lolbin-fd-exec",
            {
                **no_explain,
                "lolbin": "julia",
                "payload": "payloads/scripts/hello.jl",
            },
            tier=LabTier.LOLBIN,
            optional=True,
            skip_if=_lolbin_missing("julia"),
        ),
        LabCase(
            "lolbin-erlang",
            "lolbin-fd-exec",
            {
                **no_explain,
                "lolbin": "erlang",
                "payload": "payloads/scripts/hello.escript",
            },
            tier=LabTier.LOLBIN,
            optional=True,
            skip_if=_lolbin_missing("erlang"),
        ),
        # --- lkm-load (root) ---
        LabCase(
            "lkm-init-module",
            "lkm-load",
            {
                **no_explain,
                **lkm_flag,
                "module": hello_ko,
                "method": "init_module",
            },
            tier=LabTier.LKM,
            requires_root=True,
            skip_if=_path_missing(hello_ko),
        ),
        LabCase(
            "lkm-memfd-init-module",
            "lkm-load",
            {
                **no_explain,
                **lkm_flag,
                "module": hello_ko,
                "method": "memfd-init-module",
            },
            tier=LabTier.LKM,
            requires_root=True,
            skip_if=_path_missing(hello_ko),
        ),
        LabCase(
            "lkm-memfd-init-module-fork",
            "lkm-load",
            {
                **no_explain,
                **lkm_flag,
                "module": hello_ko,
                "method": "memfd-init-module-fork",
            },
            tier=LabTier.LKM,
            requires_root=True,
            skip_if=_path_missing(hello_ko),
        ),
        LabCase(
            "lkm-finit-module",
            "lkm-load",
            {
                **no_explain,
                **lkm_flag,
                "module": hello_ko,
                "method": "finit_module",
            },
            tier=LabTier.LKM,
            requires_root=True,
            skip_if=_path_missing(hello_ko),
        ),
        LabCase(
            "lkm-memfd-finit-module",
            "lkm-load",
            {
                **no_explain,
                **lkm_flag,
                "module": hello_ko,
                "method": "memfd-finit-module",
            },
            tier=LabTier.LKM,
            requires_root=True,
            skip_if=_path_missing(hello_ko),
        ),
        LabCase(
            "lkm-embedded-init-module",
            "lkm-load",
            {**no_explain, **lkm_flag, "method": "embedded-init-module"},
            tier=LabTier.LKM,
            requires_root=True,
            skip_if=_path_missing("bin/fenix-embedded-init-module"),
        ),
    ]

    if tiers is None:
        tiers = {LabTier.CORE}

    selected = [c for c in cases if c.tier in tiers]
    if technique_filter:
        selected = [c for c in selected if c.technique == technique_filter]
    return selected


def default_tiers_for_flags(
    *,
    full: bool = False,
    with_lkm: bool = False,
    with_remote: bool = False,
    with_lolbin: bool = False,
) -> set[LabTier]:
    if full:
        return {
            LabTier.CORE,
            LabTier.EXTENDED,
            LabTier.LOLBIN,
            LabTier.LKM,
        }
    tiers = {LabTier.CORE}
    if with_lolbin:
        tiers.add(LabTier.LOLBIN)
    if with_remote:
        tiers.add(LabTier.REMOTE)
    if with_lkm:
        tiers.add(LabTier.LKM)
    return tiers
