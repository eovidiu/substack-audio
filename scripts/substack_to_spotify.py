#!/usr/bin/env python3
import email.utils
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from feedgen.feed import FeedGenerator


def env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        return default
    return value


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text)
    return text[:80].strip("-") or "untitled"


def strip_html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n\n".join(lines)


def split_text(text: str, max_len: int) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    cur = ""

    for para in paragraphs:
        candidate = f"{cur}\n\n{para}".strip() if cur else para
        if len(candidate) <= max_len:
            cur = candidate
            continue

        if cur:
            chunks.append(cur)
            cur = ""

        while len(para) > max_len:
            cut = para.rfind(" ", 0, max_len)
            if cut == -1:
                cut = max_len
            chunks.append(para[:cut].strip())
            para = para[cut:].strip()

        cur = para

    if cur:
        chunks.append(cur)

    return chunks


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


def parse_pub_date(pub_date: str) -> datetime:
    try:
        dt = email.utils.parsedate_to_datetime(pub_date)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def fetch_feed_xml(feed_url: str, timeout: int = 30) -> str:
    # Substack may return 403 to generic bot fingerprints; emulate an RSS reader/browser.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.1",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": feed_url.rsplit("/", 1)[0],
    }

    session = requests.Session()
    last_exc = None

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
            raise
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < 3:
                time.sleep(attempt * 2)
                continue
            raise

    raise RuntimeError(f"Failed to fetch feed: {feed_url}") from last_exc


def elevenlabs_tts(
    api_key: str,
    voice_id: str,
    model_id: str,
    output_format: str,
    text: str,
) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "output_format": output_format,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.content


def concat_mp3(parts: List[Path], output_file: Path) -> None:
    if len(parts) == 1:
        output_file.write_bytes(parts[0].read_bytes())
        return

    ffmpeg_available = False
    try:
        subprocess.run(["ffmpeg", "-version"], check=False, capture_output=True)
        ffmpeg_available = True
    except FileNotFoundError:
        ffmpeg_available = False

    if ffmpeg_available:
        with tempfile.NamedTemporaryFile("w", delete=False) as list_file:
            for part in parts:
                list_file.write(f"file '{part.resolve()}'\n")
            list_path = list_file.name

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_path,
                    "-c",
                    "copy",
                    str(output_file),
                ],
                check=True,
                capture_output=True,
            )
            return
        finally:
            try:
                os.unlink(list_path)
            except OSError:
                pass

    with output_file.open("wb") as out:
        for part in parts:
            out.write(part.read_bytes())


def build_audio_url(public_base_url: str, file_name: str) -> str:
    return f"{public_base_url.rstrip('/')}/audio/{file_name}"


def build_feed(episodes: List[Dict], output_feed: Path, cfg: Dict) -> None:
    fg = FeedGenerator()
    fg.load_extension("podcast")

    fg.title(cfg["title"])
    fg.description(cfg["description"])
    if cfg["site_link"]:
        fg.link(href=cfg["site_link"], rel="alternate")
    fg.link(href=cfg["feed_url"], rel="self")
    fg.language(cfg["language"])
    fg.author({"name": cfg["author"], "email": cfg["email"]})

    fg.podcast.itunes_author(cfg["author"])
    fg.podcast.itunes_summary(cfg["description"])
    fg.podcast.itunes_type("episodic")
    fg.podcast.itunes_explicit("no")

    if cfg["image_url"]:
        fg.image(cfg["image_url"])
        fg.podcast.itunes_image(cfg["image_url"])

    sorted_eps = sorted(
        episodes,
        key=lambda e: e.get("pub_date_iso", ""),
        reverse=True,
    )

    for ep in sorted_eps:
        fe = fg.add_entry()
        fe.id(ep["guid"])
        fe.title(ep["title"])
        fe.link(href=ep["link"]) if ep.get("link") else None
        fe.description(ep["description"])
        fe.enclosure(ep["audio_url"], str(ep["audio_size_bytes"]), "audio/mpeg")

        pub_dt = datetime.fromisoformat(ep["pub_date_iso"])
        fe.pubDate(pub_dt)

        fe.podcast.itunes_author(ep.get("author") or cfg["author"])
        fe.podcast.itunes_summary(ep["description"])
        fe.podcast.itunes_explicit("no")

    ensure_parent(output_feed)
    fg.rss_file(str(output_feed), pretty=True)


