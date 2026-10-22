import json

import pytest
from fake_http import FakeHttp

from devsys.cli import main
from devsys.plane import Plane

W = "/workspaces/mabstruct"
P = W + "/projects/"


def page(results):
    return {"results": results, "next_page_results": False, "next_cursor": None}


def raw(n, name="Title", state="Review", label="requirement", parent=None, html="<p>body</p>"):
    return {
        "id": f"ks-{n}", "sequence_id": n, "name": name, "description_html": html, "priority": "none",
        "state": state, "labels": [label], "parent": parent,
        "created_at": "2026-10-20T10:00:00Z", "updated_at": "2026-10-20T10:00:00Z",
    }


def comment(cid, text, day="21"):
    return {"id": cid, "actor": "marcus", "created_at": f"2026-10-{day}T10:00:00Z", "comment_html": f"<p>{text}</p>"}


@pytest.fixture
def routes():
    r = {
        ("GET", P + "?per_page=100"): page([{"identifier": "KS", "name": "KnowStruct", "id": "ks"}]),
        ("GET", P + "ks/states/?per_page=100"): page(
            [{"id": s, "name": s} for s in ("Backlog", "Todo", "In Progress", "Review", "Done")]),
        ("GET", P + "ks/labels/?per_page=100"): page([{"id": k, "name": k} for k in ("requirement", "task")]),
        ("GET", P + "ks/issues/?per_page=100"): page([raw(7), raw(8, "other", "Todo", "task")]),
        ("GET", W + "/issues/KS-7/"): raw(7),
        ("GET", "/users/me/"): {"display_name": "ks-agent"},
        ("GET", P + "ks/issues/ks-7/comments/?per_page=100"): page([
            comment("c1", "hello"), comment("c2", "relates to: ZENSTRUCT-3", "22")]),
        ("POST", P + "ks/issues/ks-7/comments/"): comment("c9", "x"),
        ("POST", P + "ks/issues/"): {"id": "ks-7", "sequence_id": 7},
        ("PATCH", P + "ks/issues/ks-7/"): raw(7, state="Todo"),
    }
    return r


def run(routes, argv):
    return main(argv, plane=Plane(FakeHttp(routes)))


def test_whoami(capsys, routes):
    assert run(routes, ["whoami"]) == 0
    assert capsys.readouterr().out == "ks-agent\n"


def test_projects(capsys, routes):
    assert run(routes, ["projects"]) == 0
    assert capsys.readouterr().out == "KS  KnowStruct\n"


def test_create_prints_ref(capsys, tmp_path, routes):
    f = tmp_path / "b.md"
    f.write_text("## Why\n\nx")
    argv = ["create", "KS", "--label", "requirement", "--title", "T", "--body-file", str(f), "--state", "Review"]
    assert run(routes, argv) == 0
    assert capsys.readouterr().out.strip() == "KS-7"


def test_create_with_body_and_relates(capsys, routes):
    argv = ["create", "KS", "--label", "task", "--title", "T", "--body", "x", "--relates", "ks-1", "ZENSTRUCT-2"]
    plane = Plane(FakeHttp(routes))
    assert main(argv, plane=plane) == 0
    posts = [c for c in plane.http.calls if c[0] == "POST" and c[1].endswith("/comments/")]
    assert [p[2]["comment_html"] for p in posts] == ["<p>relates to: KS-1</p>", "<p>relates to: ZENSTRUCT-2</p>"]
    assert plane.http.calls[[c[1] for c in plane.http.calls].index(P + "ks/issues/")][2]["state"] == "Backlog"


def test_update_done_is_error(capsys, routes):
    assert run(routes, ["update", "KS-7", "--state", "Done"]) == 2
    assert "error:" in capsys.readouterr().err


def test_update_prints_ref_and_state(capsys, routes):
    routes[("GET", W + "/issues/KS-7/")] = raw(7, state="Todo")
    assert run(routes, ["update", "KS-7", "--state", "Todo"]) == 0
    assert capsys.readouterr().out == "KS-7  Todo\n"


def test_show_text(capsys, routes):
    assert run(routes, ["show", "ks-7"]) == 0
    assert capsys.readouterr().out == (
        "KS-7  requirement  Title\n"
        "state: Review  priority: none  parent: -  labels: requirement\n"
        "\n"
        "body\n"
        "\n"
        "### comments\n"
        "-- marcus (2026-10-21T10:00:00Z)\n"
        "hello\n"
        "\n"
        "-- marcus (2026-10-22T10:00:00Z)\n"
        "relates to: ZENSTRUCT-3\n"
        "\n"
        "related: ZENSTRUCT-3\n"
    )


def test_show_json_has_body_and_comments(capsys, routes):
    assert run(routes, ["show", "KS-7", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["body_md"] == "body"
    assert [c["id"] for c in data["comments"]] == ["c1", "c2"]
    assert data["related"] == ["ZENSTRUCT-3"]
    assert data["ref"] == "KS-7"


def test_list_prints_lines(capsys, routes, monkeypatch):
    assert run(routes, ["list", "KS", "--label", "task"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert len(out) == 1 and out[0].startswith("KS-8") and "other" in out[0]


def test_digest_passes_today(capsys, routes):
    routes[("GET", P + "ks/issues/ks-7/comments/?per_page=100")] = page([])
    assert run(routes, ["digest", "--today", "2026-10-22"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("### waiting on you (Review)\nKS-7")
    assert "(Review 2d)" in out


def test_comment_prints_id(capsys, tmp_path, routes):
    assert run(routes, ["comment", "KS-7", "--text", "hi"]) == 0
    assert capsys.readouterr().out == "c9\n"
    f = tmp_path / "c.md"
    f.write_text("from file")
    plane = Plane(FakeHttp(routes))
    assert main(["comment", "KS-7", "--file", str(f)], plane=plane) == 0
    assert plane.http.calls[-1][2] == {"comment_html": "<p>from file</p>"}


def test_relate(capsys, routes):
    assert run(routes, ["relate", "ks-7", "zenstruct-3"]) == 0
    assert capsys.readouterr().out == "KS-7 relates to ZENSTRUCT-3\n"


def test_decision(capsys, routes):
    assert run(routes, ["decision", "KS-7"]) == 0
    assert capsys.readouterr().out == "none\n"
    routes[("GET", P + "ks/issues/ks-7/comments/?per_page=100")] = page([comment("c3", "chosen: B")])
    assert run(routes, ["decision", "KS-7"]) == 0
    assert capsys.readouterr().out == "chosen: B\n"


def test_unknown_project_exit_2(capsys, routes):
    assert run(routes, ["list", "NOPE"]) == 2
    assert "error: " in capsys.readouterr().err


def test_usage_error_returns_2(capsys, routes):
    assert run(routes, ["create", "KS"]) == 2


def test_help_returns_0(capsys, routes):
    assert run(routes, ["--help"]) == 0
    assert "digest" in capsys.readouterr().out


def test_create_failed_relate_is_error_naming_ref(capsys, routes):
    routes[("POST", P + "ks/issues/ks-7/comments/")] = (429, {"detail": "throttled"})
    argv = ["create", "KS", "--label", "task", "--title", "T", "--body", "x", "--relates", "KS-1"]
    assert run(routes, argv) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: created KS-7; relating to KS-1 failed:")
