"""playbook-as-code: negotiation playbooks as data.

    load_playbook(path)            -> Playbook (validated)
    split_clauses(text)            -> list[Clause]
    locate(playbook, clauses)      -> list[Hit]  which clauses touch which positions
    scaffold(playbook, hits)       -> markdown review scaffold for the assistant/reviewer
    Assessment / changeset(...)    -> redline-ready JSON from completed assessments
"""

from .changeset import Assessment, AssessmentSet, Verdict, changeset, memo
from .locate import Clause, Hit, locate, split_clauses
from .models import Playbook, Position, load_playbook
from .scaffold import scaffold

__all__ = [
    "Playbook",
    "Position",
    "load_playbook",
    "Clause",
    "Hit",
    "split_clauses",
    "locate",
    "scaffold",
    "Verdict",
    "Assessment",
    "AssessmentSet",
    "changeset",
    "memo",
]

__version__ = "0.1.0"
