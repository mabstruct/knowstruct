import pytest

from ks.convert import html_to_md, md_to_html

SKELETON = "## Why\n\nthe need\n\n## Evidence\n\n- one\n- two\n\n## Judged by\n\n**cosmology**: a test\n"


def test_round_trip_keeps_skeleton():
    md = html_to_md(md_to_html(SKELETON))
    assert md.splitlines()[0] == "## Why" and "- one" in md and "**cosmology**" in md and "## Judged by" in md


def test_plane_editor_html_reads_as_markdown():
    html = '<h2>Why</h2><p>the <strong>need</strong></p><ul><li><p>one</p></li></ul>'
    assert html_to_md(html) == "## Why\n\nthe **need**\n\n- one"


def test_empty():
    assert html_to_md("<p></p>") == "" and md_to_html("") == "<p></p>"
    assert html_to_md(None) == "" and html_to_md("") == ""


IDEMPOTENT_HTML = [
    "<ul><li>a<ul><li>b<ul><li>c</li></ul></li></ul></li><li>d</li></ul>",
    "<ol><li>a<ol><li>b</li><li>c</li></ol></li><li>d</li></ol>",
    "<ul><li><p>a</p><ul><li><p>b</p></li></ul></li></ul>",
    "<ul><li>a</li><li>b</li></ul><ol><li>one</li><li>two</li></ol>",
    "<pre><code>* star\n+ plus\n- dash\n</code></pre>",
    "<table><thead><tr><th>a</th><th>b</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>",
    "<p>+ not a list</p>",
    "<p>* not a list either</p>",
]


@pytest.mark.parametrize("h", IDEMPOTENT_HTML)
def test_round_trip_is_idempotent(h):
    md = html_to_md(h)
    assert html_to_md(md_to_html(md)) == md


def test_raw_angle_brackets_are_escaped_not_swallowed():
    html = md_to_html("see docs/analysis/<approach>.md and KS-<n>")
    assert "&lt;approach&gt;" in html and "KS-&lt;n&gt;" in html


def test_list_directly_after_paragraph():
    html = md_to_html("Candidate requirements:\n- one\n- two")
    assert "<ul>" in html and html.count("<li>") == 2


def test_fenced_block_keeps_star_and_plus():
    md = html_to_md(md_to_html("```\n* star\n+ plus\n```"))
    assert "* star" in md and "+ plus" in md


def test_nested_list_survives_round_trip():
    html = md_to_html(html_to_md("<ul><li>a<ul><li>b</li></ul></li></ul>"))
    assert html.count("<ul>") == 2
