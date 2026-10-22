import re

_REF = re.compile(r"([A-Za-z][A-Za-z0-9]*)[-\s]\s*(\d+)")


def parse_ref(s: str) -> tuple[str, int]:
    m = _REF.fullmatch(s.strip())
    if not m:
        raise ValueError(f"not an issue reference: {s!r}")
    return m.group(1).upper(), int(m.group(2))
