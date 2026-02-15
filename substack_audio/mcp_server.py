"""MCP server: exposes Substack Audio tools to Claude Desktop."""

import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from fastmcp import FastMCP

from substack_audio.config import env
from substack_audio.feed import build_audio_url, build_feed
from substack_audio.fetch import fetch_article_by_url
from substack_audio.parse import strip_html_to_text
from substack_audio.tts import concat_mp3, elevenlabs_tts, split_text
from substack_audio.util import load_json, parse_pub_date, save_json, slugify

# Secrets (API keys) live in .env (gitignored). Non-secret defaults live in .mcp.json.
# override=True lets .env values win over empty placeholders set by .mcp.json env block.
load_dotenv(override=True)

mcp = FastMCP("Substack Audio")

# Resolve paths relative to the project root (where .mcp.json lives).
_PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", ".")).resolve()


def _state_file() -> Path:
    return _PROJECT_ROOT / env("STATE_FILE", "data/state.json")


def _episodes_file() -> Path:
    return _PROJECT_ROOT / env("EPISODES_FILE", "data/episodes.json")


def _output_audio_dir() -> Path:
    p = _PROJECT_ROOT / env("OUTPUT_AUDIO_DIR", "output/public/audio")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _output_feed_file() -> Path:
    return _PROJECT_ROOT / env("OUTPUT_FEED_FILE", "output/public/feed.xml")


def _feed_cfg() -> dict:
    public_base_url = env("PUBLIC_BASE_URL")
    return {
        "title": env("PODCAST_TITLE", "Substack Audio"),
        "description": env("PODCAST_DESCRIPTION", "Audio versions of Substack posts."),
        "site_link": env("PODCAST_LINK", ""),
        "author": env("PODCAST_AUTHOR", ""),
        "email": env("PODCAST_EMAIL", ""),
        "language": env("PODCAST_LANGUAGE", "en"),
        "image_url": env("PODCAST_IMAGE_URL", ""),
        "feed_url": f"{public_base_url.rstrip('/')}/feed.xml",
    }


@mcp.tool()
def setup_check() -> dict:
    """Check plugin configuration and return what's ready, what's missing, and what needs attention.

    Call this before generating episodes to verify all required settings are in place.
    If anything is missing, the response includes setup instructions for each value.
    """
    required = {
        "ELEVENLABS_API_KEY": {
            "value": env("ELEVENLABS_API_KEY"),
            "label": "ElevenLabs API key",
            "help": "Sign up at elevenlabs.io, go to Profile > API Keys, and copy your key.",
        },
        "ELEVENLABS_VOICE_ID": {
            "value": env("ELEVENLABS_VOICE_ID"),
            "label": "ElevenLabs Voice ID",
            "help": "In ElevenLabs, go to Voices, pick a voice, and copy the Voice ID from the URL or settings.",
        },
        "PUBLIC_BASE_URL": {
            "value": env("PUBLIC_BASE_URL"),
            "label": "Public base URL for audio files",
            "help": "The URL where your podcast files will be hosted (e.g. https://yourname.github.io/substack-audio). Set up GitHub Pages: repo Settings > Pages > Source: GitHub Actions.",
        },
    }

    recommended = {
        "PODCAST_TITLE": {
            "value": env("PODCAST_TITLE"),
            "label": "Podcast title",
            "help": "The name of your podcast as it appears in Spotify/Apple Podcasts.",
        },
        "PODCAST_AUTHOR": {
            "value": env("PODCAST_AUTHOR"),
            "label": "Podcast author name",
            "help": "Your name or pen name.",
        },
        "PODCAST_DESCRIPTION": {
            "value": env("PODCAST_DESCRIPTION"),
            "label": "Podcast description",
            "help": "A short description of your podcast for directories.",
        },
        "PODCAST_LINK": {
            "value": env("PODCAST_LINK"),
            "label": "Podcast website link",
            "help": "URL to your Substack or podcast website.",
        },
        "PODCAST_EMAIL": {
            "value": env("PODCAST_EMAIL"),
            "label": "Contact email",
            "help": "Email shown in podcast directories.",
        },
        "PODCAST_IMAGE_URL": {
            "value": env("PODCAST_IMAGE_URL"),
            "label": "Podcast cover image URL",
            "help": "URL to a square image (1400x1400 min, 3000x3000 max) for podcast directories.",
        },
    }

    missing = [
        {"env_var": k, "label": v["label"], "help": v["help"]}
        for k, v in required.items()
        if not v["value"]
    ]
    warnings = [
        {"env_var": k, "label": v["label"], "help": v["help"]}
        for k, v in recommended.items()
        if not v["value"]
    ]

    ready = len(missing) == 0

    config = {
        k: "***" if "KEY" in k else v["value"]
        for section in (required, recommended)
        for k, v in section.items()
        if v["value"]
    }

    result = {
        "ready": ready,
        "missing": missing,
        "warnings": warnings,
        "config": config,
    }

    if not ready:
        result["setup_instructions"] = (
            "Create a .env file in your working directory with the missing values. "
            "Example:\n\n"
            "ELEVENLABS_API_KEY=your_key_here\n"
            "ELEVENLABS_VOICE_ID=your_voice_id\n"
            "PUBLIC_BASE_URL=https://yourname.github.io/substack-audio\n\n"
            "Then update the connector in Claude Desktop to point --directory "
            "to your working directory, and add PROJECT_ROOT as an env var "
            "pointing to the same path."
        )

    return result


