import pytest
from fake_http import FakeHttp

from devsys.http import PlaneError
from devsys.plane import Plane

W = "/workspaces/mabstruct"
P = W + "/projects/"


def page(results, more=False, cursor=None):
    return {"results": results, "next_page_results": more, "next_cursor": cursor}


def raw_issue(n, state="s1", labels=("l1",), parent=None, **extra):
    return {
        "id": f"i{n}", "sequence_id": n, "name": f"issue {n}", "description_html": "<p>x</p>",
        "priority": "high", "state": state, "labels": list(labels), "parent": parent,
        "created_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-02T10:00:00Z", **extra,
    }


def meta_routes():
    return {
        ("GET", P + "?per_page=100"): page([{"identifier": "KS", "name": "KNOWSTRUCT", "id": "p1"}]),
        ("GET", P + "p1/states/?per_page=100"): page([{"id": "s1", "name": "Review"}, {"id": "s2", "name": "Todo"}]),
        ("GET", P + "p1/labels/?per_page=100"): page([{"id": "l1", "name": "requirement"}, {"id": "l2", "name": "task"}]),
    }


def test_get_issue_resolves_names():
    fake = FakeHttp({**meta_routes(), ("GET", W + "/issues/KS-3/"): raw_issue(3)})
    issue = Plane(fake).get_issue("ks-3")
    assert (issue.ref, issue.state, issue.labels, issue.priority) == ("KS-3", "Review", ("requirement",), "high")
    assert (issue.id, issue.project, issue.title, issue.body_md) == ("i3", "KS", "issue 3", "x")
    assert issue.parent_ref is None
    assert (issue.created_at, issue.updated_at) == ("2026-10-01T10:00:00Z", "2026-10-02T10:00:00Z")


def test_get_issue_unknown_project_makes_no_request():
    fake = FakeHttp(meta_routes())
    with pytest.raises(KeyError):
        Plane(fake).get_issue("NOPE-1")
    assert all(not p.endswith("/issues/NOPE-1/") for _, p, _ in fake.calls)


def test_get_issue_404_raises_plane_error():
    with pytest.raises(PlaneError):
        Plane(FakeHttp(meta_routes())).get_issue("KS-99")


def test_unmatched_ids_resolve_to_themselves():
    fake = FakeHttp({**meta_routes(), ("GET", W + "/issues/KS-4/"): raw_issue(4, state="sX", labels=("lX",))})
    issue = Plane(fake).get_issue("KS-4")
    assert (issue.state, issue.labels) == ("sX", ("lX",))


def test_list_issues_pages_and_filters():
    first = [raw_issue(n, state="s2", labels=("l2",)) for n in range(1, 100)] + [raw_issue(100, labels=("l2",))]
    second = [raw_issue(101, labels=("l1",))]
    ip = P + "p1/issues/"
    fake = FakeHttp({
        **meta_routes(),
        ("GET", ip + "?per_page=100"): page(first, True, "100:1:0"),
        ("GET", ip + "?per_page=100&cursor=100:1:0"): page(second),
    })
    plane = Plane(fake)
    out = plane.list_issues("KS", state="review")
    assert [i.ref for i in out] == ["KS-100", "KS-101"]
    assert len([c for c in fake.calls if "/issues/?" in c[1]]) == 2
    assert [i.ref for i in plane.list_issues("ks", state="REVIEW", label="Task")] == ["KS-100"]
    assert len(plane.list_issues("KS")) == 101


def test_parent_ref_from_same_page_and_by_id():
    ip = P + "p1/issues/"
    fake = FakeHttp({
        **meta_routes(),
        ("GET", ip + "?per_page=100"): page([raw_issue(1), raw_issue(2, parent="i1"), raw_issue(5, parent="i9")]),
        ("GET", ip + "i9/"): raw_issue(9),
    })
    out = Plane(fake).list_issues("KS")
    assert [i.parent_ref for i in out] == [None, "KS-1", "KS-9"]


def test_parent_ref_none_when_parent_unfetchable():
    ip = P + "p1/issues/"
    fake = FakeHttp({**meta_routes(), ("GET", ip + "?per_page=100"): page([raw_issue(2, parent="gone")])})
    assert Plane(fake).list_issues("KS")[0].parent_ref is None
