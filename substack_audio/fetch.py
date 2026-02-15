"""Fetching: RSS feeds, Substack APIs, single article by URL."""

import subprocess
import time
from typing import Dict

import requests
from bs4 import BeautifulSoup

try:
    import cloudscraper  # type: ignore
except Exception:  # pragma: no cover
    cloudscraper = None

from substack_audio.parse import strip_html_to_text

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


def fetch_feed_xml(feed_url: str, timeout: int = 30) -> str:
    headers = {
        **_BROWSER_HEADERS,
        "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.1",
        "Referer": feed_url.rsplit("/", 1)[0],
    }

    session = requests.Session()
    last_exc = None

    # CI-friendly first try: curl often passes Cloudflare checks where requests fails.
    try:
        curl_cmd = [
            "curl",
            "-fsSL",
            "--max-time",
            str(timeout),
            "-A",
            headers["User-Agent"],
            "-H",
            f"Accept: {headers['Accept']}",
            "-H",
            f"Accept-Language: {headers['Accept-Language']}",
            "-H",
            f"Referer: {headers['Referer']}",
            feed_url,
        ]
        curl_resp = subprocess.run(curl_cmd, check=True, capture_output=True, text=True)
        if curl_resp.stdout.strip():
            return curl_resp.stdout
    except Exception as exc:
        last_exc = exc

    for attempt in range(1, 4):
        try:
            resp = session.get(feed_url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp.text
        except requests.HTTPError as exc:
            last_exc = exc
            code = exc.response.status_code if exc.response is not None else None
            if code in (403, 429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(attempt * 2)
                continue
            break
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            break

    # Last resort for Cloudflare-protected endpoints on CI runner IP ranges.
    if cloudscraper is not None:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "darwin", "mobile": False}
        )
        resp = scraper.get(feed_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text

    raise RuntimeError(f"Failed to fetch feed: {feed_url}") from last_exc


def fetch_archive_json(feed_url: str, timeout: int = 30) -> str:
    base = feed_url.rsplit("/feed", 1)[0] if "/feed" in feed_url else feed_url.rstrip("/")
    archive_url = f"{base}/api/v1/archive?sort=new"
    return fetch_feed_xml(archive_url, timeout=timeout)


def fetch_posts_json(feed_url: str, max_posts: int, timeout: int = 30) -> str:
    base = feed_url.rsplit("/feed", 1)[0] if "/feed" in feed_url else feed_url.rstrip("/")
    posts_url = f"{base}/api/v1/posts?limit={max(10, max_posts * 3)}"
    return fetch_feed_xml(posts_url, timeout=timeout)


def fetch_article_by_url(url: str, timeout: int = 30) -> Dict:
    """Fetch a single Substack article by its URL and extract structured content."""
    headers = {
        **_BROWSER_HEADERS,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": url.rsplit("/", 1)[0],
    }

    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract title from meta or h1
    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Untitled"

    # Extract author
    author = ""
    author_meta = soup.find("meta", attrs={"name": "author"})
    if author_meta and author_meta.get("content"):
        author = author_meta["content"].strip()

    # Extract publication date
    pub_date = ""
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        pub_date = time_tag["datetime"].strip()

    # Extract description
    description = ""
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        description = og_desc["content"].strip()

    # Extract article body — Substack uses several possible containers
    content_html = ""
    for selector in [
        {"class_": "body markup"},
        {"class_": "available-content"},
        {"class_": "post-content"},
    ]:
        body_div = soup.find("div", **selector)
        if body_div:
            content_html = str(body_div)
            break

    if not content_html:
        article = soup.find("article")
        if article:
            content_html = str(article)

    content_text = strip_html_to_text(content_html)
    word_count = len(content_text.split())

    return {
        "title": title,
        "author": author,
        "pub_date": pub_date,
        "description": description,
        "link": url,
        "content_html": content_html,
        "content_text": content_text,
        "word_count": word_count,
    }
