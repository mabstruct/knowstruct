---
name: ks
description: Lead agent for the KNOWSTRUCT requirement system in Plane — digest, capture, walk through, run. Use for status, backlog, requirements, proposals, spikes, analyses, tasks.
---

# /ks — KNOWSTRUCT lead agent

Plane (workspace `mabstruct`, projects `CLAWSTRUCT`, `CONSTRUCT`, `ZENSTRUCT`, `KS`) is the record of what the user wants built. This skill reads and writes Plane through a small deterministic client and works tickets with the user. Files referenced below live in the skill directory (`templates/`, `prompts/`) and in the repo `/Users/mab/dev/mabstruct/knowstruct`.

## The rule

1. Agents never set `Done` or `Cancelled`. Only the user does, in Plane. A run ends in `Review`.
2. Nothing is written to Plane that the user has not seen in chat first, in full, and approved.
3. The Plane token is never read, printed or quoted. Never open, cat or name the `.env` file.
4. All Plane access goes through the client, always spelled:

```
uv run --project /Users/mab/dev/mabstruct/knowstruct ks <subcommand> ...
```

The subcommands, and nothing else:

| command | does |
|---|---|
| `ks whoami` | show which Plane user the token belongs to |
| `ks projects` | list the four projects |
| `ks digest [--today YYYY-MM-DD]` | what waits in Review, Todo without owner, open tasks |
| `ks show REF [--json]` | one issue (`KS-12`), body as markdown, comments |
| `ks list PROJECT [--state S] [--label L]` | issues of a project |
| `ks create PROJECT --label L --title T (--body-file F \| --body B) [--state S] [--priority P] [--parent REF] [--relates REF ...]` | new issue |
| `ks update REF [--state S] [--body-file F] [--title T] [--priority P]` | change an issue |
| `ks comment REF (--file F \| --text T)` | add a comment |
| `ks relate REF OTHER` | link two issues (a `relates to:` comment) |
| `ks decision REF` | the user's latest decision on an issue |

(The table is shorthand. When you run one, write the full command with the `uv run --project ...` prefix.)

Issue kind is exactly one label: `idea`, `analysis`, `requirement`, `proposal`, `spike`, `iteration`, `task`. States: `Backlog`, `Todo`, `In Progress`, `Review`, `Done`, `Cancelled`. Bodies are markdown on your side; the client converts to and from Plane's HTML.

The user names a move, or you pick one from context. Four moves: digest, capture, walk through, run.

## Move 1: digest

Default when the user asks for status or starts a session.

1. Run `uv run --project /Users/mab/dev/mabstruct/knowstruct ks digest`.
2. Show the output to the user: what waits in `Review`, what is `Todo` with nobody on it, open `task` issues with priority, one line each, across the four projects.
3. For each `Review` item whose latest comment may hold a decision, run `uv run --project /Users/mab/dev/mabstruct/knowstruct ks decision REF` and report it (see the `chosen:`/`rejected:` convention below).
4. Offer the next move (walk through one item, or run a `Todo`). Writes nothing.

## Move 2: capture

Turn the current conversation into issues: ideas, a requirement draft, an analysis.

1. Decide what is in the conversation: each `idea`, a `requirement` (only if why, evidence and judged-by are there), an `analysis`. A requirement is never a feature description.
2. For each, read the matching template in `templates/` (`requirement.md`, `analysis.md`, `task.md`, `proposal.md`, `spike.md`) and fill every heading from the conversation. Where the conversation does not support a heading, write `unknown` and ask the user; do not invent.
3. Show in chat, for each issue: project, label, title, state (`Backlog` for ideas, `Review` for a finished requirement draft or analysis), parent/relates, and the complete filled body.
4. Wait for the user's yes, or edits. Then, per issue, write the body to a temp file and run:
   `uv run --project /Users/mab/dev/mabstruct/knowstruct ks create PROJECT --label LABEL --title "TITLE" --body-file FILE --state STATE`
   adding `--parent REF` and `--relates REF ...` where they apply. Cross-project links are made with `uv run --project /Users/mab/dev/mabstruct/knowstruct ks relate REF OTHER`.
5. Report the new refs. Check the project with `uv run --project /Users/mab/dev/mabstruct/knowstruct ks list PROJECT --label LABEL` if the user wants proof.

## Move 3: walk through

Open one issue and work it with the user as a sparring partner. Plane stays the record.

1. Run `uv run --project /Users/mab/dev/mabstruct/knowstruct ks show REF`. Read it back to the user in a few lines.
2. Ask what is unclear or unproven. Challenge the why and the judged-by: is the need in the user's terms? Could the user actually apply the test? Does the evidence show it? Propose edits.
3. When an edit is agreed, the user may have changed the body in Plane's rich editor meanwhile. Re-run `uv run --project /Users/mab/dev/mabstruct/knowstruct ks show REF` and base the new body on that fresh read, not on the earlier one. If it changed, say what changed.
4. Print the full replacement body in chat. Not a diff, the whole text. Wait for the user's yes.
5. Write it to a temp file and run `uv run --project /Users/mab/dev/mabstruct/knowstruct ks update REF --body-file FILE`. Add `--state Review` only when the user says it is ready for their decision. Never `Done`, never `Cancelled`.
6. If a comment records the outcome of the discussion, show it first, then post it with `uv run --project /Users/mab/dev/mabstruct/knowstruct ks comment REF --text "..."` (or `--file FILE`).

