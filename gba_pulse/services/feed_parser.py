"""Small, dependency-free parser for RSS 2.0, RDF/RSS and Atom feeds."""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import re
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class FeedItem:
    title: str
    link: str
    summary: str = ""
    published: str = ""


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif tag.lower() in {"br", "p", "div", "li"} and self._skip_depth == 0:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag.lower() in {"p", "div", "li"} and self._skip_depth == 0:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self.parts.append(data)


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(value)
        parser.close()
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]*>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].split(":")[-1].lower()


def _child_text(node: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in list(node):
        if _local_name(child.tag) in wanted:
            if _local_name(child.tag) == "link":
                # Atom links normally use href; RSS links use text.
                href = child.attrib.get("href", "").strip()
                rel = child.attrib.get("rel", "alternate")
                if href and rel in {"alternate", ""}:
                    return href
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return ""


def _normalise_url(raw_url: str, base_url: str) -> str:
    candidate = urljoin(base_url, raw_url.strip()) if raw_url else ""
    parsed = urlparse(candidate)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    if host not in {"gamerz.ba", "www.gamerz.ba"}:
        return ""
    return candidate


def parse_feed(xml_data: str | bytes, base_url: str, limit: int = 5) -> list[FeedItem]:
    """Parse RSS/Atom XML. Invalid or unsupported content returns an empty list."""
    if limit <= 0:
        return []
    if isinstance(xml_data, bytes):
        if len(xml_data) > 1_000_000:
            return []
    elif len(xml_data.encode("utf-8", errors="replace")) > 1_000_000:
        return []
    try:
        root = ET.fromstring(xml_data)
    except (ET.ParseError, ValueError, TypeError):
        return []

    root_name = _local_name(root.tag)
    entries: list[ET.Element] = []
    if root_name == "feed":  # Atom
        entries = [child for child in list(root) if _local_name(child.tag) == "entry"]
    elif root_name == "rdf":  # RDF/RSS 1.0; items may be direct children
        entries = [child for child in list(root) if _local_name(child.tag) == "item"]
    else:  # RSS 2.0's channel/item structure
        entries = [node for node in root.iter() if _local_name(node.tag) == "item"]

    items: list[FeedItem] = []
    seen: set[str] = set()
    for entry in entries:
        title = strip_html(_child_text(entry, "title")) or "(Bez naslova)"
        raw_link = _child_text(entry, "link")
        if not raw_link:
            # GUIDs are not necessarily URLs; accept one only when it is absolute.
            guid = _child_text(entry, "guid")
            parsed_guid = urlparse(guid)
            raw_link = guid if parsed_guid.scheme in {"http", "https"} and parsed_guid.netloc else ""
        link = _normalise_url(raw_link, base_url)
        summary = strip_html(_child_text(entry, "description", "summary", "content", "encoded"))
        published = strip_html(_child_text(entry, "pubDate", "published", "updated", "date"))
        identity = link or title.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        items.append(FeedItem(title=title[:240], link=link, summary=summary[:600], published=published[:100]))
        if len(items) >= max(0, limit):
            break
    return items
