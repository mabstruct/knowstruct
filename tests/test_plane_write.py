import pytest
from fake_http import FakeHttp

from devsys.plane import Comment, PartialWrite, Plane, Refused, decision

W = "/workspaces/mabstruct"
P = W + "/projects/"
C = P + "p1/issues/i7/comments/"


def page(results):
    return {"results": results, "next_page_results": False, "next_cursor": None}


def raw_issue(n=7, **extra):
    return {
        "id": f"i{n}", "sequence_id": n, "name": f"issue {n}", "description_html": "<p>x</p>",
        "priority": "high", "state": "s_review", "labels": ["l_req"], "parent": None,
        "created_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-02T10:00:00Z", **extra,
    }


def raw_comment(i, html, at, actor="u1"):
    return {"id": i, "actor": actor, "created_at": at, "comment_html": html}


@pytest.fixture
def fake():
    return FakeHttp({
        ("GET", P + "?per_page=100"): page([{"identifier": "KS", "name": "KNOWSTRUCT", "id": "p1"}]),
        ("GET", P + "p1/states/?per_page=100"): page([
            {"id": "s_review", "name": "Review"}, {"id": "s_backlog", "name": "Backlog"}]),
        ("GET", P + "p1/labels/?per_page=100"): page([
            {"id": "l_req", "name": "requirement"}, {"id": "l_idea", "name": "idea"}]),
        ("POST", P + "p1/issues/"): {"id": "i7", "sequence_id": 7},
        ("GET", W + "/issues/KS-7/"): raw_issue(7),
        ("GET", W + "/issues/KS-2/"): raw_issue(2),
        ("PATCH", P + "p1/issues/i7/"): {},
        ("POST", C): raw_comment("c9", "<p>relates to: ZENSTRUCT-3</p>", "2026-10-03T00:00:00Z"),
        ("GET", C + "?per_page=100"): page([
            raw_comment("c2", "<p>chosen: B</p><p>because</p>", "2026-10-02T00:00:00Z", {"display_name": "Ann"}),
            raw_comment("c1", "<p>first</p>", "2026-10-01T00:00:00Z"),
        ]),
    })


@pytest.fixture
def plane(fake):
    return Plane(fake)


def posts(fake):
    return [c for c in fake.calls if c[0] == "POST"]


def test_create_issue_posts_ids_and_html(plane, fake):
    issue = plane.create_issue("KS", "T", "## Why\n\nx", "requirement", state="Review", priority="high")
    m, p, body = posts(fake)[0]
    assert p == "/workspaces/mabstruct/projects/p1/issues/" and body["state"] == "s_review" and body["labels"] == ["l_req"] and body["description_html"].startswith("<h2>Why</h2>")
    assert body["name"] == "T" and body["priority"] == "high"
    assert issue.ref == "KS-7"


def test_create_issue_unknown_label_makes_no_post(plane, fake):
    with pytest.raises(KeyError):
        plane.create_issue("KS", "T", "", "nope")
    assert not posts(fake)


def test_create_issue_unknown_state_makes_no_post(plane, fake):
    with pytest.raises(KeyError):
        plane.create_issue("KS", "T", "", "idea", state="Nope")
    assert not posts(fake)


def test_create_issue_parent_same_project(plane, fake):
    plane.create_issue("KS", "T", "", "idea", parent="KS-2")
    assert posts(fake)[0][2]["parent"] == "i2"


def test_create_issue_parent_other_project_raises(plane, fake):
    with pytest.raises(ValueError):
        plane.create_issue("KS", "T", "", "idea", parent="ZENSTRUCT-2")
    assert not posts(fake)


def test_create_issue_with_relates_posts_comment(plane, fake):
    plane.create_issue("KS", "T", "", "idea", relates=("ZENSTRUCT-3",))
    assert any(c[2] and c[2].get("comment_html") == "<p>relates to: ZENSTRUCT-3</p>" for c in fake.calls)


@pytest.mark.parametrize("s", ["Done", "done", "CANCELLED", " cancelled "])
def test_update_refuses_terminal_states(plane, fake, s):
    with pytest.raises(Refused):
        plane.update_issue("KS-7", state=s)
    assert not [c for c in fake.calls if c[0] == "PATCH"]


def test_update_without_body_sends_no_description(plane, fake):
    plane.update_issue("KS-7", state="Review")
    body = [c for c in fake.calls if c[0] == "PATCH"][0][2]
    assert "description_html" not in body and body == {"state": "s_review"}


def test_update_sends_given_fields(plane, fake):
    plane.update_issue("KS-7", body_md="hi", title="N", priority="low")
    call = [c for c in fake.calls if c[0] == "PATCH"][0]
    assert call[1] == P + "p1/issues/i7/"
    assert call[2] == {"description_html": "<p>hi</p>", "name": "N", "priority": "low"}


def test_comments_oldest_first_and_decision(plane):
    cs = plane.comments("KS-7")
    assert [c.text_md for c in cs] == ["first", "chosen: B\n\nbecause"]
    assert [c.actor for c in cs] == ["u1", "Ann"]
    assert decision(cs) == ("chosen", "B")
    assert decision([Comment("1", "a", "t", "rejected: too wide")]) == ("rejected", "too wide")
    assert decision([Comment("1", "a", "t", "ok")]) is None


def test_comment_posts_html(plane, fake):
    c = plane.comment("KS-7", "hello")
    assert posts(fake)[0][2] == {"comment_html": "<p>hello</p>"}
    assert c.id == "c9"


def test_relate_uppercases_refs(plane, fake):
    plane.relate("ks-7", "zenstruct-3")
    assert posts(fake)[0][2] == {"comment_html": "<p>relates to: ZENSTRUCT-3</p>"}


def test_relate_invalid_ref_makes_no_post(plane, fake):
    with pytest.raises(ValueError):
        plane.relate("KS-7", "garbage")
    assert not posts(fake)


def test_related_parses_comments(plane, fake):
    fake.routes[("GET", C + "?per_page=100")] = page([
        raw_comment("c1", "<p>relates to: KS-1, zenstruct-3</p>", "2026-10-01T00:00:00Z"),
        raw_comment("c2", "<p>relates to: KS-1</p>", "2026-10-02T00:00:00Z"),
        raw_comment("c3", "<p>unrelated</p>", "2026-10-03T00:00:00Z"),
    ])
    assert plane.related("KS-7") == ["KS-1", "ZENSTRUCT-3"]


def test_create_issue_invalid_relates_makes_no_post(plane, fake):
    with pytest.raises(ValueError):
        plane.create_issue("KS", "T", "", "idea", relates=("garbage",))
    assert not posts(fake)


def test_related_skips_free_text_and_extracts_mixed(plane, fake):
    fake.routes[("GET", C + "?per_page=100")] = page([
        raw_comment("c1", "<p>relates to: the login bug</p>", "2026-10-01T00:00:00Z"),
        raw_comment("c2", "<p>relates to: KS-1 (see notes)</p>", "2026-10-02T00:00:00Z"),
    ])
    assert plane.related("KS-7") == ["KS-1"]


def test_create_issue_failed_relate_names_created_ref(plane, fake):
    fake.routes[("POST", C)] = (429, {"detail": "throttled"})
    with pytest.raises(PartialWrite) as e:
        plane.create_issue("KS", "T", "", "idea", relates=("KS-1",))
    assert e.value.ref == "KS-7"
    msg = str(e.value)
    assert msg.startswith("created KS-7; relating to KS-1 failed: ") and "429" in msg