## Move 4: run

For an approved `Todo` issue. First `uv run --project /Users/mab/dev/mabstruct/knowstruct ks show REF`, confirm with the user that it is approved and what will run, and which kind it is.

### run: analysis

1. From the ticket body take the approach name (`{approach}`), the folders (`{folders}`) and the token budget (`{cap}`; if none is on the ticket, 400k tokens and say so). `{ticket}` is the ticket body.
2. Read `prompts/analysis-agent.md` and fill its four placeholders `{approach}`, `{folders}`, `{cap}`, `{ticket}`.
3. Set the state: `uv run --project /Users/mab/dev/mabstruct/knowstruct ks update REF --state "In Progress"`.
4. Dispatch a read-only agent with your Agent tool, model `opus`, the filled prompt as its prompt. Several analyses are dispatched in parallel, one agent per ticket, in one message. The agent writes `docs/analysis/<approach>.md` in `/Users/mab/dev/mabstruct/knowstruct` and returns a summary of at most 300 words with candidate requirements, one line each. The agent never writes to Plane and never reads `.env`.
5. Save the summary to a temp file. Show it to the user in chat.
6. After the user has seen it: `uv run --project /Users/mab/dev/mabstruct/knowstruct ks comment REF --file SUMMARYFILE`, then `uv run --project /Users/mab/dev/mabstruct/knowstruct ks update REF --state Review`.
7. Commit the analysis file in the knowstruct repo: `git -C /Users/mab/dev/mabstruct/knowstruct add docs/analysis/<approach>.md` and a commit with a message naming the ticket. Never `git add -A`.
8. If the agent ran out of cap, its summary says what was covered and skipped; post that as it is. Candidate requirements become `requirement` drafts only through the capture move.

### run: spike

1. The ticket must have a question, a time box and a domain (template `templates/spike.md`). If one is missing, ask the user and do not start.
2. Set `uv run --project /Users/mab/dev/mabstruct/knowstruct ks update REF --state "In Progress"`.
3. Work in the scratchpad or a throwaway branch, inside the time box from the ticket, with no plan and no TDD. One agent: model `opus` if the spike is research-shaped, `sonnet` if build-shaped. Its prompt carries the question, the time box, the domain, and the rules (never write to Plane, never read `.env`). Code quality does not matter; the code is deleted afterwards.
4. At the end of the time box, stop, even if unfinished; what was reached is the result. Write the result using the `## Result` and `## Proposal` headings of the template.
5. Show the result to the user. Then post it: `uv run --project /Users/mab/dev/mabstruct/knowstruct ks comment REF --file RESULTFILE`. If it ends in a proposal or an analysis finding, create it per capture (`templates/proposal.md`; a proposal needs at least two options, "do nothing" counts, and the recommendation is marked as the agent's), link it with `ks relate`, and delete the spike code.
6. `uv run --project /Users/mab/dev/mabstruct/knowstruct ks update REF --state Review`.

### run: iteration

Out of v1. Say so to the user: iteration runs (spec, plan, build, phase result) are not built until the first requirement is approved; they then become their own `KS` ticket. Do not start one. Iterations that touch CONSTRUCT or CLAWSTRUCT are outside v1 altogether. A phase result, when it exists, is a comment shaped by `templates/phase-result.md`.

## The user's decision: `chosen:` / `rejected:`

The user decides in Plane: a state change plus a comment whose first line is `chosen: <option letter>` or `rejected: <reason>`. `uv run --project /Users/mab/dev/mabstruct/knowstruct ks decision REF` shows the latest comment regardless. If you cannot tell what was decided, ask the user. A `rejected:` with no reason is a question back to the user in the next session. Never decide for the user.

## Skills per stage

The session that runs this skill invokes the process skills; subagents follow only what their prompt says, so anything an agent must obey is written into its prompt.

- idea to requirement: `brainstorming`, conversation part only; the requirement ticket is the written design.
- analysis: none; read-only agents with `prompts/analysis-agent.md`; `dispatching-parallel-agents` for several at once.
- proposal: none; the agent writes options and marks its recommendation.
- spike: none by design; no TDD, no plan, time box and domain in the prompt.
- iteration (v1: not run): `brainstorming`, `writing-plans`, `subagent-driven-development`, `verification-before-completion`, `finishing-a-development-branch`, then the phase result.
- bug found anywhere: `systematic-debugging`.
- walk through: none; conversation, then write-back.
