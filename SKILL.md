---
name: playbook-review
description: Review a contract against a negotiation playbook (YAML, playbook-as-code schema). Locates the relevant clauses, assesses each position as IDEAL / ACCEPTABLE / BELOW / WALK_AWAY / MISSING with verbatim evidence, and produces a negotiation memo plus a redline-ready changeset. Use when someone asks to "review this against our playbook", "mark up this MSA", or "what do we push back on".
---

# playbook-review

You are reviewing a counterparty's contract against *our* playbook. The playbook is the
authority on what we want; you are the reader who finds where the contract lands.

## Inputs

- A playbook YAML (`playbooks/*.yaml` or one the user supplies). Validate it first:
  `playbook validate <file>`. If it fails, stop and show the error.
- The contract as text or `.md`. If it is `.docx`, convert to text first (pandoc or
  python-docx) and keep the original for the redline step.

## Workflow

### 1. Scaffold

```bash
playbook scaffold <playbook.yaml> <contract.md> > scaffold.md
```

Read the whole scaffold. It tells you, for every position, what ideal / acceptable /
walk-away look like and which clauses the detector found. **The detector is
over-inclusive by design and it misses things**: for every position marked *Not located*,
search the contract yourself for synonyms before recording MISSING.

### 2. Assess each position

For each position, read the located clause(s) *in full*, including cross-referenced
clauses (a cap in clause 7.2 means nothing until you have read 7.3's carve-outs). Then
record:

```json
{
  "position_id": "liability-cap",
  "verdict": "WALK_AWAY",
  "clause_ref": "7.2",
  "evidence": "<verbatim quotation from the contract>",
  "reasoning": "<one to three sentences: which tier it lands in and why>",
  "find": "<verbatim text to replace, if proposing a change>",
  "replace": "<replacement text; omit to use the playbook's fallback_language>",
  "comment": "<one sentence for the counterparty explaining the change>"
}
```

Rules for the verdict:

- `IDEAL` / `ACCEPTABLE`: quote the words that satisfy the tier. No change proposed.
- `BELOW`: between acceptable and walk-away. Propose a change; name the approver from the
  playbook's `authority`.
- `WALK_AWAY`: any walk-away trigger is present. Say which trigger. Propose a change but
  flag that signing requires the approver regardless.
- `MISSING`: the contract is silent after a manual search. `evidence` is the word
  `silent`. Propose insertion of the fallback language if the playbook has it.

`evidence` is always a verbatim quotation. A verdict without a quotation is not a verdict.
If the same clause bears on two positions, assess both; do not merge.

Apply `jurisdiction_notes` where present; they change the analysis (e.g. an unreasonably
low cap under UCTA may be unenforceable, which cuts against pushing for it).

Save the assessments as JSON in the `AssessmentSet` shape (`examples/sample-assessment.json`).

### 3. Memo and changeset

```bash
playbook memo <playbook.yaml> assessments.json > memo.md
playbook changeset <playbook.yaml> assessments.json --contract <contract.md> > changes.json
```

The memo orders issues walk-away first. The changeset is a list of
`{clause_ref, find, replace, comment}` a tracked-changes tool can apply; the command exits
non-zero if any `find` string is not verbatim in the contract, so fix those before handing
it on.

### 4. Hand-off

Present: (a) the one-paragraph summary at the top of the memo, (b) the walk-away list,
(c) the changeset file path. If a redlining tool is available in the session
(docx-redline-mcp or similar), offer to apply the changeset to the original `.docx`; do
not apply it without confirmation.

## Rules

- Never soften a walk-away to BELOW to make the memo look better. The approver decides.
- Never invent evidence. If you cannot find the clause, it is MISSING, not "probably
  covered somewhere".
- The playbook is data. If you think a position is wrong, say so separately; do not
  quietly grade against a position you prefer.
- Do not edit the contract in this skill. Produce the changeset; application is a separate,
  confirmed step.
