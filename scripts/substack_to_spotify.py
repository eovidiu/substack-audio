#!/usr/bin/env python3
"""CLI entrypoint: batch-process Substack RSS feed into podcast episodes."""

from pathlib import Path
from typing import Dict, List

import requests
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

from substack_audio.config import env, env_bool, parse_csv
from substack_audio.feed import build_audio_url, build_feed
from substack_audio.fetch import fetch_archive_json, fetch_feed_xml, fetch_posts_json
from substack_audio.parse import (
    parse_archive_json,
    parse_posts_json,
    parse_rss,
    select_items,
    strip_html_to_text,
)
from substack_audio.tts import concat_mp3, elevenlabs_tts, split_text
from substack_audio.util import load_json, parse_pub_date, save_json, slugify


def main() -> None:
    load_dotenv()

    api_key = env("ELEVENLABS_API_KEY")
    voice_id = env("ELEVENLABS_VOICE_ID")
    model_id = env("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    output_format = env("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
    text_limit = int(env("ELEVENLABS_TEXT_LIMIT", "4500"))

    feed_url = env("SUBSTACK_FEED_URL", "https://ovidiueftimie.substack.com/feed")
    max_posts = int(env("MAX_POSTS_PER_RUN", "3"))
    target_articles = parse_csv(env("TARGET_ARTICLES", ""))
    target_include_processed = env_bool("TARGET_INCLUDE_PROCESSED", True)

    public_base_url = env("PUBLIC_BASE_URL")
    state_file = Path(env("STATE_FILE", "data/state.json"))
    episodes_file = Path(env("EPISODES_FILE", "data/episodes.json"))
    output_audio_dir = Path(env("OUTPUT_AUDIO_DIR", "output/public/audio"))
    output_feed_file = Path(env("OUTPUT_FEED_FILE", "output/public/feed.xml"))

    if not api_key or not voice_id:
        raise SystemExit("Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID")
    if not public_base_url:
        raise SystemExit("Missing PUBLIC_BASE_URL")

    elevenlabs_client = ElevenLabs(api_key=api_key)

    output_audio_dir.mkdir(parents=True, exist_ok=True)

    state = load_json(state_file, {"processed_guids": []})
    processed_guids = set(state.get("processed_guids", []))
    episodes: List[Dict] = load_json(episodes_file, [])

    print(f"Fetching Substack feed: {feed_url}")
    try:
        feed_xml = fetch_feed_xml(feed_url, timeout=30)
        items = parse_rss(feed_xml)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status != 403:
            raise
        print("RSS feed returned 403, falling back to Substack posts API...")
        try:
            posts_json = fetch_posts_json(feed_url, max_posts=max_posts, timeout=30)
            items = parse_posts_json(posts_json)
        except requests.HTTPError:
            print("Posts API returned 403, falling back to Substack archive API...")
            archive_json = fetch_archive_json(feed_url, timeout=30)
            items = parse_archive_json(archive_json)

    if not items:
        print("No items found in RSS feed.")
    if target_articles:
        print(f"Cherry-pick mode enabled with {len(target_articles)} selector(s).")
        new_items = select_items(items, target_articles)
        if not target_include_processed:
            new_items = [it for it in new_items if it["guid"] not in processed_guids]
        new_items = sorted(new_items, key=lambda x: parse_pub_date(x["pub_date"]))
        print(f"Matched {len(new_items)} article(s) for processing.")
    else:
        new_items = [it for it in items if it["guid"] not in processed_guids]
        new_items = sorted(new_items, key=lambda x: parse_pub_date(x["pub_date"]))[:max_posts]

    if not new_items:
        print("No posts to process.")

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
                client=elevenlabs_client,
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
