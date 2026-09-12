"""Split a contract into clauses and find which clauses each position is about.

Deterministic and intentionally over-inclusive: a reviewer would rather dismiss a false hit
than miss a clause. The assistant/skill does the judgement; this module does the pointing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import Playbook, Position

# "12.", "12.3", "12.3.1", "Clause 12", "Section 12", "(a)" are NOT clause starts by themselves.
_CLAUSE_START = re.compile(
    r"^\s*(?:(?:Clause|Section|Article)\s+)?(?P<num>\d{1,2}(?:\.\d{1,2}){0,3})\.?\s+(?P<rest>\S.*)$"
)
_HEADING_ONLY = re.compile(r"^[A-Z][A-Z0-9 ,&/()'\-]{2,60}$")


@dataclass
class Clause:
    ref: str  # "12.3"
    heading: str  # best-effort; may be ""
    text: str  # full text incl. sub-paragraphs until the next clause start
    start_line: int

    @property
    def top_level(self) -> str:
        return self.ref.split(".")[0]


@dataclass
class Hit:
    position: Position
    clause: Clause
    matched_terms: list[str] = field(default_factory=list)
    excerpt: str = ""


def split_clauses(text: str) -> list[Clause]:
    """Split on numbered clause starts. Un-numbered preamble becomes clause '0'."""
    lines = text.splitlines()
    clauses: list[Clause] = []
    cur_ref, cur_heading, cur_lines, cur_start = "0", "Preamble", [], 0
    pending_heading = ""

    for i, line in enumerate(lines):
        m = _CLAUSE_START.match(line)
        if m:
            if cur_lines or clauses or cur_ref != "0":
                clauses.append(Clause(cur_ref, cur_heading, "\n".join(cur_lines).strip(),
                                      cur_start))
            cur_ref = m.group("num")
            rest = m.group("rest").strip()
            # Heading heuristic: short, Title Case or ALL CAPS, no terminal full stop.
            heading = rest if (len(rest) <= 60 and not rest.endswith(".")
                               and rest[:1].isupper()) else pending_heading
            cur_heading = heading
            cur_lines = [line]
            cur_start = i
            pending_heading = ""
        else:
            if _HEADING_ONLY.match(line.strip()):
                pending_heading = line.strip().title()
            cur_lines.append(line)
    clauses.append(Clause(cur_ref, cur_heading, "\n".join(cur_lines).strip(), cur_start))
    return [c for c in clauses if c.text]


def _terms_in(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [t for t in terms if t.lower() in low]


def _excerpt(text: str, term: str, width: int = 220) -> str:
    low = text.lower()
    i = low.find(term.lower())
    if i < 0:
        return text[:width]
    a = max(0, i - width // 3)
    b = min(len(text), i + len(term) + (2 * width) // 3)
    body = re.sub(r"\s+", " ", text[a:b]).strip()
    return ("..." if a else "") + body + ("..." if b < len(text) else "")


def locate(playbook: Playbook, clauses: list[Clause]) -> list[Hit]:
    hits: list[Hit] = []
    for pos in playbook.positions:
        d = pos.detect
        rx = re.compile(d.regex, re.IGNORECASE) if d.regex else None
        for c in clauses:
            matched: list[str] = []
            if d.headings and any(h.lower() in c.heading.lower() for h in d.headings if c.heading):
                matched.append(f"heading:{c.heading}")
            matched += _terms_in(c.text, d.any_of)
            if d.all_of:
                found_all = _terms_in(c.text, d.all_of)
                if len(found_all) == len(d.all_of):
                    matched += found_all
                else:
                    matched = [m for m in matched if m.startswith("heading:")]
            if rx and (m := rx.search(c.text)):
                matched.append(f"regex:{m.group(0)[:40]}")
            if matched:
                term = next((t for t in matched if not t.startswith(("heading:", "regex:"))),
                            None)
                hits.append(Hit(pos, c, matched, _excerpt(c.text, term) if term else c.text[:220]))
    return hits


def missing_positions(playbook: Playbook, hits: list[Hit]) -> list[Position]:
    hit_ids = {h.position.id for h in hits}
    return [p for p in playbook.positions if p.id not in hit_ids]
