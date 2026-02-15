---
description: Configure the Substack Audio plugin for first use
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# Substack Audio Setup

Guide the user through configuring this plugin so they can generate podcast episodes.

## Critical Rules

- **NEVER ask the user to paste API keys or secrets into this chat.** Direct them to edit their `.env` file in a text editor.
- **NEVER clone or pull the plugin's code repo.** The plugin ships as a zip — all code is already here.
- **The plugin directory is READ-ONLY.** Never write files there. All user data (including `.env`) lives in the **podcast repo**.

## How Commands Work

All plugin commands run via Bash. The plugin directory is the parent of the `substack_audio/` package.

```bash
# Find the plugin directory (where pyproject.toml lives)
PLUGIN_DIR="$(dirname "$(find ~ -path "*/substack-audio/pyproject.toml" -maxdepth 6 2>/dev/null | head -1)")"

# Run any CLI command
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli <command> [args]
```

## Workflow

### Step 1: Find plugin directory and install dependencies

Locate the plugin and ensure dependencies are installed:

```bash
PLUGIN_DIR="$(dirname "$(find ~ -path "*/substack-audio/pyproject.toml" -maxdepth 6 2>/dev/null | head -1)")"
echo "Plugin directory: $PLUGIN_DIR"
```

If not found, check common Claude Desktop plugin cache paths:
```bash
ls ~/Library/Application\ Support/Claude/plugins/*/substack-audio/pyproject.toml 2>/dev/null
```

Install dependencies:
```bash
uv sync --directory "$PLUGIN_DIR"
```

Test:
```bash
uv run --directory "$PLUGIN_DIR" python -c "import substack_audio; print('ok')"
```

### Step 2: Podcast repo setup (do this BEFORE secrets)

The user needs a git repo for their podcast data (episodes, feed, audio files). The `.env` config file will also live here. This is NOT the plugin repo.

Ask: "Do you have a GitHub repository set up for this podcast? If so, what's the local path?"

**If no — create one:**
```bash
gh repo create <repo-name> --public --clone
cd <repo-name>
mkdir -p data output/public/audio .github/workflows
```

Copy the GitHub Pages workflow from the plugin:
```bash
cp "$PLUGIN_DIR/.github/workflows/podcast.yml" .github/workflows/
```

Enable GitHub Pages: tell the user to go to repo Settings > Pages > Source: GitHub Actions.

Initial commit:
```bash
git add .github/workflows/podcast.yml
git commit -m "Add GitHub Pages deploy workflow"
git push origin main
```

**If yes:**
- Ask for the local path to the repo
- Check for existing episodes:
  ```bash
  ls <podcast-repo>/data/episodes.json 2>/dev/null
  ls <podcast-repo>/output/public/feed.xml 2>/dev/null
  ```
- If found, say: "I found existing episodes. These will be preserved — new episodes are always appended."

Save the podcast repo path so future commands know where to find data and `.env`:
```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli save_config --podcast-repo-path "<podcast-repo-path>"
```

### Step 3: Create .env in the podcast repo

Copy the example `.env` to the podcast repo:
```bash
cp "$PLUGIN_DIR/.env.example" "<podcast-repo>/.env"
```

Add `.env` to the podcast repo's `.gitignore` (secrets must never be committed):
```bash
echo ".env" >> "<podcast-repo>/.gitignore"
```

Tell the user: "I've created a `.env` file in your podcast repo. You'll need to open it in a text editor to fill in your API keys. Let me tell you which values to set."

### Step 4: Required secrets (user edits .env themselves)

For secrets, do NOT collect values. Instead, give the user clear instructions:

**ELEVENLABS_API_KEY**:
> Go to [elevenlabs.io](https://elevenlabs.io) > Profile (bottom-left) > API Keys > Copy your key.
> Open `<podcast-repo>/.env` in a text editor and set `ELEVENLABS_API_KEY=your-key-here`.

**ELEVENLABS_VOICE_ID**:
> In ElevenLabs, go to Voices, pick a voice, and copy the Voice ID from the URL or settings panel.
> Suggestions: "Rachel" (warm, professional female) or "Adam" (deep male).
> Set `ELEVENLABS_VOICE_ID=your-voice-id` in the same `.env` file.

After the user confirms they've set both values, re-run `setup_check` to verify:
```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli setup_check
```

### Step 5: Voice model selection

Ask the user which ElevenLabs model they want to use:
- **eleven_v3_conversational** (default) — Latest v3 model with enhanced quality
- **eleven_multilingual_v2** — Proven multilingual model, good for non-English content
- **eleven_flash_v2_5** — Faster generation, slightly lower quality

If they pick something other than the default, tell them to update `ELEVENLABS_MODEL_ID` in `<podcast-repo>/.env`.

### Step 6: Non-secret configuration

These values are safe to collect in the chat. For each value the user provides, tell them to add it to `<podcast-repo>/.env`:

**PUBLIC_BASE_URL**:
- This is where podcast files will be hosted
- Easiest option: GitHub Pages
- The URL will be `https://<username>.github.io/<repo-name>`

**PODCAST_TITLE**: Name of the podcast (shows in Spotify, Apple Podcasts, etc.)
**PODCAST_AUTHOR**: Your name or pen name
**PODCAST_DESCRIPTION**: A sentence or two describing the podcast
**PODCAST_LINK**: URL to your Substack or website
**PODCAST_EMAIL**: Contact email for podcast directories
**PODCAST_IMAGE_URL**: URL to a square cover image (1400x1400 to 3000x3000 pixels)

### Step 7: Git auth check

Verify git can push from this machine:
```bash
git -C "<podcast-repo>" push --dry-run origin main 2>&1
```

If it fails, help the user fix auth:
```bash
which gh && gh auth status
```

If `gh` is available but not logged in: `gh auth login`

### Step 8: Validate

Run `setup_check` one final time:
```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli setup_check
```

If ready, tell the user:
"Setup complete! Run `/podcast-episode <url>` to create your first episode."

If something is still missing, show what's wrong and help fix it.
