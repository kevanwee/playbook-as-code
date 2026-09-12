# playbook-as-code

Negotiation playbooks as data: an open YAML schema for "our position on each clause", a
validator, a clause locator, and a Claude skill that reviews a contract against the
playbook and emits a memo plus a redline-ready changeset.

```yaml
- id: liability-cap
  topic: Limitation of liability
  severity: deal_breaker
  ideal:      Cap at 12 months' fees; exclusions only where required by law.
  acceptable: Cap at 12 months' fees; carve-outs for confidentiality and IP indemnity; 2x super-cap for data.
  walk_away:  Uncapped, or data-protection breach carved out with no super-cap.
  detect:
    any_of: ["aggregate liability", "shall not exceed", "limitation of liability"]
  fallback_language: |
    ...each party's total aggregate liability ... shall not exceed the Fees paid or payable
    in the twelve (12) months immediately preceding the event giving rise to the claim.
  authority: General Counsel
  jurisdiction_notes:
    SG: UCTA s 11 reasonableness applies; an unreasonably low cap risks being struck out.
```

## Why

Every legal team has a playbook. It lives in a Word table nobody opens, so every review
starts from memory. The commercial products that solve this (Luminance, Robin, Spellbook)
keep the playbook format proprietary. There is no open schema, which means no portability,
no diffing your positions against a counterparty's, and no way for an AI assistant to
review against your actual standards rather than generic ones.

The schema is the contribution. The tooling around it is deliberately thin.

## What is in the box

| Piece | What it does |
|---|---|
| `schema/playbook.schema.json` | JSON Schema, generated from the pydantic model. Validate in any language. |
| `playbooks/` | Three real playbooks: SaaS vendor-side, SaaS customer-side, mutual NDA. Singapore-law notes. |
| `playbook validate` | Fails loudly on duplicate ids, empty detectors, bad severities. |
| `playbook scaffold` | Splits a contract into numbered clauses, finds which clauses each position is about, renders a review scaffold. |
| `playbook memo` / `changeset` | Turns completed assessments into a walk-away-first memo and a `{find, replace, comment}` list a tracked-changes tool can apply. |
| `SKILL.md` | The Claude skill that does the actual assessment, with a fixed verdict vocabulary and a "quotation or it didn't happen" rule. |

## Install

```bash
pip install -e ".[dev]"
```

As a Claude skill: clone into `.claude/skills/playbook-review/`. `SKILL.md` at the repo
root is the skill.

## Quick start

```bash
playbook validate playbooks/saas-vendor.yaml
playbook scaffold playbooks/saas-vendor.yaml examples/sample-msa.md     # what to read, per position
# ... assess (by hand or via the skill) into assessments.json ...
playbook memo playbooks/saas-vendor.yaml examples/sample-assessment.json
playbook changeset playbooks/saas-vendor.yaml examples/sample-assessment.json --contract examples/sample-msa.md
```

`examples/sample-msa.md` is a deliberately hostile MSA (3-month one-sided cap, uncapped
data and IP carve-outs, Delaware law, 30-day termination for convenience inside a 36-month
term). Running the vendor playbook against it produces five walk-aways, which is the point.

## The schema

A playbook has a `side` (vendor / customer / mutual / ...), a `contract_type`, a
`jurisdiction`, and a list of positions. Each position has:

| Field | Purpose |
|---|---|
| `id`, `topic`, `severity` | Identity; severity orders the memo (`deal_breaker` > `high` > `medium` > `low`). |
| `ideal` / `acceptable` / `walk_away` | The three tiers. `acceptable` is what the business can sign without Legal; `walk_away` is what nobody can sign without the approver. |
| `detect` | How to find the clause: `any_of` terms, `all_of` terms (gate), `regex`, `headings`. Over-inclusive on purpose. |
| `fallback_language` | Pre-approved text to propose when below acceptable. |
| `authority` | Who approves going below acceptable. |
| `rationale` | Why we care; goes in the memo. |
| `jurisdiction_notes` | Per-jurisdiction legal context that changes the analysis. |

Full schema: `playbook schema`.

## Verdicts

The skill grades each position `IDEAL`, `ACCEPTABLE`, `BELOW`, `WALK_AWAY` or `MISSING`,
always with a verbatim quotation as evidence. The vocabulary is fixed so memos are
comparable across reviewers and over time.

## Changeset format

```json
{
  "changes": [
    {
      "position_id": "liability-cap",
      "severity": "deal_breaker",
      "verdict": "WALK_AWAY",
      "clause_ref": "7.2",
      "find": "<verbatim text in the contract>",
      "replace": "<replacement>",
      "comment": "<one line for the counterparty>",
      "insert_if_missing": false
    }
  ],
  "problems": []
}
```

`find` is checked against the contract text; a non-verbatim `find` is reported in
`problems` and the command exits `1`, so nothing reaches the redline tool that would fail
there. Feed `changes` to [docx-redline-mcp](https://github.com/AnsonLai/docx-redline-mcp),
[legal-redline-tools](https://github.com/evolsb/legal-redline-tools), or a person.

## Writing your own playbook

Copy the closest bundled playbook. Keep `acceptable` honest: it is the tier your commercial
team will sign at without asking you, so if you would actually want to be asked, move that
wording up to `ideal`. Give every position a `walk_away` even if it is "none"; a missing
walk-away reads as "anything goes".

## What this is not

- Not a contract analyser. It does not decide what a clause means; the skill (a reader with
  the contract in front of it) does.
- Not a redliner. It produces the changeset; other tools apply it.
- Not legal advice. The bundled playbooks are illustrative positions with Singapore-law
  notes, not a substitute for your own.

## Related projects

[citecheck](../citecheck), [oblig-register](../oblig-register), [sg-deadline](../sg-deadline).

## License

MIT.
