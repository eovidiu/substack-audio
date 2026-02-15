"""Podcast RSS feed generation."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List

from feedgen.feed import FeedGenerator

from substack_audio.util import ensure_parent


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
