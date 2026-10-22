"""Markdown <-> HTML at the Plane boundary (Plane stores HTML, ks speaks markdown)."""
import re

import markdown
from markdownify import markdownify

_EMPTY_HTML = "<p></p>"


def md_to_html(md: str) -> str:
    if not md or not md.strip():
        return _EMPTY_HTML
    return markdown.markdown(md, extensions=["fenced_code", "tables"])


def html_to_md(html: str | None) -> str:
    if not html or html.strip() == _EMPTY_HTML:
        return ""
    text = markdownify(html, heading_style="ATX", bullets="-")
    text = re.sub(r"^(\s*)[*+] ", r"\1- ", text, flags=re.M)  # normalise bullets
    text = re.sub(r"^(\s*- )\n+", r"\1", text, flags=re.M)  # <li><p> blank line after bullet
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