def main() -> None:
    load_dotenv()

    api_key = env("ELEVENLABS_API_KEY")
    voice_id = env("ELEVENLABS_VOICE_ID")
    model_id = env("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    output_format = env("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
    text_limit = int(env("ELEVENLABS_TEXT_LIMIT", "4500"))

    feed_url = env("SUBSTACK_FEED_URL", "https://ovidiueftimie.substack.com/feed")
    max_posts = int(env("MAX_POSTS_PER_RUN", "3"))

    public_base_url = env("PUBLIC_BASE_URL")
    state_file = Path(env("STATE_FILE", "data/state.json"))
    episodes_file = Path(env("EPISODES_FILE", "data/episodes.json"))
    output_audio_dir = Path(env("OUTPUT_AUDIO_DIR", "output/public/audio"))
    output_feed_file = Path(env("OUTPUT_FEED_FILE", "output/public/feed.xml"))

    if not api_key or not voice_id:
        raise SystemExit("Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID")
    if not public_base_url:
        raise SystemExit("Missing PUBLIC_BASE_URL")

    output_audio_dir.mkdir(parents=True, exist_ok=True)

    state = load_json(state_file, {"processed_guids": []})
    processed_guids = set(state.get("processed_guids", []))
    episodes: List[Dict] = load_json(episodes_file, [])

    print(f"Fetching Substack feed: {feed_url}")
    feed_xml = fetch_feed_xml(feed_url, timeout=30)
    items = parse_rss(feed_xml)

    if not items:
        print("No items found in RSS feed.")
    new_items = [it for it in items if it["guid"] not in processed_guids]
    new_items = sorted(new_items, key=lambda x: parse_pub_date(x["pub_date"]))[:max_posts]

    if not new_items:
        print("No new posts to process.")

    for item in new_items:
        title = item["title"]
        guid = item["guid"]
        link = item["link"]
        pub_dt = parse_pub_date(item["pub_date"])
        pub_iso = pub_dt.isoformat()

        print(f"Generating audio for: {title}")

        text = strip_html_to_text(item["content_html"])
        if not text:
            print(f"Skipping (empty content): {title}")
            processed_guids.add(guid)
            continue

        chunks = split_text(text, text_limit)
        slug = slugify(title)
        date_prefix = pub_dt.strftime("%Y-%m-%d")
        base_name = f"{date_prefix}-{slug}"

        part_files: List[Path] = []
        for idx, chunk in enumerate(chunks, start=1):
            print(f"  chunk {idx}/{len(chunks)}")
            audio_bytes = elevenlabs_tts(
                api_key=api_key,
                voice_id=voice_id,
                model_id=model_id,
                output_format=output_format,
                text=chunk,
            )
            part_path = output_audio_dir / f"{base_name}.part{idx}.mp3"
            part_path.write_bytes(audio_bytes)
            part_files.append(part_path)

        final_audio = output_audio_dir / f"{base_name}.mp3"
        concat_mp3(part_files, final_audio)

        for part in part_files:
            try:
                part.unlink()
            except OSError:
                pass

        excerpt = strip_html_to_text(item["description_html"]).strip()
        if not excerpt:
            excerpt = text[:250] + ("..." if len(text) > 250 else "")

        audio_url = build_audio_url(public_base_url, final_audio.name)
        audio_size = final_audio.stat().st_size

        episodes = [ep for ep in episodes if ep.get("guid") != guid]
        episodes.append(
            {
                "guid": guid,
                "title": title,
                "description": excerpt,
                "author": item.get("author", ""),
                "link": link,
                "pub_date_iso": pub_iso,
                "audio_file": final_audio.name,
                "audio_url": audio_url,
                "audio_size_bytes": audio_size,
            }
        )

        processed_guids.add(guid)

    feed_path_url = f"{public_base_url.rstrip('/')}/feed.xml"
    feed_cfg = {
        "title": env("PODCAST_TITLE", "Substack Audio"),
        "description": env("PODCAST_DESCRIPTION", "Audio versions of Substack posts."),
        "site_link": env("PODCAST_LINK", ""),
        "author": env("PODCAST_AUTHOR", ""),
        "email": env("PODCAST_EMAIL", ""),
        "language": env("PODCAST_LANGUAGE", "en"),
        "image_url": env("PODCAST_IMAGE_URL", ""),
        "feed_url": feed_path_url,
    }

    build_feed(episodes, output_feed_file, feed_cfg)

    save_json(episodes_file, episodes)
    state["processed_guids"] = sorted(processed_guids)
    save_json(state_file, state)

    print(f"Done. Feed written to: {output_feed_file}")
    print(f"Episodes tracked: {len(episodes)}")


if __name__ == "__main__":
    main()
