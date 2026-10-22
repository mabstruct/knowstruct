# KNOWSTRUCT v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new repo `~/dev/mabstruct/knowstruct/` with a deterministic Plane client (`dev`), a user-level `/dev` skill with four moves, and the first content seeded into Plane.

**Architecture:** `dev` is a small `uv` Python package: an injectable HTTP layer (`urllib` in production, a fake in tests), a `Plane` facade that speaks Plane's v1 REST in terms of issue references like `KS-12`, markdown↔HTML conversion at the boundary, a digest formatter, and a CLI the skill calls. The skill is markdown in `knowstruct/skill/dev/`, symlinked into `~/.claude/skills/dev/`. No model calls anywhere in the package.

**Tech Stack:** Python 3.12, `uv`, `pytest`, stdlib `urllib`, `markdown` (md→HTML), `markdownify` (HTML→md).

**Spec:** docs/superpowers/specs/2026-10-22-requirement-system-design.md

## Global Constraints

- New repo at `/Users/mab/dev/mabstruct/knowstruct/`, its own git history, branch `main`. Nothing from this plan lands in `zen/` except Task 10's removal of the spec and plan.
- Package name `devsys`, layout `src/devsys/`, tests in `tests/`, run with `cd /Users/mab/dev/mabstruct/knowstruct && uv run pytest -q`. Python `>=3.12`.
- Secrets: `knowstruct/.env` holds `PLANE_BASE_URL` and `PLANE_API_KEY` (the `ks-agent` token). **The user creates it by moving `zen/.env`; agents never read, move, print or quote it.** A global hook blocks any Bash command naming `.env`. `.gitignore` lists `.env`; `.env.example` is committed with placeholder values. No test reads `.env`; tests inject a fake HTTP layer. Error messages and logs never contain the token.
- Plane: base `PLANE_BASE_URL` + `/api/v1`; header `x-api-key`. `Http` paths are relative to `/api/v1`; `Plane` prefixes workspace paths with `W = "/workspaces/mabstruct"` (`/users/me/` is the one path outside it). Paths verified on this instance, relative to `W`: `GET /projects/`, `GET /projects/{pid}/states/`, `/labels/`, `GET|POST /projects/{pid}/issues/`, `GET|PATCH /projects/{pid}/issues/{id}/`, `GET /issues/{IDENT-N}/` (workspace-level retrieve by identifier), `GET|POST /projects/{pid}/issues/{id}/comments/`. Pagination: `?per_page=100&cursor=…`, response keys `results`, `next_cursor`, `next_page_results`. **Relations endpoint is 404 on this instance**: cross-project links are comments of the form `relates to: KS-12`.
- Bodies are HTML in Plane (`description_html`, `comment_html`). The client converts markdown→HTML on write and HTML→markdown on read.
- The client refuses to set state `Done` or `Cancelled` (any letter case). Only the user does that, in Plane.
- Issue kind = exactly one of the labels `idea`, `analysis`, `requirement`, `proposal`, `spike`, `iteration`, `task`. States per project: `Backlog`, `Todo`, `In Progress`, `Review`, `Done`, `Cancelled`.
- Project ids (fixed, verified): `CLAWSTRUCT` e71e5a56-933a-4faa-b172-0ac54cd6edb1, `CONSTRUCT` 14cebd9a-e2cf-440f-bd0f-e5dfa13dde50, `ZENSTRUCT` b01cdfe1-be8b-40a4-b51a-cd9e1823ad60, `KS` 49003bf0-4c54-4104-8f00-394aaff97a20. The client still discovers them from `/projects/` so a rename does not break it.
- Timestamps as ISO 8601 strings; no datetime objects cross module boundaries.
- Commit footer: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. One commit per task, files named in the task, never `git add -A`.

## Review Focus

1. A 401/403 from Plane: the raised error names the status and path, never the key → test in Task 2.
2. A body the user edited in Plane's rich editor (`<p>`, `<strong>`, `<ul>`, `<h2>`) comes back as readable markdown with the `## Why` headings intact; `update_issue` with `body_md=None` sends no `description_html` at all → tests in Task 4 and Task 5.
3. `update_issue(state="done")` and `"CANCELLED"` are refused, not just the exact-case names → test in Task 5.
4. A project with more than 100 issues: `list_issues` follows `next_cursor` until `next_page_results` is false → test in Task 3.
5. References typed by a human: `ks-12`, `KS 12`, `KS-12 ` resolve; `NOPE-1` raises an error naming the unknown project → test in Task 3.

---

### Task 1: Repo scaffold and configuration

