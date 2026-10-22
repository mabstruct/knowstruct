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
