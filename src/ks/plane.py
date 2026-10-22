from dataclasses import dataclass

from ks.convert import html_to_md
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

    def _get(self, path: str) -> dict:
        status, data = self.http.request("GET", path)
        if status >= 400:
            raise PlaneError(status, path, str(data))
        return data

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