**Files:**
- Create: `knowstruct/pyproject.toml`, `knowstruct/.gitignore`, `knowstruct/.env.example`, `knowstruct/README.md`, `knowstruct/src/devsys/__init__.py`, `knowstruct/src/devsys/config.py`
- Test: `knowstruct/tests/test_config.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) Env: base_url: str; api_key: str` — `base_url` has no trailing slash.
  - `REPO_ROOT: Path` — the directory containing `pyproject.toml` (`Path(__file__).resolve().parents[2]`).
  - `load_env(path: Path | None = None) -> Env` — reads `path` or `REPO_ROOT / ".env"`; `KEY=value` lines, `#` comments and blank lines ignored, surrounding single or double quotes stripped; raises `ConfigError(f"missing {name} in {path}")` naming the variable, never its value; raises `ConfigError` if the file is absent.
  - `class ConfigError(Exception)`.

- [ ] **Step 1: Create the repo and project files**

`git init` in `/Users/mab/dev/mabstruct/knowstruct`, branch `main`. `pyproject.toml`: name `devsys`, version `0.1.0`, `requires-python = ">=3.12"`, dependencies `markdown>=3.6`, `markdownify>=0.13`; dev dependency `pytest>=8`; `[project.scripts] dev = "devsys.cli:main"`; build backend `hatchling`, `[tool.hatch.build.targets.wheel] packages = ["src/devsys"]`. `.gitignore`: `.env`, `.env.*`, `!.env.example`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.egg-info/`. `.env.example`: `PLANE_BASE_URL=https://plane.example.com` and `PLANE_API_KEY=replace-me`. `README.md`: three lines — what `dev` is, `uv run pytest -q`, `uv run dev --help`.

- [ ] **Step 2: Write the failing tests**

```python
def test_load_env_reads_file(tmp_path):
    f = tmp_path / ".env"
    f.write_text('# c\nPLANE_BASE_URL="https://p.example/"\nPLANE_API_KEY=abc\n')
    env = load_env(f)
    assert env == Env(base_url="https://p.example", api_key="abc")

def test_load_env_missing_key_names_variable_not_value(tmp_path):
    f = tmp_path / ".env"; f.write_text("PLANE_BASE_URL=https://p.example\n")
    with pytest.raises(ConfigError, match="PLANE_API_KEY"): load_env(f)

def test_load_env_missing_file(tmp_path):
    with pytest.raises(ConfigError): load_env(tmp_path / ".env")
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /Users/mab/dev/mabstruct/knowstruct && uv run pytest tests/test_config.py -q`
Expected: FAIL with `ImportError` / `ModuleNotFoundError: devsys.config`

- [ ] **Step 4: Implement `config.py`**

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_config.py -q` — Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore .env.example README.md src/devsys/__init__.py src/devsys/config.py tests/test_config.py uv.lock
git commit -m "feat: scaffold devsys package with env loading"
```

---

### Task 2: HTTP layer and Plane projects, states, labels

**Files:**
- Create: `knowstruct/src/devsys/http.py`, `knowstruct/src/devsys/plane.py`, `knowstruct/tests/fake_http.py`
- Test: `knowstruct/tests/test_http.py`, `knowstruct/tests/test_plane_meta.py`

**Interfaces:**
- Consumes: `config.Env`.
- Produces:
  - `class Http(Protocol): def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, Any]` — `path` is relative to `/api/v1` (`/workspaces/mabstruct/projects/…`, `/users/me/`); returns status and decoded JSON (`None` for an empty body).
  - `class PlaneError(Exception)` with attributes `status: int`, `path: str`; message `f"{status} on {path}"` plus the first 200 chars of the response body. Never the key.
  - `UrlHttp(env: Env)` implementing `Http` with `urllib` against `env.base_url + "/api/v1" + path`, header `x-api-key`, `Content-Type: application/json`, timeout 30 s; raises `PlaneError` for status ≥ 400.
  - `tests/fake_http.py`: `FakeHttp(routes: dict[tuple[str, str], Any | list[Any]])` — key `(method, path)`; a list is served one element per call (for pagination); records `calls: list[tuple[str, str, dict | None]]`; unknown route → `(404, {"error": "Page not found."})`. A value that is a `tuple[int, Any]` is returned as that status.
  - `@dataclass(frozen=True) Project: identifier: str; name: str; id: str`
  - `@dataclass(frozen=True) Named: id: str; name: str` (for states and labels)
  - `Plane(http: Http, workspace: str = "mabstruct")` with `W = f"/workspaces/{workspace}"` prefixed to every workspace path, `me() -> str` (`GET /users/me/` → `display_name`), `projects() -> list[Project]`, `project(identifier: str) -> Project` (case-insensitive; raises `KeyError(f"unknown project {identifier}")`), `states(project: Project) -> list[Named]`, `labels(project: Project) -> list[Named]`; all three cached per instance after first fetch.
  - `_paged(http, path) -> list[dict]` — follows `next_cursor` while `next_page_results` is true, `per_page=100`.

