"""Markdown <-> HTML at the Plane boundary (Plane stores HTML, ks speaks markdown).

md -> HTML is CommonMark (markdown-it-py) with tables and raw HTML off, so text such as
`<approach>` is escaped rather than swallowed. HTML -> md is markdownify, tuned so that its
output parses back to the same HTML: nested list content is indented four spaces and a line
that would open a block (`+ x`, `1. x`, `# x`, `> x`) is escaped.
"""
import re

from markdown_it import MarkdownIt
from markdownify import MarkdownConverter

_EMPTY_HTML = "<p></p>"
_MD = MarkdownIt("commonmark", {"html": False}).enable("table")
_INDENT = "    "
_BLOCK_START = re.compile(r"^(\s*)([-+*]|\d+[.)]|#{1,6}|>)(?=\s|$)", re.M)


def _escape_block_start(text: str) -> str:
    def esc(m: re.Match) -> str:
        marker = m.group(2)
        if marker[0].isdigit():  # "1." -> "1\\."
            return m.group(1) + marker[:-1] + "\\" + marker[-1]
        return m.group(1) + "\\" + marker
    return _BLOCK_START.sub(esc, text)


class _Converter(MarkdownConverter):
    def convert_p(self, el, text, parent_tags):
        out = super().convert_p(el, text, parent_tags)
        return out if "_inline" in parent_tags else _escape_block_start(out)

    def convert_li(self, el, text, parent_tags):
        text = (text or "").strip()
        if not text:
            return "\n"
        parent = el.parent
        if parent is not None and parent.name == "ol":
            start = parent.get("start")
            start = int(start) if start and str(start).isnumeric() else 1
            bullet = f"{start + len(el.find_previous_siblings('li'))}."
        else:
            bullet = "-"
        first, *rest = text.split("\n")
        if not first.startswith("\\"):
            first = _escape_block_start(first)
        lines = [f"{bullet} {first}"] + [_INDENT + line if line.strip() else "" for line in rest]
        return "\n".join(lines) + "\n"


def md_to_html(md: str) -> str:
    if not md or not md.strip():
        return _EMPTY_HTML
    return _MD.render(md).strip()


def html_to_md(html: str | None) -> str:
    if not html or html.strip() == _EMPTY_HTML:
        return ""
    text = _Converter(heading_style="ATX", bullets="-").convert(html)
    return text.strip()
