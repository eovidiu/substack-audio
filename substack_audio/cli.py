"""CLI entry point: replaces MCP server with direct Bash-callable commands.

Usage: uv run --directory <plugin-dir> python -m substack_audio.cli <command> [args]

All commands output JSON to stdout.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from substack_audio.config import env
from substack_audio.feed import build_audio_url, build_feed
from substack_audio.fetch import fetch_article_by_url
from substack_audio.tts import concat_mp3, elevenlabs_tts, split_text
from substack_audio.util import load_json, parse_pub_date, save_json, slugify

# Plugin directory = parent of substack_audio/ package.
_PLUGIN_DIR = Path(__file__).resolve().parent.parent

# Load .env from multiple locations (first found wins, later overrides earlier):
# 1. Plugin directory (shipped defaults in .env.example, or local dev .env)
# 2. Podcast repo (user's secrets — this is the primary location)
load_dotenv(_PLUGIN_DIR / ".env", override=True)

# Check config for podcast repo path and load its .env too
_config_path = _PLUGIN_DIR / "data" / "config.json"
if _config_path.exists():
    import json as _json
    _cfg = _json.loads(_config_path.read_text())
    _podcast_env = Path(_cfg.get("podcast_repo_path", "")) / ".env"
    if _podcast_env.exists():
        load_dotenv(_podcast_env, override=True)

# Project root: where data/ and output/ live.
# Defaults to plugin dir, but CLI commands can override with --project-root.
_DEFAULT_PROJECT_ROOT = str(_PLUGIN_DIR)


def _project_root(args) -> Path:
    """Resolve project root from CLI args or env."""
    root = getattr(args, "project_root", None) or os.getenv("PROJECT_ROOT", _DEFAULT_PROJECT_ROOT)
    return Path(root).resolve()


def _config_file() -> Path:
    return _PLUGIN_DIR / "data" / "config.json"


def _output(data: dict):
    """Print JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


# --- Commands ---


def cmd_setup_check(args):
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
            "help": "The URL where your podcast files will be hosted (e.g. https://yourname.github.io/my-podcast).",
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

    config = {
        k: "***" if "KEY" in k else v["value"]
        for section in (required, recommended)
        for k, v in section.items()
        if v["value"]
    }

    _output({
        "ready": len(missing) == 0,
        "missing": missing,
        "warnings": warnings,
        "config": config,
        "voice_model": env("ELEVENLABS_MODEL_ID", "eleven_v3_conversational"),
        "plugin_dir": str(_PLUGIN_DIR),
    })


def cmd_fetch_article(args):
    result = fetch_article_by_url(args.url)
    _output(result)