@mcp.tool()
def fetch_article(url: str) -> dict:
    """Fetch a Substack article by URL and return its text content with metadata.

    Returns title, author, publication date, description, full text, and word count.
    Use this to retrieve article content before creating a narrative.
    """
    return fetch_article_by_url(url)


@mcp.tool()
def generate_audio(text: str, title: str, pub_date: str = "") -> dict:
    """Convert narrative text into an MP3 audio file via ElevenLabs TTS.

    Chunks the text, generates audio for each chunk, and concatenates into a single MP3.
    Returns the audio file path, public URL, and file size in bytes.

    Args:
        text: The narrative text to convert to speech.
        title: Episode title (used for the filename).
        pub_date: ISO date string for filename prefix (defaults to today).
    """
    api_key = env("ELEVENLABS_API_KEY")
    voice_id = env("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        return {
            "error": "Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID. "
            "Run the setup_check tool or /setup command to see what's needed."
        }

    model_id = env("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    output_format = env("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
    text_limit = int(env("ELEVENLABS_TEXT_LIMIT", "4500"))
    public_base_url = env("PUBLIC_BASE_URL")

    if not public_base_url:
        return {
            "error": "Missing PUBLIC_BASE_URL. "
            "Run the setup_check tool or /setup command to see what's needed."
        }

    client = ElevenLabs(api_key=api_key)
    output_dir = _output_audio_dir()

    # Parse pub_date for filename prefix
    if pub_date:
        try:
            dt = parse_pub_date(pub_date)
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    date_prefix = dt.strftime("%Y-%m-%d")
    slug = slugify(title)
    base_name = f"{date_prefix}-{slug}"

    chunks = split_text(text, text_limit)
    part_files = []

    for idx, chunk in enumerate(chunks, start=1):
        audio_bytes = elevenlabs_tts(
            client=client,
            voice_id=voice_id,
            model_id=model_id,
            output_format=output_format,
            text=chunk,
        )
        part_path = output_dir / f"{base_name}.part{idx}.mp3"
        part_path.write_bytes(audio_bytes)
        part_files.append(part_path)

    final_audio = output_dir / f"{base_name}.mp3"
    concat_mp3(part_files, final_audio)

    # Clean up part files
    for part in part_files:
        try:
            part.unlink()
        except OSError:
            pass

    audio_url = build_audio_url(public_base_url, final_audio.name)
    audio_size = final_audio.stat().st_size

    return {
        "audio_file": final_audio.name,
        "audio_path": str(final_audio),
        "audio_url": audio_url,
        "audio_size_bytes": audio_size,
        "chunks_processed": len(chunks),
    }


@mcp.tool()
def list_episodes() -> dict:
    """List all current podcast episodes and processing state.

    Returns the episode list from episodes.json and the count of processed GUIDs.
    """
    episodes = load_json(_episodes_file(), [])
    state = load_json(_state_file(), {"processed_guids": []})
    return {
        "episodes": episodes,
        "episode_count": len(episodes),
        "processed_guids_count": len(state.get("processed_guids", [])),
    }


@mcp.tool()
def update_feed(
    title: str,
    description: str,
    author: str,
    link: str,
    guid: str,
    pub_date_iso: str,
    audio_file: str,
    audio_url: str,
    audio_size_bytes: int,
) -> dict:
    """Add a new episode to the podcast feed and update tracking state.

    Updates episodes.json, state.json, and rebuilds feed.xml.

    Args:
        title: Episode title.
        description: Episode description/excerpt.
        author: Episode author name.
        link: Original article URL.
        guid: Unique identifier for the episode (typically the article URL).
        pub_date_iso: Publication date in ISO 8601 format.
        audio_file: MP3 filename (e.g., "2025-10-26-my-article.mp3").
        audio_url: Full public URL to the MP3 file.
        audio_size_bytes: File size in bytes.
    """
    episodes_file = _episodes_file()
    state_file = _state_file()

    episodes = load_json(episodes_file, [])
    state = load_json(state_file, {"processed_guids": []})
    processed_guids = set(state.get("processed_guids", []))

    # Remove existing entry for this guid (allows re-generation)
    episodes = [ep for ep in episodes if ep.get("guid") != guid]
    episodes.append(
        {
            "guid": guid,
            "title": title,
            "description": description,
            "author": author,
            "link": link,
            "pub_date_iso": pub_date_iso,
            "audio_file": audio_file,
            "audio_url": audio_url,
            "audio_size_bytes": audio_size_bytes,
        }
    )

    processed_guids.add(guid)

    # Rebuild feed
    cfg = _feed_cfg()
    build_feed(episodes, _output_feed_file(), cfg)

    # Persist state
    save_json(episodes_file, episodes)
    state["processed_guids"] = sorted(processed_guids)
    save_json(state_file, state)

    return {
        "episodes_count": len(episodes),
        "feed_path": str(_output_feed_file()),
        "state_path": str(state_file),
    }


if __name__ == "__main__":
    mcp.run()
