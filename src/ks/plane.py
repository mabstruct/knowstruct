import re
from dataclasses import dataclass

from ks.convert import html_to_md, md_to_html
from ks.http import Http, PlaneError
from ks.refs import parse_ref


@dataclass(frozen=True)
class Project:
    identifier: str
    name: str
    id: str


@dataclass(frozen=True)
class Named:
    id: str
    name: str


@dataclass(frozen=True)
class Issue:
    ref: str
    id: str
    project: str
    title: str
    state: str
    labels: tuple[str, ...]
    priority: str
    body_md: str
    parent_ref: str | None
    created_at: str
    updated_at: str


_REF_IN_TEXT = re.compile(r"\b[A-Za-z][A-Za-z0-9]*-\d+\b")
FORBIDDEN_STATES = ("done", "cancelled")


class Refused(Exception):
    pass


@dataclass(frozen=True)
class Comment:
    id: str
    actor: str
    created_at: str
    text_md: str


def decision(comments: list[Comment]) -> tuple[str, str] | None:
    for c in reversed(comments):
        first = c.text_md.split("\n", 1)[0]
        for word in ("chosen", "rejected"):
            if first.lower().startswith(f"{word}:"):
                return word, first[len(word) + 1:].strip()
    return None


def _paged(http: Http, path: str) -> list[dict]:
    out: list[dict] = []
    url = f"{path}?per_page=100"
    while True:
        status, data = http.request("GET", url)
        if isinstance(data, list):
            return out + data
        out.extend(data["results"])
        if not data.get("next_page_results"):
            return out
        url = f"{path}?per_page=100&cursor={data['next_cursor']}"


