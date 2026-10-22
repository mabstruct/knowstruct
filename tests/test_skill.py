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


ROOT = Path(__file__).parents[1]


def test_skill_names_both_analysis_paths():
    text = SKILL.read_text()
    assert "ks-analyst" in text and "session model" in text
    assert "does not exist yet" not in text


def test_analyst_agent_has_no_shell():
    agent = (ROOT / "agents" / "ks-analyst.md").read_text()
    front = agent.split("---")[1]
    tools = next(l for l in front.splitlines() if l.startswith("tools:"))
    assert "name: ks-analyst" in front and "Bash" not in tools
    assert ".env" in agent


def test_analysis_prompt_forbids_env_and_ks():
    prompt = (SKILL.parent / "prompts" / "analysis-agent.md").read_text()
    assert ".env" in prompt and "{slug}" in prompt and "do not run `ks`" in prompt.lower()
