"""Render a review scaffold: for every position, what the playbook wants and which clauses
the contract has on the point. This is the document the assistant (or a junior) fills in."""

from __future__ import annotations

from collections import defaultdict

from .locate import Hit, missing_positions
from .models import Playbook


def scaffold(playbook: Playbook, hits: list[Hit], *, contract_name: str = "the contract") -> str:
    by_pos: dict[str, list[Hit]] = defaultdict(list)
    for h in hits:
        by_pos[h.position.id].append(h)
    missing = missing_positions(playbook, hits)

    out = [
        f"# Review scaffold: {contract_name}",
        "",
        f"Playbook: **{playbook.name}** v{playbook.version} ({playbook.side.value} side, "
        f"{playbook.contract_type}, {playbook.jurisdiction})",
        "",
        f"{len(playbook.positions)} positions; {len(playbook.positions) - len(missing)} "
        f"located in the contract, {len(missing)} not found.",
        "",
        "For each position: read the located clauses in full, then record a verdict "
        "(IDEAL / ACCEPTABLE / BELOW / WALK_AWAY / MISSING) with a quotation as evidence. "
        "See SKILL.md.",
        "",
    ]
    for pos in playbook.positions:
        out += [f"## {pos.topic}  `{pos.id}`  [{pos.severity.value}]", ""]
        if pos.rationale:
            out += [f"*Why we care:* {pos.rationale}", ""]
        out += [
            "| Tier | Position |", "|---|---|",
            f"| Ideal | {pos.ideal} |",
            f"| Acceptable | {pos.acceptable} |",
            f"| Walk away | {pos.walk_away} |",
            "",
        ]
        jn = pos.jurisdiction_notes.get(playbook.jurisdiction)
        if jn:
            out += [f"*{playbook.jurisdiction} note:* {jn}", ""]
        hs = by_pos.get(pos.id, [])
        if not hs:
            out += ["**Not located.** Either the contract is silent (record MISSING) or the "
                    "clause uses wording the detector does not know; search manually before "
                    "concluding it is absent.", ""]
        else:
            out += ["Located in:", ""]
            for h in hs:
                head = f" {h.clause.heading}" if h.clause.heading else ""
                out += [f"- **Clause {h.clause.ref}**{head}  (matched: "
                        f"{', '.join(h.matched_terms)})", f"  > {h.excerpt}", ""]
        out += [f"*Approval to go below acceptable:* {pos.authority}", ""]
        if pos.fallback_language:
            out += ["<details><summary>Pre-approved fallback language</summary>", "",
                    "```", pos.fallback_language.strip(), "```", "", "</details>", ""]
    return "\n".join(out)
