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

All commands run via Bash. No MCP server, no connector.

```bash
# Find uv (sandbox PATH may not include it)
UV="$(command -v uv 2>/dev/null || echo /opt/homebrew/bin/uv)"
[ -x "$UV" ] || UV="$HOME/.local/bin/uv"
[ -x "$UV" ] || UV="$HOME/.cargo/bin/uv"

PLUGIN_DIR="<path to this directory>"
"$UV" run --directory "$PLUGIN_DIR" python -m substack_audio.cli <command> [args]
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

- Always verify git authentication is working before attempting to push (`git push --dry-run`).
- Use the user's existing git credentials on their machine.
- Never force-push. Never push to a branch other than what the user specifies.
- After pushing, verify the push succeeded before reporting success.
- Git operations happen in the **podcast repo**, not the plugin directory.