- [ ] **Step 1: Write the failing tests**

```python
def test_urlhttp_error_hides_key(monkeypatch):
    # monkeypatch urllib.request.urlopen to raise HTTPError(401, body=b'{"detail":"bad"}')
    http = UrlHttp(Env("https://p.example", "SECRET-KEY"))
    with pytest.raises(PlaneError) as e: http.request("GET", "/users/me/")
    assert e.value.status == 401 and "/users/me/" in str(e.value) and "SECRET-KEY" not in str(e.value)

def test_urlhttp_sends_header_and_json(monkeypatch):
    # capture the Request object; assert headers["X-api-key"] == "k", data == b'{"a": 1}', full URL == "https://p.example/api/v1/workspaces/mabstruct/projects/"
    ...

def test_project_lookup_case_insensitive():
    fake = FakeHttp({("GET", "/workspaces/mabstruct/projects/?per_page=100"): {"results": [{"identifier": "KS", "name": "KNOWSTRUCT", "id": "p1"}], "next_page_results": False, "next_cursor": None}})
    plane = Plane(fake)
    assert plane.project("ks") == Project("KS", "KNOWSTRUCT", "p1")
    with pytest.raises(KeyError, match="NOPE"): plane.project("NOPE")
    plane.projects(); assert len(fake.calls) == 1  # cached

def test_states_and_labels():
    # routes for /workspaces/mabstruct/projects/p1/states/?per_page=100 and …/labels/?per_page=100 → Named lists in response order
    ...
```

- [ ] **Step 2: Run tests to verify they fail** — `uv run pytest tests/test_http.py tests/test_plane_meta.py -q` — Expected: FAIL, modules missing

- [ ] **Step 3: Implement `http.py`, `plane.py` (projects/states/labels/_paged only), `tests/fake_http.py`**

- [ ] **Step 4: Run tests to verify they pass** — Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/devsys/http.py src/devsys/plane.py tests/fake_http.py tests/test_http.py tests/test_plane_meta.py
git commit -m "feat: http layer with key-safe errors; plane projects, states, labels"
```

---

### Task 3: Issue references and reading issues

**Files:**
- Modify: `knowstruct/src/devsys/plane.py`
- Create: `knowstruct/src/devsys/refs.py`
- Test: `knowstruct/tests/test_refs.py`, `knowstruct/tests/test_plane_read.py`

**Interfaces:**
- Consumes: Task 2 (`Plane`, `Project`, `Named`, `_paged`, `FakeHttp`).
- Produces:
  - `parse_ref(s: str) -> tuple[str, int]` — accepts `KS-12`, `ks-12`, `KS 12`, with surrounding whitespace; returns `("KS", 12)`; raises `ValueError(f"not an issue reference: {s!r}")`.
  - `@dataclass(frozen=True) Issue: ref: str; id: str; project: str; title: str; state: str; labels: tuple[str, ...]; priority: str; body_md: str; parent_ref: str | None; created_at: str; updated_at: str` — `ref` is `IDENT-N` upper case; `state` and `labels` are names, resolved through `Plane.states`/`labels`; `body_md` from `description_html` via Task 4's `html_to_md` (until Task 4 exists, `body_md` is the raw HTML; Task 4 switches it).
  - `Plane.get_issue(ref: str) -> Issue` — `GET /issues/{IDENT-N}/`; unknown project → `KeyError` from `project()` before any request; 404 → `PlaneError`.
  - `Plane.list_issues(project: str, state: str | None = None, label: str | None = None) -> list[Issue]` — `GET /projects/{pid}/issues/` paged; filters by state name and label name client-side, case-insensitive; order as returned.
  - `Plane._to_issue(project: Project, raw: dict) -> Issue` — `parent_ref` resolved only when `raw["parent"]` is an id of an issue in the same page or fetched by id (`GET /projects/{pid}/issues/{id}/`); else `None`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("s", ["KS-12", "ks-12", "KS 12", " KS-12 "])
def test_parse_ref_variants(s): assert parse_ref(s) == ("KS", 12)

def test_parse_ref_rejects(): 
    with pytest.raises(ValueError): parse_ref("twelve")

def test_get_issue_resolves_names():
    # routes: projects (KS→p1), states (s1→Review), labels (l1→requirement), GET /workspaces/mabstruct/issues/KS-3/ → raw with state "s1", labels ["l1"], sequence_id 3, name, description_html "<p>x</p>", priority "high", parent None
    issue = Plane(fake).get_issue("ks-3")
    assert (issue.ref, issue.state, issue.labels, issue.priority) == ("KS-3", "Review", ("requirement",), "high")

def test_get_issue_unknown_project_makes_no_request():
    with pytest.raises(KeyError): plane.get_issue("NOPE-1")
    assert all(not p.endswith("/issues/NOPE-1/") for _, p, _ in fake.calls)

def test_list_issues_pages_and_filters():
    # two pages: first {"results":[...], "next_cursor":"100:1:0", "next_page_results":True}, second with False; 101 raw issues, 2 in state Review; label filter "task"
    out = plane.list_issues("KS", state="review")
    assert len(out) == 2 and len([c for c in fake.calls if "/issues/?" in c[1]]) == 2
```

