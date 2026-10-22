import re
from pathlib import Path

SKILL = Path(__file__).parents[1] / "skill" / "ks" / "SKILL.md"


def test_skill_only_calls_existing_subcommands():
    used = set(re.findall(r"\bks (whoami|projects|digest|show|list|create|update|comment|relate|decision|\w+)\b", SKILL.read_text()))
    assert used <= {"whoami", "projects", "digest", "show", "list", "create", "update", "comment", "relate", "decision"}


def test_templates_have_skeleton_headings():
    t = SKILL.parent / "templates"
    assert (t / "requirement.md").read_text().startswith("## Why")
    assert {"## Requirement", "## Options", "## Recommendation (agent's)", "## What a spike would settle"} <= set(l.strip() for l in (t / "proposal.md").read_text().splitlines())
    for name in ("analysis", "spike", "task", "phase-result"):
        assert (t / f"{name}.md").exists()


def test_skill_never_sets_done():
    assert "--state Done" not in SKILL.read_text() and "--state Cancelled" not in SKILL.read_text()
