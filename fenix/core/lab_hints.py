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
"""Lab guidance messages (sysctl, security warnings) for technique runs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

YELLOW = "\033[33m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

MEMFD_NOEXEC_PROC = Path("/proc/sys/vm/memfd_noexec")


def read_vm_memfd_noexec() -> int | None:
    """Return vm.memfd_noexec sysctl value, or None if unreadable."""
    try:
        raw = MEMFD_NOEXEC_PROC.read_text(encoding="ascii").strip()
        return int(raw.split()[0])
    except (OSError, ValueError):
        return None


def print_noexec_seal_lab_hints(*, file: TextIO | None = None) -> None:
    """
    After a failed --noexec-seal --fchmod run, explain expected behavior and
    optional sysctl commands (with security warnings).
    """
    out = file if file is not None else sys.stderr
    val = read_vm_memfd_noexec()
    val_s = str(val) if val is not None else "(unknown)"

    lines = [
        "",
        f"{BOLD}memfd noexec bypass lab{NC}",
        "",
        f"  {DIM}vm.memfd_noexec{NC} = {val_s}",
        "",
        "  This run uses --noexec-seal (MFD_NOEXEC_SEAL on the memfd). On modern",
        "  kernels, fchmod(0755) before exec is blocked — that is the intended lab",
        "  outcome, not a broken install.",
        "",
    ]

    if val == 0:
        lines.extend(
            [
                "  sysctl is already permissive (0). This failure is from --noexec-seal on the",
                "  memfd, not from vm.memfd_noexec. You cannot get hello from fenix with both",
                "  --noexec-seal and --fchmod on a modern kernel — that is the lab point.",
                "",
                f"  {BOLD}Enable system-wide memfd noexec policy{NC} (extra hardened-host scenarios):",
                "",
                "    sudo sysctl -w vm.memfd_noexec=1",
                "",
                f"  {YELLOW}WARNING:{NC} This hardens memfd behavior on the entire host.",
                "  Use only on isolated, disposable research VMs.",
                "",
                "  Make persistent across reboot (lab VM only):",
                "",
                "    echo 'vm.memfd_noexec=1' | sudo tee /etc/sysctl.d/99-fenix-lab.conf",
                "    sudo sysctl --system",
                "",
                f"  {BOLD}Relax memfd policy{NC} (only if sysctl is later set to 1 or 2):",
                "",
                "    sudo sysctl -w vm.memfd_noexec=0",
                "",
                f"  {YELLOW}WARNING:{NC} This reduces system security. Lab VMs only.",
                "",
            ]
        )
    elif val in (1, 2):
        lines.extend(
            [
                "  Host sysctl already enforces memfd noexec (values 1 or 2).",
                "",
                f"  {BOLD}Relax system-wide memfd noexec{NC} (permissive lab only — not recommended):",
                "",
                "    sudo sysctl -w vm.memfd_noexec=0",
                "",
                f"  {YELLOW}WARNING:{NC} This reduces system security by allowing executable",
                "  memfds by default. Use only on isolated lab VMs you can rebuild.",
                "",
            ]
        )

    lines.extend(
        [
            f"  {BOLD}Successful exec with fchmod{NC} (comparison / baseline, omit the seal):",
            "",
            "    fenix run memfd-exec --payload payloads/hello_elf/hello \\",
            "      --fchmod --method execveat",
            "",
            "  Docs: docs/MEMFD_NOEXEC_LAB.md",
            "",
        ]
    )

    for line in lines:
        print(line, file=out, flush=True)
