"""CLI: validate, schema, locate, scaffold, memo, changeset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .changeset import AssessmentSet, changeset, memo
from .locate import locate, split_clauses
from .models import json_schema, load_playbook
from .scaffold import scaffold


def _load(path: Path):
    try:
        return load_playbook(path)
    except ValidationError as e:
        print(f"invalid playbook {path}:\n{e}", file=sys.stderr)
        sys.exit(2)


def cmd_validate(a):
    for p in a.playbook:
        pb = _load(p)
        print(f"ok  {p}  ({pb.name} v{pb.version}, {len(pb.positions)} positions)")
    return 0


def cmd_schema(a):
    print(json.dumps(json_schema(), indent=2))
    return 0


def cmd_locate(a):
    pb = _load(a.playbook)
    clauses = split_clauses(a.contract.read_text(encoding="utf-8"))
    for h in locate(pb, clauses):
        print(f"{h.position.id:28} clause {h.clause.ref:8} {', '.join(h.matched_terms)}")
    return 0


def cmd_scaffold(a):
    pb = _load(a.playbook)
    clauses = split_clauses(a.contract.read_text(encoding="utf-8"))
    print(scaffold(pb, locate(pb, clauses), contract_name=a.contract.name))
    return 0


def cmd_memo(a):
    pb = _load(a.playbook)
    print(memo(AssessmentSet.load(a.assessments), pb))
    return 0


def cmd_changeset(a):
    pb = _load(a.playbook)
    text = a.contract.read_text(encoding="utf-8") if a.contract else None
    cs = changeset(AssessmentSet.load(a.assessments), pb, text)
    print(json.dumps(cs, indent=2))
    return 1 if cs["problems"] else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="playbook", description="Negotiation playbooks as data.")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate")
    v.add_argument("playbook", type=Path, nargs="+")
    v.set_defaults(fn=cmd_validate)

    s = sub.add_parser("schema", help="print JSON Schema for playbook files")
    s.set_defaults(fn=cmd_schema)

    lo = sub.add_parser("locate")
    lo.add_argument("playbook", type=Path)
    lo.add_argument("contract", type=Path)
    lo.set_defaults(fn=cmd_locate)

    sc = sub.add_parser("scaffold")
    sc.add_argument("playbook", type=Path)
    sc.add_argument("contract", type=Path)
    sc.set_defaults(fn=cmd_scaffold)

    me = sub.add_parser("memo")
    me.add_argument("playbook", type=Path)
    me.add_argument("assessments", type=Path)
    me.set_defaults(fn=cmd_memo)

    ch = sub.add_parser("changeset")
    ch.add_argument("playbook", type=Path)
    ch.add_argument("assessments", type=Path)
    ch.add_argument("--contract", type=Path, help="verify `find` strings are verbatim")
    ch.set_defaults(fn=cmd_changeset)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
