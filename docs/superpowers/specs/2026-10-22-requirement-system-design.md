# KNOWSTRUCT requirement system — backlog, requirement cycle, lead agent

Status: draft, 2026-10-22. From the brainstorm of 2026-10-21/22. This document describes a *development process* and the thin tooling it needs, not a feature of ZEN. It lives in `knowstruct/docs/superpowers/`.

## 1. Intent

Three knowledge-system approaches were built in succession — CLAWSTRUCT (OpenClaw agents and skills), CONSTRUCT (LangGraph workflows and a GUI), ZENSTRUCT (ZEN: markdown vault, Claude-maintained wiki, qmd search). Each went from idea to spec to months of building. None reaches the target. The best results came from the first and least manageable one; the second organised knowledge per source and never formed an entity-level view; the third re-finds snippets well but surfaces no insight from the collection.

The user's diagnosis, which this document adopts: the gap is upstream of the code. Ideas have no place to wait, the *why* is never written down and reviewed before a plan exists, and the target widened underneath the three builds (physical AI → research → any knowledge across work and life) without anyone noticing what got lost at each widening. `zen-ask` v2 is the current example: a well-made spec for a feature nobody has shown to be the bottleneck.

So, before any further build: a backlog where ideas wait, a requirement cycle where the why is written and reviewed, agents that bring analysis, options and time-boxed experiments as proposals, and the user acting as product owner and reviewer, in their own time. The first content of the system is a re-analysis of all three approaches.

## 2. Goals, non-goals, anti-goals

Goals

1. Every idea has a place (a Plane issue) and nothing is built from an idea that has not become a reviewed requirement.
2. Two equal ways to review, chosen per ticket: in Plane alone, asynchronously, at the user's pace (editing the ticket toward a clarification); or walking through the ticket with the lead agent as a sparring partner, who questions, clarifies and edits with the user and writes the result back. Neither is required for the other.
3. Agents work with autonomy inside a ticket: analysis, requirement drafts, proposals with options, time-boxed spikes (POCs). Each ends in something the user can approve or reject.
4. Findings from the three approaches stay attributed to their approach and are consolidated in one stream (KS).
5. Every proposal can be judged on a domain where the user can tell good from bad (physical AI, cosmology, math, general AI).

Non-goals

- No new platform. Plane is the backlog; Claude Code is the agent runtime; the existing superpowers flow (brainstorm → spec → plan → subagent-driven build → review) stays the build process inside an approved iteration.
- No change to ZEN's product code, vault or wiki in this work.
- No automation that acts on Plane without a session: no bots, no webhooks, no scheduled runs in v1.

Anti-goals — the work fails even if it runs when:

- The requirement system becomes the fourth multi-month project. The tooling is one skill and one small client; if it grows beyond that, stop and write a requirement for it.
- A spike's code survives as product code. Spikes end in a proposal; keeping anything is a new ticket.
- The agent decides a requirement, a conflict between findings, or a priority. It proposes; the user decides.
- Ask-v2 or any existing draft gets built because it is already written.

## 3. Constraints

