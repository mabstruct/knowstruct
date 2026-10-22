from dataclasses import dataclass

from ks.http import Http


@dataclass(frozen=True)
class Project:
    identifier: str
    name: str
    id: str


@dataclass(frozen=True)
class Named:
    id: str
    name: str


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
