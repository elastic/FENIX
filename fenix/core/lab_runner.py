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
"""Run the full FENIX lab coverage matrix."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum

from fenix.core.lab_matrix import LabCase, LabTier, build_lab_cases, default_tiers_for_flags
from fenix.core.runner import run_from_options
import fenix.techniques  # noqa: F401


class CaseOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"


@dataclass
class CaseResult:
    case: LabCase
    outcome: CaseOutcome
    detail: str = ""
    exit_code: int | None = None


def _resolve_skip(case: LabCase) -> str | None:
    from fenix.core.lab_matrix import _not_linux, _not_root

    reason = _not_linux()
    if reason:
        return reason
    if case.requires_root:
        reason = _not_root()
        if reason:
            return reason
    if case.skip_if:
        return case.skip_if()
    return None


def run_lab_matrix(
    *,
    tiers: set[LabTier] | None = None,
    technique_filter: str | None = None,
    dry_run: bool = False,
    continue_on_error: bool = True,
) -> list[CaseResult]:
    cases = build_lab_cases(tiers=tiers, technique_filter=technique_filter)
    results: list[CaseResult] = []

    for case in cases:
        skip = _resolve_skip(case)
        if skip:
            results.append(CaseResult(case, CaseOutcome.SKIP, skip))
            continue

        if dry_run:
            results.append(CaseResult(case, CaseOutcome.SKIP, "dry-run"))
            continue

        print(f"\n{'=' * 72}", file=sys.stderr)
        print(f"[lab] {case.case_id} → {case.technique}", file=sys.stderr)
        if case.note:
            print(f"      {case.note}", file=sys.stderr)
        print(f"{'=' * 72}", file=sys.stderr)

        try:
            rc = run_from_options(case.technique, dict(case.options))
        except FileNotFoundError as exc:
            detail = str(exc)
            if "Helper" in detail or "not found" in detail.lower():
                results.append(CaseResult(case, CaseOutcome.SKIP, detail))
            elif case.optional:
                results.append(CaseResult(case, CaseOutcome.SKIP, detail))
            else:
                results.append(CaseResult(case, CaseOutcome.ERROR, detail))
        except (ValueError, PermissionError, OSError) as exc:
            detail = str(exc)
            if case.optional:
                results.append(CaseResult(case, CaseOutcome.SKIP, detail))
            else:
                results.append(CaseResult(case, CaseOutcome.ERROR, detail))
            if not continue_on_error:
                break
            continue
        except Exception as exc:
            results.append(CaseResult(case, CaseOutcome.ERROR, str(exc)))
            if not continue_on_error:
                break
            continue

        if rc == 0:
            results.append(CaseResult(case, CaseOutcome.PASS, exit_code=0))
        elif case.optional:
            results.append(
                CaseResult(case, CaseOutcome.SKIP, f"exit {rc} (optional)", exit_code=rc)
            )
        else:
            results.append(CaseResult(case, CaseOutcome.FAIL, f"exit {rc}", exit_code=rc))
            if not continue_on_error:
                break

    return results


def format_lab_report(results: list[CaseResult]) -> str:
    lines: list[str] = []
    width = 72
    lines.append("")
    lines.append("FENIX lab matrix summary".center(width))
    lines.append("-" * width)
    lines.append(f"{'CASE':<36} {'TECHNIQUE':<22} {'RESULT':<6} DETAIL")
    lines.append("-" * width)

    for r in results:
        detail = r.detail
        limit = 56 if r.outcome in (CaseOutcome.ERROR, CaseOutcome.SKIP) else 28
        if len(detail) > limit:
            detail = detail[: limit - 3] + "..."
        lines.append(
            f"{r.case.case_id:<36} {r.case.technique:<22} {r.outcome.value:<6} {detail}"
        )

    passed = sum(1 for r in results if r.outcome == CaseOutcome.PASS)
    failed = sum(1 for r in results if r.outcome == CaseOutcome.FAIL)
    skipped = sum(1 for r in results if r.outcome == CaseOutcome.SKIP)
    errors = sum(1 for r in results if r.outcome == CaseOutcome.ERROR)
    lines.append("-" * width)
    lines.append(
        f"Total {len(results)} | PASS {passed} | FAIL {failed} | SKIP {skipped} | ERROR {errors}"
    )
    return "\n".join(lines)


def lab_exit_code(results: list[CaseResult]) -> int:
    if any(r.outcome == CaseOutcome.FAIL for r in results):
        return 1
    if any(r.outcome == CaseOutcome.ERROR for r in results):
        return 1
    return 0