- [ ] **Step 2: Run tests to verify they fail** — Expected: FAIL, `refs` missing / `get_issue` missing

- [ ] **Step 3: Implement `refs.py` and the read side of `plane.py`**

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest -q` — Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/devsys/refs.py src/devsys/plane.py tests/test_refs.py tests/test_plane_read.py
git commit -m "feat: issue references, get_issue and paged list_issues"
```

---

### Task 4: Markdown ↔ HTML conversion

**Files:**
- Create: `knowstruct/src/devsys/convert.py`
- Modify: `knowstruct/src/devsys/plane.py` (`_to_issue` uses `html_to_md`)
- Test: `knowstruct/tests/test_convert.py`

**Interfaces:**
- Produces:
  - `md_to_html(md: str) -> str` — `markdown.markdown(md, extensions=["fenced_code", "tables"])`; empty input → `"<p></p>"` (Plane's own empty body).
  - `html_to_md(html: str) -> str` — `markdownify` with `heading_style="ATX"`, bullets `-`; collapses runs of three or more newlines to two; strips leading/trailing whitespace; `None` or `""` or `"<p></p>"` → `""`.

- [ ] **Step 1: Write the failing tests**

```python
SKELETON = "## Why\n\nthe need\n\n## Evidence\n\n- one\n- two\n\n## Judged by\n\n**cosmology**: a test\n"

def test_round_trip_keeps_skeleton():
    md = html_to_md(md_to_html(SKELETON))
    assert md.splitlines()[0] == "## Why" and "- one" in md and "**cosmology**" in md and "## Judged by" in md

def test_plane_editor_html_reads_as_markdown():
    html = '<h2>Why</h2><p>the <strong>need</strong></p><ul><li><p>one</p></li></ul>'
    assert html_to_md(html) == "## Why\n\nthe **need**\n\n- one"

def test_empty(): assert html_to_md("<p></p>") == "" and md_to_html("") == "<p></p>"
```

- [ ] **Step 2: Run tests to verify they fail** — Expected: FAIL, module missing

- [ ] **Step 3: Implement `convert.py`; switch `_to_issue` to `body_md=html_to_md(raw.get("description_html"))`**

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest -q` — Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/devsys/convert.py src/devsys/plane.py tests/test_convert.py
git commit -m "feat: markdown/html conversion at the Plane boundary"
```

---

### Task 5: Writing issues, comments, relations, decisions

**Files:**
- Modify: `knowstruct/src/devsys/plane.py`
- Test: `knowstruct/tests/test_plane_write.py`

**Interfaces:**
- Consumes: Tasks 2–4.
- Produces:
  - `class Refused(Exception)` — message `f"state {name!r} is set by the user in Plane, not by the agent"`.
  - `FORBIDDEN_STATES = ("done", "cancelled")` (compared lower-cased, stripped).
  - `Plane.create_issue(project: str, title: str, body_md: str, label: str, *, state: str = "Backlog", priority: str = "none", parent: str | None = None, relates: tuple[str, ...] = ()) -> Issue` — `POST /projects/{pid}/issues/` with `name`, `description_html`, `state` (id), `labels` ([id]), `priority`, `parent` (id via `get_issue(parent)` when given, same project only, else `ValueError`); unknown label or state name → `KeyError` before any POST; then one `relate()` per entry of `relates`; returns `get_issue(ref)` of the new issue.
  - `Plane.update_issue(ref: str, *, state: str | None = None, body_md: str | None = None, title: str | None = None, priority: str | None = None) -> Issue` — `PATCH /projects/{pid}/issues/{id}/` with only the given fields; `state` in `FORBIDDEN_STATES` → `Refused` before any request.
  - `@dataclass(frozen=True) Comment: id: str; actor: str; created_at: str; text_md: str`
  - `Plane.comment(ref: str, text_md: str) -> Comment` — `POST …/comments/` with `comment_html`.
  - `Plane.comments(ref: str) -> list[Comment]` — paged `GET …/comments/`, oldest first (sort by `created_at`); `actor` is `display_name` when the response nests an actor dict, else the raw id string.
  - `Plane.relate(ref: str, other: str) -> Comment` — validates both refs with `parse_ref`, posts the comment `relates to: {OTHER}`.
  - `Plane.related(ref: str) -> list[str]` — refs parsed from comments whose first line starts with `relates to:` (comma-separated allowed), in order, deduplicated.
  - `decision(comments: list[Comment]) -> tuple[str, str] | None` — scans newest first; first line of a comment lower-cased starting `chosen:` → `("chosen", rest.strip())`; `rejected:` → `("rejected", rest.strip())`; else `None`. Pure function in `plane.py`.

- [ ] **Step 1: Write the failing tests**

```python
def test_create_issue_posts_ids_and_html():
    issue = plane.create_issue("KS", "T", "## Why\n\nx", "requirement", state="Review", priority="high")
    m, p, body = [c for c in fake.calls if c[0] == "POST"][0]
    assert p == "/workspaces/mabstruct/projects/p1/issues/" and body["state"] == "s_review" and body["labels"] == ["l_req"] and body["description_html"].startswith("<h2>Why</h2>")
    assert issue.ref == "KS-7"

def test_create_issue_unknown_label_makes_no_post():
    with pytest.raises(KeyError): plane.create_issue("KS", "T", "", "nope")
    assert not [c for c in fake.calls if c[0] == "POST"]

def test_create_issue_with_relates_posts_comment():
    plane.create_issue("KS", "T", "", "idea", relates=("ZENSTRUCT-3",))
    assert any(c[2] and c[2].get("comment_html") == "<p>relates to: ZENSTRUCT-3</p>" for c in fake.calls)

@pytest.mark.parametrize("s", ["Done", "done", "CANCELLED", " cancelled "])
def test_update_refuses_terminal_states(s):
    with pytest.raises(Refused): plane.update_issue("KS-7", state=s)
    assert not [c for c in fake.calls if c[0] == "PATCH"]

def test_update_without_body_sends_no_description():
    plane.update_issue("KS-7", state="Review")
    body = [c for c in fake.calls if c[0] == "PATCH"][0][2]
    assert "description_html" not in body and body == {"state": "s_review"}

def test_comments_oldest_first_and_decision():
    cs = plane.comments("KS-7")
    assert [c.text_md for c in cs] == ["first", "chosen: B\n\nbecause"]
    assert decision(cs) == ("chosen", "B")
    assert decision([Comment("1", "a", "t", "rejected: too wide")]) == ("rejected", "too wide")
    assert decision([Comment("1", "a", "t", "ok")]) is None

def test_related_parses_comments():
    # comments: "relates to: KS-1, zenstruct-3", "relates to: KS-1"
    assert plane.related("KS-7") == ["KS-1", "ZENSTRUCT-3"]
```

- [ ] **Step 2: Run tests to verify they fail** — Expected: FAIL, attributes missing

- [ ] **Step 3: Implement the write side of `plane.py`**

- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest -q` — Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/devsys/plane.py tests/test_plane_write.py
git commit -m "feat: create/update issues with refused terminal states, comments, relations, decisions"
```

---

### Task 6: Digest

**Files:**
- Create: `knowstruct/src/devsys/digest.py`
- Test: `knowstruct/tests/test_digest.py`

**Interfaces:**
- Consumes: `Plane.projects`, `Plane.list_issues`, `Plane.comments`, `decision`, `Issue`.
- Produces:
  - `digest(plane: Plane, today: str) -> str` — `today` is an ISO date (`2026-10-22`); layout below; exact text, trailing newline, sections omitted when empty, projects in the order `KS, CLAWSTRUCT, CONSTRUCT, ZENSTRUCT` then any others alphabetically.
  - `age(created_or_updated: str, today: str) -> str` — `"0d"`, `"3d"`, from the date part of the ISO timestamp.
  - `line(issue: Issue, today: str, decision: tuple[str, str] | None) -> str` — `f"{issue.ref:<14}{kind:<12}{issue.title}  ({issue.state} {age})"`, where `kind` is the first kind label in the fixed order or `-`; when `decision` is given, append `  → {decision[0]}: {decision[1]}`; for `task` kind append `  [{priority}]` when priority is not `none`.

Layout:

```
### waiting on you (Review)
KS-3          requirement The knowledge system  (Review 2d)
ZENSTRUCT-2   analysis    ZEN  (Review 1d)  → rejected: too narrow

### approved, nobody on it (Todo)
CONSTRUCT-2   analysis    CONSTRUCT  (Todo 0d)

### open tasks
KS-5          task        revoke the old token  (Backlog 0d)  [high]
```

Only `Review` issues get the decision lookup (one `comments()` call each); `Todo` and task lines do not.

- [ ] **Step 1: Write the failing tests**

```python
def test_digest_layout(): 
    # FakeHttp with KS and ZENSTRUCT, issues as in the layout above, comments on ZENSTRUCT-2 with "rejected: too narrow"
    assert digest(plane, "2026-10-22") == EXPECTED  # the layout block verbatim

def test_digest_empty_sections_omitted():
    assert digest(plane_with_nothing, "2026-10-22") == "nothing waiting\n"

def test_age(): assert age("2026-10-19T10:00:00Z", "2026-10-22") == "3d"
```

- [ ] **Step 2: Run tests to verify they fail** — Expected: FAIL, module missing
- [ ] **Step 3: Implement `digest.py`**
- [ ] **Step 4: Run tests to verify they pass** — Expected: all pass
- [ ] **Step 5: Commit**

```bash
git add src/devsys/digest.py tests/test_digest.py
git commit -m "feat: digest of review, todo and open tasks"
```

---

### Task 7: CLI

**Files:**
- Create: `knowstruct/src/devsys/cli.py`
- Test: `knowstruct/tests/test_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv: list[str] | None = None, plane: Plane | None = None) -> int` — `plane=None` builds `Plane(UrlHttp(load_env()))`; tests pass a `Plane(FakeHttp(...))`. Prints to stdout; errors (`PlaneError`, `Refused`, `KeyError`, `ValueError`, `ConfigError`) print `error: {message}` to stderr and return 2. Subcommands:
  - `dev whoami` — `plane.me()`.
  - `dev projects` — one line per project: `IDENT  name`.
  - `dev digest` — `digest(plane, today)`; `--today YYYY-MM-DD` for tests, default local date.
  - `dev show REF [--json]` — text: `REF  kind  title`, `state: … priority: … parent: … labels: …`, blank line, `body_md`, blank line, `### comments`, each `-- actor (created_at)` then text; `related: …` line when any. `--json`: `asdict(issue)` plus `comments` and `related`.
  - `dev list PROJECT [--state S] [--label L]` — `line()` per issue without decisions.
  - `dev create PROJECT --label L --title T (--body-file F | --body TEXT) [--state S] [--priority P] [--parent REF] [--relates REF ...]` — prints the new `REF`.
  - `dev update REF [--state S] [--body-file F] [--title T] [--priority P]` — prints `REF  state` after.
  - `dev comment REF (--file F | --text TEXT)` — prints the comment id.
  - `dev relate REF OTHER` — prints `REF relates to OTHER`.
  - `dev decision REF` — prints `chosen: B`, `rejected: …`, or `none`.
  Body files are read as UTF-8 markdown.

- [ ] **Step 1: Write the failing tests**

```python
def test_create_prints_ref(capsys, tmp_path):
    f = tmp_path / "b.md"; f.write_text("## Why\n\nx")
    assert main(["create", "KS", "--label", "requirement", "--title", "T", "--body-file", str(f), "--state", "Review"], plane=plane) == 0
    assert capsys.readouterr().out.strip() == "KS-7"

def test_update_done_is_error(capsys):
    assert main(["update", "KS-7", "--state", "Done"], plane=plane) == 2
    assert "error:" in capsys.readouterr().err

def test_show_json_has_body_and_comments(capsys): ...
def test_digest_passes_today(capsys): ...
def test_unknown_project_exit_2(capsys): assert main(["list", "NOPE"], plane=plane) == 2
```

- [ ] **Step 2: Run tests to verify they fail** — Expected: FAIL, module missing
- [ ] **Step 3: Implement `cli.py` with `argparse`**
- [ ] **Step 4: Run tests to verify they pass** — `uv run pytest -q`; also `uv run dev --help` prints the subcommands — Expected: all pass, help lists ten subcommands
- [ ] **Step 5: Commit**

```bash
git add src/devsys/cli.py tests/test_cli.py
git commit -m "feat: dev command line"
```

---

### Task 8: The `/dev` skill and its templates

**Files:**
- Create: `knowstruct/skill/dev/SKILL.md`, `knowstruct/skill/dev/templates/requirement.md`, `proposal.md`, `analysis.md`, `spike.md`, `task.md`, `phase-result.md`, `knowstruct/skill/dev/prompts/analysis-agent.md`
- Create: symlink `~/.claude/skills/dev` → `/Users/mab/dev/mabstruct/knowstruct/skill/dev`
- Test: `knowstruct/tests/test_skill.py`

**Interfaces:**
- Consumes: the CLI subcommands of Task 7 (the skill calls `uv run --project /Users/mab/dev/mabstruct/knowstruct dev …` and nothing else).
- Produces: a skill the session invokes; no Python.

- [ ] **Step 1: Write the failing test**

```python
SKILL = Path(__file__).parents[1] / "skill" / "dev" / "SKILL.md"

def test_skill_only_calls_existing_subcommands():
    used = set(re.findall(r"\bks (whoami|projects|digest|show|list|create|update|comment|relate|decision|\w+)\b", SKILL.read_text()))
    assert used <= {"whoami","projects","digest","show","list","create","update","comment","relate","decision"}

def test_templates_have_skeleton_headings():
    t = (SKILL.parent / "templates")
    assert (t / "requirement.md").read_text().startswith("## Why")
    assert {"## Requirement", "## Options", "## Recommendation (agent's)", "## What a spike would settle"} <= set(l.strip() for l in (t / "proposal.md").read_text().splitlines())
    for name in ("analysis", "spike", "task", "phase-result"): assert (t / f"{name}.md").exists()

def test_skill_never_sets_done():
    assert "--state Done" not in SKILL.read_text() and "--state Cancelled" not in SKILL.read_text()
```

- [ ] **Step 2: Run test to verify it fails** — Expected: FAIL, files missing

- [ ] **Step 3: Write `SKILL.md`**

Frontmatter `name: dev`, `description: Lead agent for the KNOWSTRUCT requirement system in Plane — digest, capture, walk through, run. Use for status, backlog, requirements, proposals, spikes, analyses, tasks.` Body, in this order: the one rule (agents never set Done/Cancelled; nothing is written to Plane the user has not seen in chat first; the token is never read or printed; all Plane access via `uv run --project /Users/mab/dev/mabstruct/knowstruct dev …`); the four moves from spec §4.4 each with the exact `dev` commands it runs and what it shows the user before writing; **capture** fills a template from `templates/` and shows it; **walk through** runs `dev show REF`, re-runs it before any `dev update --body-file`, and prints the full replacement body in chat first; **run** for `analysis` dispatches read-only agents with `prompts/analysis-agent.md` (model per spec §4.8: Opus), writes the long form to `docs/analysis/<approach>.md`, posts the summary with `dev comment` and sets `--state Review`; **run** for `spike` with the time box from the ticket; **run** for `iteration` is out of v1 and says so. End with the `chosen:`/`rejected:` convention and the skills-per-stage table from spec §4.7 condensed to one line per stage.

- [ ] **Step 4: Write the templates** from spec §4.3, each heading on its own line with a one-line italic hint under it; `analysis.md` has the six questions as `## ` headings plus `## Candidate requirements` and a `Budget:` line; `spike.md` has `Question`, `Time box`, `Domain`, `Result`, `Proposal`; `task.md` has `Owner` and `Done when`; `phase-result.md` has `Built`, `Verified how`, `Look at`, `Open`.

- [ ] **Step 5: Write `prompts/analysis-agent.md`** — the read-only analysis prompt: the approach name and folders (placeholders `{approach}`, `{folders}`), the reading rule from spec §4.6 (prompts, skills, workflow definitions, docs, configuration, produced outputs; no code bodies; skip `node_modules/`, `.venv/`, binaries, papers), the token cap placeholder `{cap}`, the six questions, the output: `docs/analysis/{approach}.md` long form and a ≤ 300-word summary with candidate requirements as one line each; "if the cap runs out, report what was covered and what was skipped".

- [ ] **Step 6: Create the symlink** — `ln -s /Users/mab/dev/mabstruct/knowstruct/skill/dev ~/.claude/skills/dev` (skip if it exists).

- [ ] **Step 7: Run tests to verify they pass** — `uv run pytest -q` — Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add skill/dev/SKILL.md skill/dev/templates skill/dev/prompts tests/test_skill.py
git commit -m "feat: /dev skill with four moves, ticket templates and analysis prompt"
```

---

### Task 9: Seed the first content (live, needs `knowstruct/.env`)

**Files:**
- Create: `knowstruct/docs/tickets/ks-requirement-knowledge-system.md`, `analysis-clawstruct.md`, `analysis-construct.md`, `analysis-zenstruct.md`, `analysis-what-got-lost.md`, `proposal-zen-ask-v2.md`, `task-revoke-old-token.md`, `task-smtp-decision.md`, `task-delete-book-ingest-branch.md`, `knowstruct/scripts/seed.sh`
- Test: `knowstruct/tests/test_seed.py` (static: the script only calls `dev create` and `dev relate`, every `--body-file` exists, every `--label` is a kind)

**Interfaces:**
- Consumes: the CLI. Live Plane; this task is the first real write and the first check that `ks-agent` can create issues.

- [ ] **Step 1: Write the ticket bodies**

`ks-requirement-knowledge-system.md` — exact text:

```
## Why
I add information sources; the system digests them and, while doing so, evaluates connections. Afterwards I can ask around the knowledge base and look at a landscape of a theme. Knowledge is held per knowledge entity — insights, connections, syntheses, entities, sources, references, persons, places, considerations — not per source. Physical AI was the initial motor; the target is any knowledge across my work and life.

Two ways in. Browse: the landscape is layered — a handful of themes at the top (cosmology → early universe, galaxies, formation, stars, general relativity, quantum gravity, string theory), the next level of detail only as I browse in, never hundreds of nodes at once. Ask: a question returns about five good suggestions; following one reaches the depth that topic needs, then links and wiki pages.

## Evidence
- CLAWSTRUCT: promising first results on physical AI; unmanageable as a system.
- CONSTRUCT: organised knowledge per source; the entity-level view never formed.
- ZENSTRUCT: has topic/entity/source/synthesis pages but still only re-finds snippets; no levels above the pages (agent's reading, to be checked by the analyses).
- zen-ui graph: everything on one canvas, unreadable — the counterexample for browse.

## Judged by
Domains where I can tell good from bad: physical AI, cosmology, math, general AI. A proposal shows itself on one of them. Browse test: open cosmology and see the themes above, not a hundred nodes. Ask test: a question on one of these domains yields five suggestions of which the first is one I would have chosen.

## Out of scope
Ingest mechanics, the wiki schema, any UI beyond what the tests above need.

## Source
Brainstorm 2026-10-21/22; design docs/superpowers/specs/2026-10-22-requirement-system-design.md §5.
```

The four analysis bodies: the `analysis.md` template filled with approach name, folders from spec §3 (CLAWSTRUCT: `mabstruct-workspace/`, context `evolving/`, `mabstruct_articles/`; CONSTRUCT: `construct/`, `construct-testws/`; ZENSTRUCT: `zen/`; what-got-lost: `mab-notes/`, `mabstruct-site/`, `physicalAI/` README and structure, `research/` listing only), `Budget: 400k tokens of reading, Opus 5.5` (what-got-lost: `session model`), questions left empty for the agent.

`proposal-zen-ask-v2.md`: `## Requirement` → `KS-<n>` (filled by the script from the created ref), `## Options` → `### A: zen-ask v2 as specified (docs/superpowers/specs/2026-10-18-zen-ask-v2-design.md on branch ask-v2)`, `### B: do nothing until the generalisation layer exists`, `## Recommendation (agent's)` → `B until the analyses are in; A covers the ask-half only`, `## What a spike would settle` → `whether the five-suggestion test passes on cosmology with the current wiki`.

Three task bodies: `Owner: user`, one-line `Done when`.

- [ ] **Step 2: Write `scripts/seed.sh`** — `set -euo pipefail`; `DEV="uv run --project $(dirname "$0")/.. dev"`; creates in order: the KS requirement (`--state Review --priority high`) capturing its ref; four analyses (`--state Todo`; the CONSTRUCT one with `--parent CONSTRUCT-1`; each with `--relates $REQ`); the proposal in ZENSTRUCT (`--state Backlog`, `--relates $REQ`, body with `KS-<n>` substituted via `sed`); the three tasks in KS (`--state Backlog`, priorities `high`, `low`, `low`). Prints every ref. Guard: refuses to run twice by checking `$DEV list KS --label requirement` for the title first.

- [ ] **Step 3: Write and run the static test** — Expected: PASS

- [ ] **Step 4: Run the seed** — `bash scripts/seed.sh` — Expected: nine refs printed; then `uv run dev digest` shows one line under *waiting on you*, four under *approved, nobody on it*, three under *open tasks*. If `.env` is absent the script fails with `error: missing … .env` and the task stops here: report it, do not work around it.

- [ ] **Step 5: Commit**

```bash
git add docs/tickets scripts/seed.sh tests/test_seed.py
git commit -m "feat: seed the first requirement, analyses, proposal and tasks"
```

---

### Task 10: Move the design and plan; README

**Files:**
- Create: `knowstruct/docs/superpowers/specs/2026-10-22-requirement-system-design.md`, `knowstruct/docs/superpowers/plans/2026-10-22-knowstruct-v1.md` (copies), `knowstruct/docs/analysis/.gitkeep`
- Modify: `knowstruct/README.md`
- Delete (in `zen/`): the same two files, one commit there.

- [ ] **Step 1: Copy both files into `knowstruct/docs/superpowers/…`; fix the spec's §4.5 sentence "moves there from `zen/docs/` when the repo exists" to "lives here"; set the plan's **Spec:** line to the new path.**
- [ ] **Step 2: README** — sections: what KNOWSTRUCT is (two sentences from spec §1), setup (`uv sync`; create `.env` from `.env.example` with the `ks-agent` token; the skill symlink), use (`uv run dev digest`, `dev show`, the four moves by name), test (`uv run pytest -q`), where the long-form analyses go.
- [ ] **Step 3: Run `uv run pytest -q`** — Expected: all pass (nothing changed in code)
- [ ] **Step 4: Commit in `knowstruct`** — `git add docs README.md && git commit -m "docs: design, plan and README"`
- [ ] **Step 5: In `zen/`, `git rm` the two files and commit** — `git commit -m "docs: requirement-system design and plan moved to knowstruct"`.