- Plane, self-hosted at `PLANE_BASE_URL`, workspace `mabstruct`, REST `/api/v1/workspaces/mabstruct/…`, header `x-api-key`. Token in `.env` as `PLANE_API_KEY` (in `zen/.env` today, in `knowstruct/.env` once that repo exists, §4.5); a global PreToolUse hook blocks any Bash command that names `.env`, so all Plane access goes through a Python client that loads `.env` itself and never prints the key. The token must never appear in chat, logs, commits or Plane itself.
- **Two identities** (user's decision): the agent acts in Plane as its own member, `ks-agent`, with its own personal access token; that is the token in `.env`. The user acts only through the Plane UI as themselves. So every agent write is attributed in Plane's history, and "only the user moves an issue out of `Review`" is enforceable: the client refuses to set `Done` or `Cancelled` at all.
- Plane stores bodies and comments as HTML (`description_html`, `comment_html`). The client converts markdown → HTML on write and HTML → markdown on read, with one small dependency each; the round trip is lossy after rich-text edits in Plane, so the walk-through move shows the exact change before any body rewrite (§4.4).
- Four projects exist (ids in the Claude memory `plane-requirement-system`): `CLAWSTRUCT`, `CONSTRUCT`, `ZENSTRUCT`, `KS` (name KNOWSTRUCT). Each has the default states, a `Review` state (group `started`) and labels `analysis`, `idea`, `requirement`, `proposal`, `spike`.
- Folder map of `~/dev/mabstruct/` as the user gave it (Claude memory `mabstruct-folder-map`): `mabstruct-workspace/` is CLAWSTRUCT, `construct/` is CONSTRUCT (`construct-testws/` a sample of one phase), `zen/` is ZENSTRUCT; `evolving/`, `mabstruct_articles/`, `mabstruct-site/`, `mab-notes/`, `physicalAI/`, `research/` are context.
- Python with `uv`, pytest, macOS, zsh. No LLM calls from the client; it is deterministic.
- The user's review time is the scarce resource. Everything that reaches `Review` must be readable in Plane alone, without the chat transcript.

## 4. The parts

### 4.1 Plane structure

Projects: `CLAWSTRUCT`, `CONSTRUCT`, `ZENSTRUCT` hold what concerns one approach: its analysis, ideas and spikes that only make sense there. `KS` holds the consolidated stream: requirements, cross-approach proposals, decisions, iterations.

Issue kinds, by label (one kind label per issue):

| label | what it is | who writes it | done when |
|---|---|---|---|
| `idea` | a thought, unshaped; may be one line | user or agent | promoted to a requirement, or cancelled |
| `analysis` | findings about something that exists (an approach, a corpus, a tool) | agent | user has read it and moved it to Done; requirements it suggests exist as separate issues |
| `requirement` | the why: what the system must make possible and how success would be recognised | agent drafts from conversation or analysis; user owns the text | user approves (Done) or rejects (Cancelled) |
| `proposal` | options for *how* to meet a requirement, each with trade-offs and cost, and a recommendation | agent | user picks an option or sends it back |
| `spike` | a time-boxed experiment answering one question; result is a proposal or a finding | agent | the proposal/finding exists; the spike's code is discarded |
| `iteration` (new label) | an approved unit of build: links the requirement, the chosen proposal, the plan; carries the phase result | lead agent opens, dev flow fills | phase result approved |
| `task` (new label) | a general follow-up or reminder outside the cycle (revoke a token, set up SMTP, move a file); has an owner (user or agent) and a one-line "done when"; prioritised with Plane's priority field, parked in `Backlog`, cancelled by the user at any time | user, or agent via *capture* when a conversation leaves loose ends | the owner has done it |

States, same in every project: `Backlog` (waiting), `Todo` (approved to start), `In Progress` (an agent is on it), `Review` (waiting on the user), `Done`, `Cancelled`. Only the user moves an issue out of `Review`.

Relations: `parent` for requirement → its proposals/spikes/iterations; Plane's "relates to" for cross-project links (e.g. a CONSTRUCT analysis finding that feeds a KS requirement). Every issue in an approach project that produced a KS requirement links to it.

Cycles: one Plane cycle per iteration round, in KS. Not used in v1 beyond that.

Issue bodies are markdown with a fixed skeleton per kind (§4.3), so the user can read and edit them in Plane without the agent.

### 4.2 The cycle

```
idea ──► requirement (draft) ──► Review ──► approved
                                   │            │
                                   ▼            ▼
                                rejected    proposal / spike ──► Review ──► option chosen
                                                                               │
                                                                               ▼
                                                          iteration: spec → plan → build → phase result ──► Review ──► Done
```

- A requirement is never written as a feature. Its skeleton forces the why, the evidence, and how the user would judge it.
- A proposal gives at least two options. "Do nothing" is a valid option. The recommendation is marked as the agent's.
- A spike has a time box (wall-clock or token budget, set on the ticket), one question, and a stated domain to show itself on. It ends in a proposal or an analysis finding, posted as a comment and a new issue; its code lives in the scratchpad or a throwaway branch and is deleted.
- An iteration runs the existing superpowers build flow. Its spec and plan are committed in the repo of the approach it touches; the ticket links them. The phase result is a comment: what was built, how it was verified, what the user should look at, and the open points. Then `Review`.
- The user decides in Plane: state change plus a comment whose first line is `chosen: <option letter>` or `rejected: <reason>` (my call; the digest shows the latest comment regardless, and the skill asks the user when it cannot tell what was decided). A rejection with no reason is a question back to the user in the next session.

### 4.3 Ticket skeletons

Requirement:

```
## Why
(the need, in the user's terms; the moment it would matter)
## Evidence
(what in the three approaches, the corpora or the conversation shows it)
## Judged by
(the domain and the concrete test the user would apply)
## Out of scope
## Source
(links to analysis/idea issues, conversation date)
```

Proposal:

```
## Requirement
(link)
## Options
### A …  — what, trade-offs, cost (calls/time), risk
### B …
## Recommendation (agent's)
## What a spike would settle
```

Analysis (per approach): what it was meant to do; what it actually produced (with paths); what the user got from it; where it hurt (unmanageable, unsatisfying, flat); the one thing it did that the others did not; candidate requirements (one line each, become `requirement` drafts in KS).

Spike: question, time box, domain, result (filled at the end), proposal link.

Phase result (comment on the iteration): built, verified how, look at, open.

### 4.4 The lead agent

A Claude Code skill, working name `/ks`, backed by a small deterministic Plane client (`ks` package: `uv` project, Python, urllib, loads `.env`, prints never the key). The skill has four moves; the user names one or the agent picks from context:

1. **digest** — list what waits in `Review`, what is `Todo` with nobody on it, and the open `task` issues with their priority, across the four projects, with one line each. Default move at session start when the user asks for status.
2. **capture** — turn the current conversation into issues: ideas, a requirement draft, an analysis. Shows the skeletons filled in before writing to Plane; writes on the user's yes.
3. **walk through** — open one issue and work it with the user as a sparring partner: read it back, ask what is unclear or unproven in it, challenge the why and the judged-by, propose edits, and write the agreed body and a comment back. Plane stays the record; nothing is written the user has not seen in chat first. Because the user may have edited the body in Plane's rich editor since, the agent always re-reads before proposing and shows the exact replacement text before writing it.
4. **run** — for an approved `Todo` issue: an `analysis` dispatches read-only subagents; a `spike` runs in the scratchpad with its time box. Each ends with the result posted to Plane and the state set to `Review`. The agent never sets `Done`.

**Scope of v1** (my call): digest, capture, walk through, and `run` for `analysis` and `spike`. `run` for `iteration` (the superpowers plan/build flow, phase-result comment, cycle creation) is not built until the first requirement is approved; it then becomes its own `KS` ticket. Iterations that touch CONSTRUCT or CLAWSTRUCT are outside v1 altogether; only `zen/` has implementer and reviewer agents.

"Dev teams" are what `run` dispatches: the existing agents (`zen-implementer`, `zen-reviewer`, Explore, general-purpose), not a new orchestration layer.

The client exposes roughly: `list_issues(project, state=None, label=None)`, `get_issue`, `create_issue(project, title, body, label, parent=None, relates=())`, `update_issue(state=None, body=None)` (refuses `Done`/`Cancelled`), `comment(issue, text)`, `relate(issue, other)` (Plane v1 has a relations endpoint with `relates_to`; pagination is cursor-based, `per_page` ≤ 100). Tests use a stubbed HTTP layer; no test touches the real Plane.

### 4.5 Where things live

My call: a new, small repo `~/dev/mabstruct/knowstruct/`, created in this build, holds the `ks` client (a `uv` project), `.env` (gitignored, with a committed `.env.example`), `docs/analysis/` (the long-form analyses) and this design. `zen/` stays app development for ZEN only, per the user's standing rule, and nothing of this lands in `zen/` product code.

The `/ks` skill is a **user-level** skill in `~/.claude/skills/ks/`, not a project skill, so it is available whichever repo a session starts in (an iteration later commits into `zen/`; an analysis reads `construct/`). It runs the client with `uv run --project ~/dev/mabstruct/knowstruct ks …`; the client locates `.env` next to its own `pyproject.toml`, so the session's working directory does not matter.

### 4.6 First content

In this order, each its own ticket:

1. `KS-?` **requirement**: the knowledge system (draft from this conversation, §5 below is its substance). `Review`.
2. Three **analysis** issues, one per approach project, run as three parallel read-only agents answering §4.3's analysis questions; long form committed to `docs/analysis/<approach>.md`, summary and candidate requirements in the issue. Plus one `KS` analysis: *what got lost at each widening of the target* (physical AI → research → everything), read by the lead agent across the context folders. All four `Review`.

   Budget (my call): each analysis agent reads prompts, skills, agent and workflow definitions, docs, configuration and produced outputs (workspaces, wikis, articles); it does not read code bodies beyond what those point to, and skips `node_modules/`, `.venv/`, binaries and papers. `research/` is listed only (file count, titles from filenames), never read. `physicalAI/` contributes its README and folder structure. Each agent gets a token cap written on its ticket (first value: 400k tokens of reading); if it runs out, it reports what it covered and what it skipped, and that is the result. Analyses run on the session model.
3. `ZENSTRUCT` **proposal**: `zen-ask` v2, moved from "next build" to one option under the ask-half of the requirement, with its existing spec linked. `Backlog` until the requirement is approved.
4. The user's existing `CONSTRUCT-1 "review current state"` becomes the parent of the CONSTRUCT analysis.

### 4.7 Skills per stage

Subagents do not pick up skills on their own: the superpowers entry skill tells a dispatched subagent to ignore it, so a subagent follows only what its agent definition or its prompt says. Rule: **the session that runs `/ks` invokes the process skills; agent definitions carry their working rules inline** (as `zen-implementer` already does with TDD). Anything an agent must obey — ZEN hard rules, no network in `tools/`, the token never printed — is repeated in its definition, never assumed from a skill.

| stage | skill | who runs it |
|---|---|---|
| idea → requirement | `brainstorming`, conversation part only; the "written design" is the requirement ticket, not a spec | the session, with the user |
| analysis | none; read-only agents (Explore / general-purpose) with the §4.3 questions in the prompt; `dispatching-parallel-agents` to run several at once | the session dispatches |
| proposal | none as a skill; the agent writes options and marks its recommendation | a general-purpose agent, or the session |
| spike | none by design: no TDD, no plan, time box and domain in the prompt; result is a proposal | one agent in the scratchpad |
| iteration | `brainstorming` (the spec) → `writing-plans` → `subagent-driven-development` with `zen-implementer` (TDD inline) and `zen-reviewer` → `verification-before-completion` → `finishing-a-development-branch` → phase result to Plane | the session orchestrates, in the touched repo |
| bug found anywhere | `systematic-debugging` | whoever hits it |
| walk through | none; conversation, then write-back | the session, with the user |

`using-git-worktrees` stays optional; zen works on branches.

### 4.8 Models

Same rule as ZEN's baseline: a cheap model where the work carries out something already decided, a premium model where judgement is the work, none where it can be deterministic. Tiers available: Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.1 (the session model at the time of writing). Each agent file's `model:` line is the single place to change a choice.

| agent | model | why |
|---|---|---|
| lead agent (`/ks`: digest, capture, walk through, orchestrating runs) | the session model (`/model`) | interactive, judgement-heavy, small context per move |
| `ks` client | none | deterministic Python |
| analysis agents (three, read-only, long reading) | premium: Opus 5.5 | judgement over large, messy material; three runs, cost bounded |
| "what got lost" analysis | the session model | the lead agent does it itself, with conversation context |
| proposal writer | premium: Opus 5.5 | options and trade-offs are judgement |
| spike, research-shaped | premium: Opus 5.5 | the result is a judgement |
| spike, build-shaped | Sonnet 5.5 | code under a time box; code quality does not matter |
| Explore / search helpers | Haiku 5.5 | find things, report paths |
| builder-check reviewer of a design | Opus 5.5 | one read, questions only |
| `zen-implementer` | Sonnet 5.5 (as set) | the plan carries the design |
| `zen-reviewer` | Opus 5.5 (as set) | spotting drift is judgement |
| ingest agents | unchanged, per `docs/benchmarks/2026-10-15-ingest-model-comparison.md` | already measured |

No benchmark compares Fable 5.1 and Opus 5.5 on this work: "premium" means Opus where an agent file needs a fixed `model:` line, and the session model where it is simply the session. The first three analyses are the place to notice a wrong tier before anything repeats.

## 5. Decided by the user

- Plane is the backlog; one project per approach plus `KS` for consolidation; names CLAWSTRUCT, CONSTRUCT, ZENSTRUCT, KS/KNOWSTRUCT.
- Two review modes, both first-class: editing a ticket in Plane alone, in the user's own time, with a clarification goal; or walking through the ticket with an agent as sparring partner.
- Agents get autonomy to experiment and come back with proposals (requirement proposals and POCs); the user approves or rejects.
- The knowledge system target, as stated 2026-10-22: add sources → digest, evaluating connections → ask around the base, and browse a landscape. Knowledge held per entity (insights, connections, syntheses, entities, sources, references, persons, places, considerations), not per source. The landscape is layered: a handful of themes at the top (cosmology → early universe, galaxies, formation, stars, general relativity, quantum gravity, string theory), detail only as one browses in, never hundreds of nodes at once. Asking returns about five good suggestions; following one reaches the depth that topic needs, then links and wiki pages. Quality can be judged by the user in physical AI, cosmology, math and general AI.
- Physical AI was the initial motor, not the yardstick; the target was generalised to research and then to any knowledge across work and life.
- The agent gets its own Plane member and token (`ks-agent`); the user's own token is not used by the tooling.

## 6. My calls (reversible, marked)

Issue kinds as labels (not Plane issue types), the `iteration` label, the `Review` state in group `started`, the skeletons in §4.3, the four skill moves and the v1 scope of `run` (§4.4), the `chosen:`/`rejected:` comment convention (§4.2), the client's shape and its hard refusal of `Done`/`Cancelled`, the new `knowstruct/` repo and the user-level skill (§4.5), the analysis budget (§4.6), the order of first content, the analysis questions, and the reading that ask-v2 is the ask-half without the generalisation layer.

## 7. Left to the builder

Exact client module layout and test stubs; the markdown/HTML conversion libraries; the digest's text layout; how issue ids are quoted back in chat; the analysis agents' prompts beyond §4.3; where spike time boxes and token caps are recorded on the ticket (a line in the body is fine).

## 8. Cost

One skill, one client of a few hundred lines, no model calls in the tooling. The analysis step is the first real spend: three read-only agents over three codebases plus one context read. After that, cost is per ticket and visible on the ticket.
