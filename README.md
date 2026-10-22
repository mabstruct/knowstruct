# KNOWSTRUCT

KNOWSTRUCT is a requirement system for the knowledge-system effort: the *why* is written down and reviewed before any plan or build exists. Plane is the backlog, the user is product owner and reviewer, and agents bring analysis, requirements, proposals and spikes as tickets. `ks` is its deterministic command-line client for a self-hosted Plane instance, used by the `/ks` Claude Code skill.

## Setup

```
uv sync
cp .env.example .env        # put the ks-agent personal access token in it (never your own)
ln -s $(pwd)/skill/ks ~/.claude/skills/ks
```

## Use

```
uv run ks digest
uv run ks show KS-1
uv run ks --help
```

The `/ks` skill has four moves:

- **digest** — what is open, what waits for your review, what changed.
- **capture** — turn an idea or a note into a ticket in the backlog.
- **walk through** — step through a ticket or a requirement with you, one decision at a time.
- **run** — let an agent carry out an approved analysis, proposal or spike and report back as a ticket.

## Test

```
uv run pytest -q
```

## Layout

- `src/ks/` — the `ks` client.
- `skill/ks/` — the `/ks` Claude Code skill (symlinked into `~/.claude/skills/`).
- `docs/tickets/` — ticket text and templates.
- `docs/analysis/` — long-form analyses land here.
- `docs/superpowers/` — the design and the build plan.
- `scripts/seed.sh` — seeds Plane with the initial tickets.
