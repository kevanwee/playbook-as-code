import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from playbook import (
    AssessmentSet,
    Playbook,
    Verdict,
    changeset,
    load_playbook,
    locate,
    memo,
    scaffold,
    split_clauses,
)
from playbook.cli import main
from playbook.locate import missing_positions
from playbook.models import json_schema

ROOT = Path(__file__).resolve().parent.parent
PLAYBOOKS = ROOT / "playbooks"
EXAMPLES = ROOT / "examples"


@pytest.fixture(scope="session")
def vendor():
    return load_playbook(PLAYBOOKS / "saas-vendor.yaml")


@pytest.fixture(scope="session")
def msa_text():
    return (EXAMPLES / "sample-msa.md").read_text(encoding="utf-8")


def test_all_bundled_playbooks_validate():
    for p in PLAYBOOKS.glob("*.yaml"):
        pb = load_playbook(p)
        assert pb.positions, p


def test_duplicate_position_id_rejected(vendor):
    raw = vendor.model_dump(mode="json")
    raw["positions"].append(raw["positions"][0])
    with pytest.raises(ValidationError, match="duplicate position id"):
        Playbook.model_validate(raw)


def test_detect_requires_something():
    with pytest.raises(ValidationError, match="detect needs"):
        Playbook.model_validate({
            "name": "x", "side": "vendor", "contract_type": "t",
            "positions": [{"id": "a", "topic": "t", "ideal": "i", "acceptable": "a",
                           "walk_away": "w", "detect": {}}],
        })


def test_json_schema_matches_committed_file():
    committed = json.loads((ROOT / "schema" / "playbook.schema.json").read_text("utf-8"))
    assert committed == json_schema(), "run: playbook schema > schema/playbook.schema.json"


def test_split_clauses(msa_text):
    cs = split_clauses(msa_text)
    refs = [c.ref for c in cs]
    assert refs[:3] == ["0", "1", "1.1"]
    assert "7.2" in refs and "9.2" in refs
    c72 = next(c for c in cs if c.ref == "7.2")
    assert "three (3) months" in c72.text
    c7 = next(c for c in cs if c.ref == "7")
    assert c7.heading == "Limitation of Liability"


def test_locate_finds_expected_clauses(vendor, msa_text):
    hits = locate(vendor, split_clauses(msa_text))
    by_pos = {}
    for h in hits:
        by_pos.setdefault(h.position.id, set()).add(h.clause.ref)
    assert "7.2" in by_pos["liability-cap"]
    assert "7.4" in by_pos["consequential-loss"]
    assert "6.1" in by_pos["ip-indemnity"]  # all_of + any_of both satisfied
    assert "5.1" in by_pos["data-protection"]
    assert "8.2" in by_pos["termination-convenience"]
    assert "9.2" in by_pos["governing-law"]
    missing = {p.id for p in missing_positions(vendor, hits)}
    assert "non-solicit" in missing


def test_all_of_gate_blocks_partial_matches(vendor):
    # "indemnify" without "intellectual property" must not hit ip-indemnity
    text = "1. Indemnity\n1.1 The Supplier shall indemnify the Customer for third party claims."
    hits = [h for h in locate(vendor, split_clauses(text)) if h.position.id == "ip-indemnity"]
    assert hits == []


def test_scaffold_renders_every_position(vendor, msa_text):
    md = scaffold(vendor, locate(vendor, split_clauses(msa_text)), contract_name="MSA")
    for p in vendor.positions:
        assert f"`{p.id}`" in md
    assert "**Not located.**" in md  # non-solicit
    assert "UCTA" in md  # jurisdiction note surfaced


def test_memo_and_changeset(vendor, msa_text):
    aset = AssessmentSet.load(EXAMPLES / "sample-assessment.json")
    m = memo(aset, vendor)
    assert m.index("Walk-away issues") < m.index("Below standard or missing")
    assert "Limitation of liability" in m

    cs = changeset(aset, vendor, msa_text)
    assert cs["problems"] == []
    ids = [c["position_id"] for c in cs["changes"]]
    assert "sla-sole-remedy" not in ids  # ACCEPTABLE -> no change
    assert ids[0] == "liability-cap"  # deal_breaker sorts first
    fallback = next(c for c in cs["changes"] if c["position_id"] == "consequential-loss")
    assert fallback["replace"].startswith("Neither party shall be liable")  # from playbook
    missing = next(c for c in cs["changes"] if c["position_id"] == "auto-renewal")
    assert missing["insert_if_missing"] is True


def test_changeset_flags_non_verbatim_find(vendor, msa_text):
    aset = AssessmentSet(contract="c", playbook="p", assessments=[{
        "position_id": "liability-cap", "verdict": Verdict.BELOW, "evidence": "x",
        "find": "text that is not in the contract"}])
    cs = changeset(aset, vendor, msa_text)
    assert cs["problems"] and "verbatim" in cs["problems"][0]


def test_cli_roundtrip(capsys):
    assert main(["validate", str(PLAYBOOKS / "saas-vendor.yaml")]) == 0
    assert main(["locate", str(PLAYBOOKS / "saas-vendor.yaml"),
                 str(EXAMPLES / "sample-msa.md")]) == 0
    assert "liability-cap" in capsys.readouterr().out
    assert main(["changeset", str(PLAYBOOKS / "saas-vendor.yaml"),
                 str(EXAMPLES / "sample-assessment.json"),
                 "--contract", str(EXAMPLES / "sample-msa.md")]) == 0
