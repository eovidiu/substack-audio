# Substack Audio Plugin — Directives

These rules are mandatory for all sessions using this plugin.

## Two-Repo Architecture

This plugin uses two separate repositories:

1. **Plugin code** (this directory) — ships as a zip, lives in the Claude Desktop plugin cache. READ-ONLY.
2. **Podcast repo** (user's own repo) — where episodes, feed, and audio files live. This is what gets pushed to GitHub Pages.

**NEVER clone or pull the plugin's code repo.** All code is already available in the plugin cache.

**NEVER write user data to the plugin directory.** Episodes, feed, and audio go to the podcast repo.

The podcast repo path is stored in `data/config.json` in the plugin directory (via `save_config`/`get_config`).

## CLI Commands

All commands run via Bash using `python3` with `PYTHONPATH`. No `uv`, no MCP server, no connector.

```bash
PLUGIN_DIR="<path to this directory>"
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli <command> [args]
```

If dependencies are missing, install them first:
```bash
python3 -m pip install --user -r "$PLUGIN_DIR/requirements.txt"
```

Available commands:
- `setup_check` — Check if all required config is set
- `fetch_article <url>` — Fetch a Substack article
- `generate_audio --title "..." --pub-date "..." --text-file /path/to/text [--project-root <podcast-repo>]` — Generate MP3 via ElevenLabs
- `update_feed --title "..." --description "..." --author "..." --link "..." --guid "..." --pub-date-iso "..." --audio-file "..." --audio-url "..." --audio-size-bytes N [--project-root <podcast-repo>]` — Add episode to feed
- `list_episodes [--project-root <podcast-repo>]` — List all episodes
- `cleanup [--project-root <podcast-repo>]` — Remove orphaned .part*.mp3 files
- `get_config` — Read persistent plugin config
- `save_config [--podcast-repo-path "..."] [--github-username "..."]` — Save persistent config

Use `--project-root` to point data commands at the user's podcast repo.

## Feed Integrity

**NEVER delete, reorder, or modify existing episodes in `episodes.json` or `feed.xml`.**

- New episodes are **appended only**. Existing entries must not be touched.
- When rebuilding `feed.xml`, all existing episodes must appear with their original data intact.
- The only allowed modification to an existing episode is re-generating its audio (same GUID), which replaces that single entry in-place.
- If `episodes.json` or `feed.xml` already exist in the user's repository, load and preserve them before adding anything.

Violating this rule breaks podcast subscribers' feeds and can cause episodes to disappear from Spotify/Apple Podcasts.

## Secret Handling

**NEVER ask the user to type API keys, tokens, or passwords into the chat.**

- Direct users to set secrets in the `.env` file **in their podcast repo** (not the plugin directory, which is read-only).
- If a secret is missing, explain where to set it — do not prompt for the value.
- The CLI loads `.env` from the podcast repo path stored in `data/config.json`.

## Git Operations

- Push via HTTPS using `GITHUB_TOKEN` from `.env`. Temporarily set token in remote URL, push, then reset URL.
- Never persist the token in `.git/config`.
- Never force-push. Never push to a branch other than what the user specifies.
- After pushing, verify the push succeeded before reporting success.
- Git operations happen in the **podcast repo**, not the plugin directory.
