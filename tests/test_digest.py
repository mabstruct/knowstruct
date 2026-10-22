from fake_http import FakeHttp

from ks.digest import age, digest
from ks.plane import Plane

W = "/workspaces/mabstruct"
P = W + "/projects/"

EXPECTED = """### waiting on you (Review)
KS-3          requirement The knowledge system  (Review 2d)
ZENSTRUCT-2   analysis    ZEN  (Review 1d)  → rejected: too narrow

### approved, nobody on it (Todo)
CONSTRUCT-2   analysis    CONSTRUCT  (Todo 0d)

### open tasks
KS-5          task        revoke the old token  (Backlog 0d)  [high]
"""


def page(results):
    return {"results": results, "next_page_results": False, "next_cursor": None}


def raw(pid, n, name, state, label, day, priority="none"):
    return {
        "id": f"{pid}-{n}", "sequence_id": n, "name": name, "description_html": "", "priority": priority,
        "state": state, "labels": [label], "parent": None,
        "created_at": f"2026-10-{day}T10:00:00Z", "updated_at": f"2026-10-{day}T10:00:00Z",
    }


def build(issues_by_project):
    routes = {("GET", P + "?per_page=100"): page(
        [{"identifier": i, "name": i, "id": i.lower()} for i in issues_by_project])}
    for ident, issues in issues_by_project.items():
        pid = ident.lower()
        routes[("GET", P + f"{pid}/states/?per_page=100")] = page(
            [{"id": s, "name": s} for s in ("Backlog", "Todo", "In Progress", "Review", "Done")])
        routes[("GET", P + f"{pid}/labels/?per_page=100")] = page(
            [{"id": k, "name": k} for k in ("analysis", "requirement", "task")])
        routes[("GET", P + f"{pid}/issues/?per_page=100")] = page(issues)
    return routes


def test_digest_layout():
    routes = build({
        "ZENSTRUCT": [raw("zenstruct", 2, "ZEN", "Review", "analysis", "21")],
        "CONSTRUCT": [raw("construct", 2, "CONSTRUCT", "Todo", "analysis", "22")],
        "KS": [
            raw("ks", 3, "The knowledge system", "Review", "requirement", "20"),
            raw("ks", 5, "revoke the old token", "Backlog", "task", "22", "high"),
            raw("ks", 6, "finished", "Done", "task", "22"),
        ],
    })
    routes[("GET", W + "/issues/ZENSTRUCT-2/")] = raw("zenstruct", 2, "ZEN", "Review", "analysis", "21")
    routes[("GET", W + "/issues/KS-3/")] = raw("ks", 3, "The knowledge system", "Review", "requirement", "20")
    routes[("GET", P + "zenstruct/issues/zenstruct-2/comments/?per_page=100")] = page([
        {"id": "c1", "actor": "u", "created_at": "2026-10-21T00:00:00Z", "comment_html": "<p>rejected: too narrow</p>"}])
    routes[("GET", P + "ks/issues/ks-3/comments/?per_page=100")] = page([])
    assert digest(Plane(FakeHttp(routes)), "2026-10-22") == EXPECTED


def test_digest_empty_sections_omitted():
    routes = build({"KS": [raw("ks", 1, "x", "Done", "task", "22")]})
    assert digest(Plane(FakeHttp(routes)), "2026-10-22") == "nothing waiting\n"


def test_age():
    assert age("2026-10-19T10:00:00Z", "2026-10-22") == "3d"
