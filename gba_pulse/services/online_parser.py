"""Extract the online-member count from visible homepage link text only."""
from __future__ import annotations
from html.parser import HTMLParser
import re

_ONLINE_PATTERN = re.compile(r"\bonline\s*(?:\(\s*(\d+)\s*\)|\s+(\d+))", re.IGNORECASE)


class _AnchorTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_anchor = False
        self.parts: list[str] = []
        self.anchors: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "a":
            self.in_anchor = True
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.in_anchor:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.in_anchor:
            self.anchors.append(" ".join(self.parts))
            self.in_anchor = False


def parse_online_count(html: str) -> int | None:
    """Find a visible anchor like 'Online (123)' or 'Online 123'."""
    parser = _AnchorTextParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        return None
    for text in parser.anchors:
        match = _ONLINE_PATTERN.search(" ".join(text.split()))
        if match:
            raw = match.group(1) or match.group(2)
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
    return None
