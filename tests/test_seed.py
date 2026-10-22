import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = (ROOT / "scripts" / "seed.sh").read_text()
KINDS = {"idea", "analysis", "requirement", "proposal", "spike", "iteration", "task"}


def test_only_create_relate_list():
    verbs = re.findall(r"\$KS\s+(\S+)", SCRIPT)
    assert verbs
    assert set(verbs) <= {"create", "relate", "list"}


def test_labels_are_kinds():
    labels = re.findall(r"--label\s+(\S+)", SCRIPT)
    assert labels
    assert set(labels) <= KINDS


def test_body_sources_exist():
    names = re.findall(r"docs/tickets/[\w.-]+\.md|\$T/([\w.-]+\.md)", SCRIPT)
    names = [n for n in names if n]
    assert len(names) == 10
    for n in names:
        assert (ROOT / "docs" / "tickets" / n).is_file(), n


def test_proposal_placeholder_substituted():
    assert "KS-<n>" in (ROOT / "docs/tickets/proposal-zen-ask-v2.md").read_text()
    assert 's/KS-<n>/$REQ/' in SCRIPT
