"""Completed assessments -> negotiation memo + redline-ready changeset.

The changeset format is intentionally minimal so it can be fed to any tracked-changes tool
(docx-redline-mcp, legal-redline-tools, or a human): a list of
{clause_ref, find, replace, comment, severity}. `find` must be a verbatim substring of the
contract; we check that here so nothing downstream has to.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from .models import Playbook, Severity

_ORDER = {Severity.DEAL_BREAKER: 0, Severity.HIGH: 1, Severity.MEDIUM: 2, Severity.LOW: 3}


class Verdict(StrEnum):
    IDEAL = "IDEAL"
    ACCEPTABLE = "ACCEPTABLE"
    BELOW = "BELOW"  # below acceptable but above walk-away; needs approval or a counter
    WALK_AWAY = "WALK_AWAY"
    MISSING = "MISSING"


class Assessment(BaseModel):
    position_id: str
    verdict: Verdict
    clause_ref: str | None = None
    evidence: str = Field(description="verbatim quotation from the contract, or 'silent'")
    reasoning: str = ""
    find: str | None = Field(default=None, description="verbatim text to replace (if any)")
    replace: str | None = None
    comment: str | None = Field(default=None, description="comment for the counterparty")


class AssessmentSet(BaseModel):
    contract: str
    playbook: str
    assessments: list[Assessment]

    @classmethod
    def load(cls, path: str | Path) -> AssessmentSet:
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def changeset(aset: AssessmentSet, playbook: Playbook, contract_text: str | None = None) -> dict:
    changes = []
    problems = []
    for a in aset.assessments:
        pos = playbook.position(a.position_id)
        if a.verdict in (Verdict.IDEAL, Verdict.ACCEPTABLE):
            continue
        replace = a.replace or (pos.fallback_language.strip() if pos.fallback_language else None)
        if contract_text is not None and a.find and a.find not in contract_text:
            problems.append(f"{a.position_id}: `find` text is not a verbatim substring of "
                            "the contract; the redline tool would fail")
        changes.append({
            "position_id": a.position_id,
            "topic": pos.topic,
            "severity": pos.severity.value,
            "verdict": a.verdict.value,
            "clause_ref": a.clause_ref,
            "find": a.find,
            "replace": replace,
            "comment": a.comment or f"{pos.topic}: proposed to align with our standard position.",
            "insert_if_missing": a.verdict is Verdict.MISSING,
        })
    changes.sort(key=lambda c: _ORDER[Severity(c["severity"])])
    return {"contract": aset.contract, "playbook": aset.playbook, "changes": changes,
            "problems": problems}


def memo(aset: AssessmentSet, playbook: Playbook) -> str:
    rows = []
    for a in aset.assessments:
        pos = playbook.position(a.position_id)
        rows.append((pos, a))
    rows.sort(key=lambda r: (_ORDER[r[0].severity], list(Verdict).index(r[1].verdict) * -1))

    blocking = [r for r in rows if r[1].verdict is Verdict.WALK_AWAY]
    needs_approval = [r for r in rows if r[1].verdict in (Verdict.BELOW, Verdict.MISSING)]
    fine = [r for r in rows if r[1].verdict in (Verdict.IDEAL, Verdict.ACCEPTABLE)]

    out = [f"# Negotiation memo: {aset.contract}", "",
           f"Reviewed against **{playbook.name}** v{playbook.version}.", "",
           f"**{len(blocking)} walk-away**, {len(needs_approval)} below standard or missing, "
           f"{len(fine)} at or above acceptable.", ""]

    def section(title: str, items):
        if not items:
            return
        out.extend([f"## {title}", ""])
        for pos, a in items:
            out.append(f"### {pos.topic}  [{pos.severity.value}]  {a.verdict.value}")
            if a.clause_ref:
                out.append(f"Clause {a.clause_ref}.")
            out.append(f"> {a.evidence}")
            if a.reasoning:
                out.append(f"\n{a.reasoning}")
            if a.verdict not in (Verdict.IDEAL, Verdict.ACCEPTABLE):
                out.append(f"\n*Approval:* {pos.authority}")
                if a.comment:
                    out.append(f"*Proposed to counterparty:* {a.comment}")
            out.append("")

    section("Walk-away issues (escalate before responding)", blocking)
    section("Below standard or missing (approval or counter required)", needs_approval)
    section("At or above acceptable", fine)
    return "\n".join(out)
