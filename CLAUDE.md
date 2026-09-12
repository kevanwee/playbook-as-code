# CLAUDE.md — playbook-as-code

Engineering conventions for this repository. They bind AI assistants and humans equally.

## What this is

A schema (`Playbook` in `models.py`, exported to `schema/playbook.schema.json`), three
reference playbooks, thin tooling (locate, scaffold, memo, changeset), and a skill. The
schema is the product; everything else exists to make the schema useful.

## Non-negotiables

1. **The schema is stable.** Adding an optional field is fine. Renaming, removing, or
   making a field required is a major version and needs a migration note in the README.
   `schema/playbook.schema.json` is generated (`playbook schema`) and a test fails if it
   drifts from the model.
2. **Locate is over-inclusive, never clever.** `locate.py` is substring/regex matching by
   design. Do not add embeddings, fuzzy matching, or a model. A missed clause is caught by
   the skill's mandatory manual search; a "smart" locator that silently misses is not.
3. **Verdict vocabulary is fixed.** IDEAL / ACCEPTABLE / BELOW / WALK_AWAY / MISSING. Do not
   add "PARTIAL", "NEEDS_REVIEW" or similar; they exist to avoid making a call.
4. **Evidence is verbatim.** `Assessment.evidence` and `find` are quotations. `changeset()`
   verifies `find` against the contract and reports problems; keep that check.
5. **Bundled playbooks are real.** Positions must be ones a Singapore practitioner would
   recognise, with `jurisdiction_notes` that are accurate. A vague or wrong playbook is worse
   than none because people will copy it. If unsure about a legal note, leave it out.
6. **The skill reports; it does not edit.** Applying the changeset to a document is a
   separate, user-confirmed step outside this repo.

## Layout

```
SKILL.md                     the Claude skill (repo root is the skill directory)
schema/playbook.schema.json  generated; do not hand-edit
playbooks/                   reference playbooks
src/playbook/
  models.py                  schema (pydantic) + loader + json_schema()
  locate.py                  clause splitter + detector matching
  scaffold.py                markdown review scaffold
  changeset.py               Assessment models, memo(), changeset()
  cli.py                     argparse; no logic
examples/                    hostile MSA + a completed assessment for it
tests/
```

## Testing discipline

- Every bundled playbook loads in tests. A playbook that fails validation cannot be
  committed.
- `examples/sample-msa.md` is deliberately hostile and `sample-assessment.json` is a full
  assessment of it. Tests assert the locator finds the specific clauses and the changeset
  round-trips. If you change the sample, update both.
- Detector changes need a positive and a negative test (see `test_all_of_gate_blocks_partial_matches`).
- `python -m pytest` and `ruff check src tests` before every commit.

## Style

- Python 3.11+, type hints, pydantic v2 for the schema, dataclasses for locator output.
- Line length 100.
- Playbook YAML: two-space indent, `>` folded scalars for prose tiers, `|` literal for
  `fallback_language` (whitespace matters in clause text). One blank line between positions.
- Position ids: kebab-case, stable, meaningful (`liability-cap`, not `pos-01`). The same
  topic should have the same id across playbooks so they can be diffed.

## Legal-content conventions

- `acceptable` is what the business may sign without Legal. Write it as a threshold, not
  an aspiration.
- `walk_away` lists triggers, each of which alone is sufficient.
- `jurisdiction_notes` cite the provision (e.g. "PDPA s 26D") so the reader can check.
- Fallback language is pre-approved text. It should be signable as written, not a sketch.

## Commit hygiene

- Imperative subject, scoped: `playbooks(nda): tighten residuals walk-away`.
- Schema changes and playbook changes are never in the same commit.
- No AI attribution lines or co-author trailers.

## What not to build here

- A `.docx` redliner (use docx-redline-mcp or legal-redline-tools with the changeset).
- Clause-meaning analysis or a "risk score". The skill grades against a playbook; that is
  the only scoring.
- A playbook marketplace or registry. Playbooks are files in a repo.
