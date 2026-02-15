"""Parsing: RSS XML, Substack JSON APIs, HTML stripping, item selectors."""

import json
import xml.etree.ElementTree as ET
from typing import Dict, List

from bs4 import BeautifulSoup


def strip_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n\n".join(lines)


def parse_rss(feed_xml: str) -> List[Dict]:
    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "dc": "http://purl.org/dc/elements/1.1/",
    }

    root = ET.fromstring(feed_xml)
    channel = root.find("channel")
    if channel is None:
        return []

    items = []
    for item in channel.findall("item"):
        title = (item.findtext("title") or "Untitled").strip()
        link = (item.findtext("link") or "").strip()
        guid = (item.findtext("guid") or link or title).strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = item.findtext("description") or ""
        content_encoded = item.findtext("content:encoded", namespaces=ns) or description
        author = item.findtext("dc:creator", namespaces=ns) or ""

        items.append(
            {
                "title": title,
                "link": link,
                "guid": guid,
                "pub_date": pub_date,
                "description_html": description,
                "content_html": content_encoded,
                "author": author.strip(),
            }
        )

    return items


def _parse_substack_json_rows(rows: list) -> List[Dict]:
    items: List[Dict] = []
    for row in rows:
        title = (row.get("title") or "Untitled").strip()
        link = (row.get("canonical_url") or "").strip()
        guid = str(row.get("id") or link or title).strip()
        pub_date = (row.get("post_date") or "").strip()
        description = (row.get("description") or row.get("subtitle") or "").strip()
        content_html = row.get("body_html") or row.get("truncated_body_text") or description

        author = ""
        bylines = row.get("publishedBylines") or []
        if bylines and isinstance(bylines, list):
            first = bylines[0] or {}
            author = (first.get("name") or "").strip()

        items.append(
            {
                "title": title,
                "link": link,
                "guid": guid,
                "pub_date": pub_date,
                "description_html": description,
                "content_html": content_html,
                "author": author,
            }
        )
    return items


def parse_archive_json(archive_json: str) -> List[Dict]:
    return _parse_substack_json_rows(json.loads(archive_json))


def parse_posts_json(posts_json: str) -> List[Dict]:
    return _parse_substack_json_rows(json.loads(posts_json))


def item_matches_selector(item: Dict, selector: str) -> bool:
    sel = selector.strip()
    if not sel:
        return False

    title = (item.get("title") or "").strip()
    guid = str(item.get("guid") or "").strip()
    link = (item.get("link") or "").strip()

    if ":" in sel:
        field, value = sel.split(":", 1)
        field = field.strip().lower()
        value = value.strip()
        if not value:
            return False

        if field in {"guid", "id"}:
            return guid.lower() == value.lower()
        if field in {"link", "url"}:
            return link.lower() == value.lower()
        if field == "title":
            return value.lower() in title.lower()

    needle = sel.lower()
    return (
        needle in title.lower()
        or needle in guid.lower()
        or needle in link.lower()
    )


def select_items(items: List[Dict], selectors: List[str]) -> List[Dict]:
    return [it for it in items if any(item_matches_selector(it, sel) for sel in selectors)]