def cmd_generate_audio(args):
    from elevenlabs.client import ElevenLabs

    api_key = env("ELEVENLABS_API_KEY")
    voice_id = env("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        _output({"error": "Missing ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID. Run /setup first."})
        sys.exit(1)

    public_base_url = env("PUBLIC_BASE_URL")
    if not public_base_url:
        _output({"error": "Missing PUBLIC_BASE_URL. Run /setup first."})
        sys.exit(1)

    model_id = env("ELEVENLABS_MODEL_ID", "eleven_v3_conversational")
    output_format = env("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
    text_limit = int(env("ELEVENLABS_TEXT_LIMIT", "4500"))

    # Read narrative text from file
    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text:
        _output({"error": f"Text file is empty: {args.text_file}"})
        sys.exit(1)

    root = _project_root(args)
    output_dir = root / "output" / "public" / "audio"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse pub_date for filename prefix
    if args.pub_date:
        try:
            dt = parse_pub_date(args.pub_date)
        except Exception:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    date_prefix = dt.strftime("%Y-%m-%d")
    slug = slugify(args.title)
    base_name = f"{date_prefix}-{slug}"

    client = ElevenLabs(api_key=api_key)
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
    for orphan in output_dir.glob("*.part*.mp3"):
        try:
            orphan.unlink()
        except OSError:
            pass

    audio_url = build_audio_url(public_base_url, final_audio.name)
    audio_size = final_audio.stat().st_size

    _output({
        "audio_file": final_audio.name,
        "audio_path": str(final_audio),
        "audio_url": audio_url,
        "audio_size_bytes": audio_size,
        "chunks_processed": len(chunks),
    })


def cmd_update_feed(args):
    root = _project_root(args)
    episodes_file = root / "data" / "episodes.json"
    state_file = root / "data" / "state.json"
    output_feed = root / "output" / "public" / "feed.xml"

    episodes_file.parent.mkdir(parents=True, exist_ok=True)
    output_feed.parent.mkdir(parents=True, exist_ok=True)

    episodes = load_json(episodes_file, [])
    state = load_json(state_file, {"processed_guids": []})
    processed_guids = set(state.get("processed_guids", []))

    # Remove existing entry for this guid (allows re-generation)
    episodes = [ep for ep in episodes if ep.get("guid") != args.guid]
    episodes.append({
        "guid": args.guid,
        "title": args.title,
        "description": args.description,
        "author": args.author,
        "link": args.link,
        "pub_date_iso": args.pub_date_iso,
        "audio_file": args.audio_file,
        "audio_url": args.audio_url,
        "audio_size_bytes": args.audio_size_bytes,
    })

    processed_guids.add(args.guid)

    # Rebuild feed
    public_base_url = env("PUBLIC_BASE_URL")
    cfg = {
        "title": env("PODCAST_TITLE", "Substack Audio"),
        "description": env("PODCAST_DESCRIPTION", "Audio versions of Substack posts."),
        "site_link": env("PODCAST_LINK", ""),
        "author": env("PODCAST_AUTHOR", ""),
        "email": env("PODCAST_EMAIL", ""),
        "language": env("PODCAST_LANGUAGE", "en"),
        "image_url": env("PODCAST_IMAGE_URL", ""),
        "feed_url": f"{public_base_url.rstrip('/')}/feed.xml" if public_base_url else "",
    }
    build_feed(episodes, output_feed, cfg)

    # Persist
    save_json(episodes_file, episodes)
    state["processed_guids"] = sorted(processed_guids)
    save_json(state_file, state)

    _output({
        "episodes_count": len(episodes),
        "feed_path": str(output_feed),
        "state_path": str(state_file),
    })


def cmd_list_episodes(args):
    root = _project_root(args)
    episodes_file = root / "data" / "episodes.json"
    state_file = root / "data" / "state.json"

    episodes = load_json(episodes_file, [])
    state = load_json(state_file, {"processed_guids": []})

    _output({
        "episodes": episodes,
        "episode_count": len(episodes),
        "processed_guids_count": len(state.get("processed_guids", [])),
    })


def cmd_cleanup(args):
    root = _project_root(args)
    output_dir = root / "output" / "public" / "audio"

    removed = []
    if output_dir.exists():
        for orphan in output_dir.glob("*.part*.mp3"):
            try:
                orphan.unlink()
                removed.append(orphan.name)
            except OSError as e:
                removed.append(f"{orphan.name} (failed: {e})")

    _output({"removed": removed, "removed_count": len(removed)})


def cmd_get_config(args):
    cfg = load_json(_config_file(), {})
    _output(cfg)


def cmd_save_config(args):
    cfg = load_json(_config_file(), {})
    if args.podcast_repo_path:
        cfg["podcast_repo_path"] = str(Path(args.podcast_repo_path).resolve())
    if args.github_username:
        cfg["github_username"] = args.github_username
    _config_file().parent.mkdir(parents=True, exist_ok=True)
    save_json(_config_file(), cfg)
    _output(cfg)


# --- Argument parser ---


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="substack_audio.cli", description="Substack Audio CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # setup_check
    sub.add_parser("setup_check", help="Check plugin configuration status")

    # fetch_article
    p = sub.add_parser("fetch_article", help="Fetch a Substack article by URL")
    p.add_argument("url", help="Article URL")

    # generate_audio
    p = sub.add_parser("generate_audio", help="Generate audio from narrative text file")
    p.add_argument("--title", required=True, help="Episode title")
    p.add_argument("--pub-date", default="", help="Publication date (ISO format)")
    p.add_argument("--text-file", required=True, help="Path to narrative text file")
    p.add_argument("--project-root", help="Podcast repo path (where audio is saved)")

    # update_feed
    p = sub.add_parser("update_feed", help="Add episode to feed and update state")
    p.add_argument("--title", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--author", required=True)
    p.add_argument("--link", required=True)
    p.add_argument("--guid", required=True)
    p.add_argument("--pub-date-iso", required=True)
    p.add_argument("--audio-file", required=True)
    p.add_argument("--audio-url", required=True)
    p.add_argument("--audio-size-bytes", required=True, type=int)
    p.add_argument("--project-root", help="Podcast repo path")

    # list_episodes
    p = sub.add_parser("list_episodes", help="List all episodes")
    p.add_argument("--project-root", help="Podcast repo path")

    # cleanup
    p = sub.add_parser("cleanup", help="Remove orphaned .part*.mp3 files")
    p.add_argument("--project-root", help="Podcast repo path")

    # get_config
    sub.add_parser("get_config", help="Read persistent plugin config")

    # save_config
    p = sub.add_parser("save_config", help="Save persistent plugin config")
    p.add_argument("--podcast-repo-path", help="Path to user's podcast repo")
    p.add_argument("--github-username", help="GitHub username")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "setup_check": cmd_setup_check,
        "fetch_article": cmd_fetch_article,
        "generate_audio": cmd_generate_audio,
        "update_feed": cmd_update_feed,
        "list_episodes": cmd_list_episodes,
        "cleanup": cmd_cleanup,
        "get_config": cmd_get_config,
        "save_config": cmd_save_config,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        _output({"error": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    main()
