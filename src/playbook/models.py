"""Playbook schema (pydantic). `schema/playbook.schema.json` is generated from this file;
run `playbook schema > schema/playbook.schema.json` after changing anything here."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class Side(StrEnum):
    VENDOR = "vendor"
    CUSTOMER = "customer"
    MUTUAL = "mutual"
    LICENSOR = "licensor"
    LICENSEE = "licensee"
    EMPLOYER = "employer"
    OTHER = "other"


class Severity(StrEnum):
    DEAL_BREAKER = "deal_breaker"  # walk-away territory; escalate immediately
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Detect(BaseModel):
    """How to find the clause(s) a position is about. Case-insensitive substring match on
    `any_of`; every term in `all_of` must be present; `regex` is a raw pattern."""

    any_of: list[str] = Field(default_factory=list)
    all_of: list[str] = Field(default_factory=list)
    regex: str | None = None
    headings: list[str] = Field(default_factory=list, description="clause headings to match")

    @model_validator(mode="after")
    def _non_empty(self) -> Detect:
        if not (self.any_of or self.all_of or self.regex or self.headings):
            raise ValueError("detect needs at least one of any_of / all_of / regex / headings")
        return self


class Position(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    topic: str
    severity: Severity = Severity.MEDIUM
    ideal: str = Field(description="what we open with / would love to get")
    acceptable: str = Field(description="what we can sign without escalation")
    walk_away: str = Field(description="what we cannot sign; escalate or decline")
    detect: Detect
    fallback_language: str | None = Field(
        default=None, description="pre-approved clause text to propose when below acceptable"
    )
    authority: str = Field(
        default="Legal", description="who can approve signing below `acceptable`"
    )
    rationale: str | None = Field(default=None, description="why we care; for the memo")
    jurisdiction_notes: dict[str, str] = Field(
        default_factory=dict, description="e.g. {'SG': 'UCTA s 11 reasonableness...'}"
    )
    tags: list[str] = Field(default_factory=list)


class Playbook(BaseModel):
    name: str
    version: str = "1"
    side: Side
    contract_type: str
    jurisdiction: str = "SG"
    owner: str | None = None
    updated: date | None = Field(default=None, description="ISO date (YAML parses it natively)")
    summary: str | None = None
    positions: list[Position]

    @model_validator(mode="after")
    def _unique_ids(self) -> Playbook:
        seen = set()
        for p in self.positions:
            if p.id in seen:
                raise ValueError(f"duplicate position id {p.id!r}")
            seen.add(p.id)
        return self

    def position(self, pid: str) -> Position:
        for p in self.positions:
            if p.id == pid:
                return p
        raise KeyError(pid)


def load_playbook(path: str | Path) -> Playbook:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Playbook.model_validate(raw)


def json_schema() -> dict:
    return Playbook.model_json_schema()