class Plane:
    def __init__(self, http: Http, workspace: str = "mabstruct"):
        self.http = http
        self.W = f"/workspaces/{workspace}"
        self._projects: list[Project] | None = None
        self._states: dict[str, list[Named]] = {}
        self._labels: dict[str, list[Named]] = {}

    def me(self) -> str:
        _, data = self.http.request("GET", "/users/me/")
        return data["display_name"]

    def projects(self) -> list[Project]:
        if self._projects is None:
            rows = _paged(self.http, f"{self.W}/projects/")
            self._projects = [Project(r["identifier"], r["name"], r["id"]) for r in rows]
        return self._projects

    def project(self, identifier: str) -> Project:
        for p in self.projects():
            if p.identifier.lower() == identifier.lower():
                return p
        raise KeyError(f"unknown project {identifier}")

    def _named(self, cache: dict[str, list[Named]], project: Project, kind: str) -> list[Named]:
        if project.id not in cache:
            rows = _paged(self.http, f"{self.W}/projects/{project.id}/{kind}/")
            cache[project.id] = [Named(r["id"], r["name"]) for r in rows]
        return cache[project.id]

    def states(self, project: Project) -> list[Named]:
        return self._named(self._states, project, "states")

    def labels(self, project: Project) -> list[Named]:
        return self._named(self._labels, project, "labels")

    def _send(self, method: str, path: str, body: dict | None = None) -> dict:
        status, data = self.http.request(method, path, body)
        if status >= 400:
            raise PlaneError(status, path, str(data))
        return data

    def _get(self, path: str) -> dict:
        return self._send("GET", path)

    def get_issue(self, ref: str) -> Issue:
        ident, n = parse_ref(ref)
        project = self.project(ident)
        return self._to_issue(project, self._get(f"{self.W}/issues/{project.identifier}-{n}/"))

    def list_issues(self, project: str, state: str | None = None, label: str | None = None) -> list[Issue]:
        proj = self.project(project)
        rows = _paged(self.http, f"{self.W}/projects/{proj.id}/issues/")
        refs = {r["id"]: f"{proj.identifier}-{r['sequence_id']}" for r in rows}
        issues = [self._to_issue(proj, r, refs) for r in rows]
        if state is not None:
            issues = [i for i in issues if i.state.lower() == state.lower()]
        if label is not None:
            issues = [i for i in issues if label.lower() in (name.lower() for name in i.labels)]
        return issues

    def _to_issue(self, project: Project, raw: dict, page_refs: dict[str, str] | None = None) -> Issue:
        states = {s.id: s.name for s in self.states(project)}
        labels = {lb.id: lb.name for lb in self.labels(project)}
        return Issue(
            ref=f"{project.identifier}-{raw['sequence_id']}",
            id=raw["id"],
            project=project.identifier,
            title=raw["name"],
            state=states.get(raw["state"], raw["state"]),
            labels=tuple(labels.get(i, i) for i in raw.get("labels") or []),
            priority=raw.get("priority") or "",
            body_md=html_to_md(raw.get("description_html")),
            parent_ref=self._parent_ref(project, raw.get("parent"), page_refs or {}),
            created_at=raw.get("created_at") or "",
            updated_at=raw.get("updated_at") or "",
        )

    def _parent_ref(self, project: Project, parent_id: str | None, page_refs: dict[str, str]) -> str | None:
        if not parent_id:
            return None
        if parent_id in page_refs:
            return page_refs[parent_id]
        try:
            parent = self._get(f"{self.W}/projects/{project.id}/issues/{parent_id}/")
        except PlaneError:
            return None
        return f"{project.identifier}-{parent['sequence_id']}"

    @staticmethod
    def _resolve(items: list[Named], name: str, kind: str) -> str:
        for item in items:
            if item.name.lower() == name.strip().lower():
                return item.id
        raise KeyError(f"unknown {kind} {name!r}")

    @staticmethod
    def _check_state(state: str) -> None:
        if state.strip().lower() in FORBIDDEN_STATES:
            raise Refused(f"state {state!r} is set by the user in Plane, not by the agent")

    def create_issue(
        self, project: str, title: str, body_md: str, label: str, *,
        state: str = "Backlog", priority: str = "none", parent: str | None = None,
        relates: tuple[str, ...] = (),
    ) -> Issue:
        proj = self.project(project)
        self._check_state(state)
        state_id = self._resolve(self.states(proj), state, "state")
        label_id = self._resolve(self.labels(proj), label, "label")
        parent_id = None
        if parent is not None:
            if parse_ref(parent)[0] != proj.identifier.upper():
                raise ValueError(f"parent {parent} is not in project {proj.identifier}")
            parent_id = self.get_issue(parent).id
        rel = [f"{a}-{n}" for a, n in (parse_ref(o) for o in relates)]
        body = {
            "name": title, "description_html": md_to_html(body_md), "state": state_id,
            "labels": [label_id], "priority": priority, "parent": parent_id,
        }
        created = self._send("POST", f"{self.W}/projects/{proj.id}/issues/", body)
        ref = f"{proj.identifier}-{created['sequence_id']}"
        for other in rel:
            self.relate(ref, other)
        return self.get_issue(ref)

    def update_issue(
        self, ref: str, *, state: str | None = None, body_md: str | None = None,
        title: str | None = None, priority: str | None = None,
    ) -> Issue:
        if state is not None:
            self._check_state(state)
        issue = self.get_issue(ref)
        proj = self.project(issue.project)
        body: dict = {}
        if state is not None:
            body["state"] = self._resolve(self.states(proj), state, "state")
        if body_md is not None:
            body["description_html"] = md_to_html(body_md)
        if title is not None:
            body["name"] = title
        if priority is not None:
            body["priority"] = priority
        self._send("PATCH", f"{self.W}/projects/{proj.id}/issues/{issue.id}/", body)
        return self.get_issue(ref)

    def _comments_path(self, ref: str) -> str:
        issue = self.get_issue(ref)
        return f"{self.W}/projects/{self.project(issue.project).id}/issues/{issue.id}/comments/"

    @staticmethod
    def _to_comment(raw: dict) -> Comment:
        actor = raw.get("actor")
        if isinstance(actor, dict):
            actor = actor.get("display_name")
        return Comment(raw["id"], str(actor or ""), raw.get("created_at") or "", html_to_md(raw.get("comment_html")))

    def comment(self, ref: str, text_md: str) -> Comment:
        raw = self._send("POST", self._comments_path(ref), {"comment_html": md_to_html(text_md)})
        return self._to_comment(raw)

    def comments(self, ref: str) -> list[Comment]:
        rows = _paged(self.http, self._comments_path(ref))
        return sorted((self._to_comment(r) for r in rows), key=lambda c: c.created_at)

    def relate(self, ref: str, other: str) -> Comment:
        a, n = parse_ref(ref)
        b, m = parse_ref(other)
        return self.comment(f"{a}-{n}", f"relates to: {b}-{m}")

    def related(self, ref: str) -> list[str]:
        out: list[str] = []
        for c in self.comments(ref):
            first = c.text_md.split("\n", 1)[0]
            if not first.lower().startswith("relates to:"):
                continue
            for m in _REF_IN_TEXT.finditer(first.split(":", 1)[1]):
                ident, n = parse_ref(m.group())
                r = f"{ident}-{n}"
                if r not in out:
                    out.append(r)
        return out
