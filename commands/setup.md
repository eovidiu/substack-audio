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
- **Automate everything possible.** Run commands via Bash. Never tell the user to open a terminal.

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

### Step 2: Git identity and authentication check

Before creating or using any repo, verify who the user is and that git works:

```bash
# Show git identity
GIT_NAME="$(git config --global user.name)"
GIT_EMAIL="$(git config --global user.email)"
echo "Git user: $GIT_NAME <$GIT_EMAIL>"
```

Present this to the user: "I'll be using this git identity: **<name> \<<email>\>**. Is that correct?"

If git user/email is not set, ask for their name and email, then set it:
```bash
git config --global user.name "<name>"
git config --global user.email "<email>"
```

**Store the git name and email — they will be used later to pre-fill `.env` values.**

Check if `gh` CLI is available and authenticated:
```bash
which gh 2>/dev/null && gh auth status 2>&1
```

If `gh` is available, also grab the GitHub username for later:
```bash
GH_USER=$(gh api user --jq '.login')
echo "GitHub username: $GH_USER"
```

If `gh` is available but not authenticated, run `gh auth login` now — before proceeding.

If `gh` is not available, verify git can reach GitHub:
```bash
git ls-remote https://github.com/octocat/Hello-World.git HEAD 2>&1 | head -1
```

If auth fails, help fix it before continuing. **Do not proceed to repo creation with broken auth.**

### Step 3: Podcast repo setup

The user needs a git repo for their podcast data (episodes, feed, audio files). The `.env` config file will also live here. This is NOT the plugin repo.

Ask: "Do you have a GitHub repository set up for this podcast? If so, what's the local path?"

**If no — create one automatically via Bash:**

Ask the user for:
- A repo name (e.g., `my-podcast`)
- Where to create it locally (e.g., `~/work` — the repo will be `~/work/my-podcast`)

Use `gh` or plain `git` based on what was detected in Step 2.

**If `gh` is available (from Step 2):**

```bash
# Create the repo directory locally
mkdir -p <parent-dir>/<repo-name>
cd <parent-dir>/<repo-name>
git init

# Create required directories
mkdir -p data output/public/audio .github/workflows

# Copy GitHub Pages workflow from plugin
cp "$PLUGIN_DIR/.github/workflows/podcast.yml" .github/workflows/

# Initial commit
git add .github/workflows/podcast.yml
git commit -m "Add GitHub Pages deploy workflow"

# Create GitHub repo and push
gh repo create <repo-name> --public --source=. --push

# Enable GitHub Pages with GitHub Actions as the build source
gh api "repos/$GH_USER/<repo-name>/pages" -X POST -f "build_type=workflow" 2>/dev/null || echo "Pages may need manual setup at: https://github.com/$GH_USER/<repo-name>/settings/pages"
```

**If `gh` is NOT available — use plain git:**

Ask the user for their GitHub username, then:
```bash
# Create the repo directory locally
mkdir -p <parent-dir>/<repo-name>
cd <parent-dir>/<repo-name>
git init

# Create required directories
mkdir -p data output/public/audio .github/workflows

# Copy GitHub Pages workflow from plugin
cp "$PLUGIN_DIR/.github/workflows/podcast.yml" .github/workflows/

# Initial commit
git add .github/workflows/podcast.yml
git commit -m "Add GitHub Pages deploy workflow"
```

Then ask the user to create the repo on GitHub (https://github.com/new) and provide the repo URL. Once they do:
```bash
git remote add origin https://github.com/<username>/<repo-name>.git
git push -u origin main
```

Tell the user: "Go to your repo Settings > Pages > Source: GitHub Actions to enable GitHub Pages."

**If yes — use existing repo:**
- Ask for the local path to the repo
- Check for existing episodes:
  ```bash
  ls <podcast-repo>/data/episodes.json 2>/dev/null
  ls <podcast-repo>/output/public/feed.xml 2>/dev/null
  ```
- If found, say: "I found existing episodes. These will be preserved — new episodes are always appended."

**In both cases**, save the podcast repo path:
```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli save_config --podcast-repo-path "<podcast-repo-path>"
```

### Step 4: Collect podcast details and build .env

At this point you know:
- **GIT_NAME** (from Step 2) → use as default for `PODCAST_AUTHOR`
- **GIT_EMAIL** (from Step 2) → use as default for `PODCAST_EMAIL`
- **GH_USER** and **repo name** (from Steps 2-3) → compute `PUBLIC_BASE_URL=https://<GH_USER>.github.io/<repo-name>`

Ask the user the remaining questions. Present the inferred defaults and let them confirm or change:

1. **Podcast title** — "What should your podcast be called?" (no default)
2. **Podcast author** — "Author name?" (default: `GIT_NAME`)
3. **Podcast description** — "A sentence or two describing your podcast:" (no default)
4. **Substack/website URL** — "What's your Substack or website URL?" (no default, used for `PODCAST_LINK`)
5. **Contact email** — "Contact email for podcast directories?" (default: `GIT_EMAIL`)
6. **Cover image URL** — "URL to a square cover image (1400x1400 to 3000x3000)? Leave blank to skip for now." (optional)
7. **Voice model** — "Which ElevenLabs model?"
   - **eleven_v3** (default) — Latest v3, enhanced quality
   - **eleven_multilingual_v2** — Multilingual, good for non-English
   - **eleven_flash_v2_5** — Faster, slightly lower quality

Now write the `.env` file directly via Bash with all collected and inferred values:

```bash
cat > "<podcast-repo>/.env" << 'ENVEOF'
# ElevenLabs — edit these two values in a text editor:
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here
ELEVENLABS_MODEL_ID=<chosen model or eleven_v3>
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128
ELEVENLABS_TEXT_LIMIT=4500

# Podcast metadata
PODCAST_TITLE=<title>
PODCAST_AUTHOR=<author>
PODCAST_DESCRIPTION=<description>
PODCAST_LINK=<link>
PODCAST_EMAIL=<email>
PODCAST_LANGUAGE=en
PODCAST_IMAGE_URL=<image url or empty>

# Hosting
PUBLIC_BASE_URL=https://<GH_USER>.github.io/<repo-name>
ENVEOF
```

Add `.env` to the podcast repo's `.gitignore`:
```bash
grep -qxF '.env' "<podcast-repo>/.gitignore" 2>/dev/null || echo ".env" >> "<podcast-repo>/.gitignore"
```

### Step 5: Set API secrets (only manual step)

First, try to open the `.env` file directly in the user's default editor:
```bash
open "<podcast-repo>/.env"
```

Then tell the user, including the full file path and a clickable link:

> I've created your `.env` file with all the podcast settings pre-filled. There are just **two values** you need to set manually (I can't handle API keys in this chat).
>
> **File location:** `<podcast-repo>/.env`
> **Click to open:** [Open .env file](file://<podcast-repo>/.env)
>
> 1. Replace `your_key_here` with your ElevenLabs API key
>    - Get it at [elevenlabs.io](https://elevenlabs.io) > Profile > API Keys
> 2. Replace `your_voice_id_here` with your ElevenLabs Voice ID
>    - In ElevenLabs > Voices > pick a voice > copy the Voice ID
>    - Suggestions: "Rachel" (warm female) or "Adam" (deep male)
> 3. Save the file
>
> Let me know when you're done and I'll verify everything works.

### Step 6: Validate

After the user confirms they've set the secrets, run `setup_check`:

```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli setup_check
```

If `ready` is true:
"Setup complete! Run `/podcast-episode <url>` to create your first episode."

If something is still missing, show what's wrong and help fix it.
