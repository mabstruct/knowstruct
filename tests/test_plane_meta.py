import pytest
from fake_http import FakeHttp

from ks.plane import Named, Plane, Project

P = "/workspaces/mabstruct/projects/"


def page(results, more=False, cursor=None):
    return {"results": results, "next_page_results": more, "next_cursor": cursor}


def test_project_lookup_case_insensitive():
    fake = FakeHttp({("GET", P + "?per_page=100"): page([{"identifier": "KS", "name": "KNOWSTRUCT", "id": "p1"}])})
    plane = Plane(fake)
    assert plane.project("ks") == Project("KS", "KNOWSTRUCT", "p1")
    with pytest.raises(KeyError, match="NOPE"):
        plane.project("NOPE")
    plane.projects()
    assert len(fake.calls) == 1


def test_states_and_labels_paged_and_cached():
    fake = FakeHttp({
        ("GET", P + "p1/states/?per_page=100"): page([{"id": "s1", "name": "Backlog"}], True, "c2"),
        ("GET", P + "p1/states/?per_page=100&cursor=c2"): page([{"id": "s2", "name": "Todo"}]),
        ("GET", P + "p1/labels/?per_page=100"): page([{"id": "l1", "name": "idea"}, {"id": "l2", "name": "task"}]),
    })
    plane = Plane(fake)
    p = Project("KS", "KNOWSTRUCT", "p1")
    assert plane.states(p) == [Named("s1", "Backlog"), Named("s2", "Todo")]
    assert plane.labels(p) == [Named("l1", "idea"), Named("l2", "task")]
    plane.states(p)
    plane.labels(p)
    assert len(fake.calls) == 3


def test_me():
    plane = Plane(FakeHttp({("GET", "/users/me/"): {"display_name": "ks-agent"}}))
    assert plane.me() == "ks-agent"
