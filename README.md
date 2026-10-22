# KNOWSTRUCT

KNOWSTRUCT is a requirement system for the knowledge-system effort: the *why* is written down and reviewed before any plan or build exists. Plane is the backlog, the user is product owner and reviewer, and agents bring analysis, requirements, proposals and spikes as tickets. `dev` is its deterministic command-line client for a self-hosted Plane instance, used by the `/dev` Claude Code skill.

## Setup

```
uv sync
cp .env.example .env        # put the ks-agent personal access token in it (never your own)
ln -s $(pwd)/skill/dev ~/.claude/skills/dev
mkdir -p ~/.claude/agents && ln -s $(pwd)/agents/dev-analyst.md ~/.claude/agents/dev-analyst.md
```

## Use

```
uv run dev digest
uv run dev show KS-1
uv run dev --help
```

The `/dev` skill has four moves:

- **digest** — what waits in `Review`, what is `Todo` with nobody on it, and the open tasks, one line each.
- **capture** — turn the conversation into tickets (ideas, a requirement draft, an analysis), written after you have seen them in full.
- **walk through** — work one ticket with the agent as sparring partner: read back, question the why and the judged-by, propose edits, write back after you have seen the full text.
- **run** — carry out an approved `Todo` ticket and post the result for your review. In v1 this covers analyses and spikes only.

## Test

```
uv run pytest -q
```

## Layout

- `src/devsys/` — the `dev` client.
- `skill/dev/` — the `/dev` Claude Code skill (symlinked into `~/.claude/skills/`); ticket templates in `skill/dev/templates/`, the analysis prompt in `skill/dev/prompts/`.
- `agents/dev-analyst.md` — the read-only analyst agent `run` dispatches for analyses (symlinked into `~/.claude/agents/`).
- `docs/tickets/` — the text of the seeded tickets.
- `docs/analysis/` — long-form analyses land here.
- `docs/superpowers/` — the design and the build plan.
- `scripts/seed.sh` — seeds Plane with the initial tickets.
