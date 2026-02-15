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

## Sandbox Environment

Claude Desktop CoWorks runs inside an **Ubuntu 22.04 Linux VM** (not macOS).

- `python3`, `pip`, `git`, `curl`, `wget` are available out of the box
- `uv`, `gh`, `brew` are NOT pre-installed
- Only `gh` needs to be installed (for GitHub repo creation). Everything else uses built-in tools.
- Plugin cache is mounted **read-only**
- `open` command does not exist — use `file://` links and show paths instead
- No `sudo` access — install tools to `$HOME/.local/bin`

## How Commands Work

All plugin commands run via `python3` with `PYTHONPATH` set to the plugin directory.

```bash
# Find the plugin directory (where pyproject.toml lives)
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"

# Run any CLI command
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli <command> [args]
```

Store `PLUGIN_DIR` at the start and reuse it throughout.

## Workflow

### Step 1: Find plugin and install Python dependencies

Locate the plugin directory:
```bash
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"
echo "Plugin directory: $PLUGIN_DIR"
```

If not found via `/`, also try:
```bash
find "$HOME" /sessions /mnt -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1
```

Install Python dependencies (uses pip, no uv needed):
```bash
python3 -m pip install --user -r "$PLUGIN_DIR/requirements.txt" 2>&1 | tail -3
```

Test that the plugin loads:
```bash
PYTHONPATH="$PLUGIN_DIR" python3 -c "import substack_audio; print('ok')"
```

### Step 2: Git identity and GitHub authentication

**Two separate things are needed and they are NOT the same:**
- **Git identity** = display name for commits (e.g. "Ovidiu")
- **GitHub username** = the actual GitHub account login (e.g. "eovidiu")

**You MUST resolve both separately. NEVER use the git display name as the GitHub username.**

#### 2a. Git commit identity

```bash
GIT_NAME="$(git config --global user.name)"
GIT_EMAIL="$(git config --global user.email)"
echo "Git identity: $GIT_NAME <$GIT_EMAIL>"
```

Present: "I'll use this git identity for commits: **<name> \<<email>\>**. Is that correct?"

If not set, ask for their name and email:
```bash
git config --global user.name "<name>"
git config --global user.email "<email>"
```

**GIT_NAME and GIT_EMAIL are only used for: commit authorship, PODCAST_AUTHOR default, PODCAST_EMAIL default. NEVER for repo URLs.**

#### 2b. Install gh and authenticate with GitHub

Install `gh` CLI (single binary, no package manager needed):
```bash
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$HOME/.local/bin"
command -v gh 2>/dev/null && echo "gh found" || {
  GH_VERSION="2.67.0"
  ARCH="$(uname -m)"
  [ "$ARCH" = "aarch64" ] && ARCH="arm64"
  [ "$ARCH" = "x86_64" ] && ARCH="amd64"
  curl -LsSf "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${ARCH}.tar.gz" | tar xz -C /tmp
  cp /tmp/gh_${GH_VERSION}_linux_${ARCH}/bin/gh "$HOME/.local/bin/gh"
  chmod +x "$HOME/.local/bin/gh"
  gh --version
}
```

Tell the user before starting auth:

> To connect to GitHub, you'll need to open a link in your browser and enter a one-time code. This is a one-time step.

Check if already authenticated:
```bash
gh auth status 2>&1
```

If not authenticated, start the device code flow:
```bash
gh auth login --hostname github.com --git-protocol https --web
```

This prints a URL (https://github.com/login/device) and a code. Present both clearly and wait for the user to confirm they've authorized.

If `--web` fails, fall back to token-based auth:
```bash
gh auth login --hostname github.com --git-protocol https --with-token
```
Tell the user: "Create a token at https://github.com/settings/tokens/new with scopes: `repo`, `read:org`, `workflow`."

#### 2c. Get GitHub username — MANDATORY STEP

**This step is MANDATORY. Do NOT skip it. Do NOT proceed without it.**

After the user confirms they've authorized, run:
```bash
GH_USER=$(gh api user --jq '.login')
echo "GitHub username: $GH_USER"
```

Present to the user: "Your GitHub account is **<GH_USER>**. Repos will be created under github.com/**<GH_USER>**/. Is that correct?"

**Wait for confirmation before proceeding.**

**REMEMBER: GH_USER (e.g. "eovidiu") ≠ GIT_NAME (e.g. "Ovidiu"). For the rest of this setup, use GH_USER for all GitHub URLs, repo names, and Pages URLs. Use GIT_NAME only for podcast author name.**

### Step 3: Podcast repo setup

The user needs a git repo for their podcast data (episodes, feed, audio files). The `.env` config file will also live here. This is NOT the plugin repo.

Ask: "Do you have a GitHub repository set up for this podcast? If so, what's the local path?"

**If no — create one:**

Ask the user for:
- A repo name (e.g., `my-podcast`)
- Where to create it locally (e.g., `~/work` — the repo will be `~/work/my-podcast`)

Then present a summary and **ask for confirmation before executing**:

> I'm going to:
> 1. Create a local directory at `<parent-dir>/<repo-name>`
> 2. Initialize a git repo with the GitHub Pages deploy workflow
> 3. Create a public GitHub repo `<GH_USER>/<repo-name>` (using GitHub username **<GH_USER>**, not "<GIT_NAME>")
> 4. Push the initial commit
> 5. Enable GitHub Pages
>
> Ready to proceed?

**Only after the user confirms**, execute via Bash:

```bash
mkdir -p <parent-dir>/<repo-name>
cd <parent-dir>/<repo-name>
git init

mkdir -p data output/public/audio .github/workflows

cp "$PLUGIN_DIR/.github/workflows/podcast.yml" .github/workflows/

git add .github/workflows/podcast.yml
git commit -m "Add GitHub Pages deploy workflow"

gh repo create <repo-name> --public --source=. --push

gh api "repos/$GH_USER/<repo-name>/pages" -X POST -f "build_type=workflow" 2>/dev/null || echo "Pages may need manual setup at: https://github.com/$GH_USER/<repo-name>/settings/pages"
```

Verify:
```bash
git log --oneline -1
gh repo view $GH_USER/<repo-name> --json url --jq '.url'
```

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
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli save_config --podcast-repo-path "<podcast-repo-path>"
```

### Step 4: Collect podcast details and build .env

At this point you have:
- **GIT_NAME** (display name from Step 2a, e.g. "Ovidiu") → default for `PODCAST_AUTHOR`
- **GIT_EMAIL** (from Step 2a) → default for `PODCAST_EMAIL`
- **GH_USER** (GitHub login from Step 2c, e.g. "eovidiu") → used in `PUBLIC_BASE_URL`
- **repo name** (from Step 3) → used in `PUBLIC_BASE_URL`

**IMPORTANT: GH_USER and GIT_NAME are different. Use GH_USER for PUBLIC_BASE_URL, never GIT_NAME.**

`PUBLIC_BASE_URL=https://<GH_USER>.github.io/<repo-name>`

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

### Step 5: Write CLAUDE.md in the podcast repo

Write a `CLAUDE.md` file in the podcast repo so that every future conversation opened in this folder has full context. Use the values collected in previous steps:

```bash
cat > "<podcast-repo>/CLAUDE.md" << 'CLAUDEEOF'
# Podcast Project — Context for Claude

## Environment

- **Plugin directory:** <PLUGIN_DIR>
- **Podcast repo:** <podcast-repo>
- **GitHub username:** <GH_USER>
- **Git identity:** <GIT_NAME> <<GIT_EMAIL>>

## Setup (run once per session if deps are missing)

```
python3 -m pip install --user -r "<PLUGIN_DIR>/requirements.txt"
```

## CLI Commands

All commands use the plugin's CLI via Bash:

```
PYTHONPATH="<PLUGIN_DIR>" python3 -m substack_audio.cli <command> [args]
```

Available commands:
- `setup_check` — Check if all required config is set
- `fetch_article <url>` — Fetch a Substack article
- `generate_audio --title "..." --pub-date "..." --text-file /path --project-root "<podcast-repo>"` — Generate MP3
- `update_feed --title "..." --description "..." --author "..." --link "..." --guid "..." --pub-date-iso "..." --audio-file "..." --audio-url "..." --audio-size-bytes N --project-root "<podcast-repo>"` — Add episode to feed
- `list_episodes --project-root "<podcast-repo>"` — List all episodes
- `cleanup --project-root "<podcast-repo>"` — Remove orphaned .part*.mp3 files
- `get_config` — Read persistent plugin config
- `save_config` — Save persistent config

## Podcast Configuration

- **Title:** <PODCAST_TITLE>
- **Author:** <PODCAST_AUTHOR>
- **Description:** <PODCAST_DESCRIPTION>
- **Website:** <PODCAST_LINK>
- **Email:** <PODCAST_EMAIL>
- **Cover image:** <PODCAST_IMAGE_URL or "not set">
- **Public URL:** https://<GH_USER>.github.io/<repo-name>
- **Voice model:** <ELEVENLABS_MODEL_ID>

## Critical Rules

- **NEVER delete or reorder existing episodes** in episodes.json or feed.xml. Append only.
- **NEVER ask the user to paste API keys** into the chat. Secrets live in `.env`.
- **NEVER clone or pull the plugin code repo.** Plugin code is at the path above.
- Git operations happen in THIS repo, not the plugin directory.
- Always use `--project-root "<podcast-repo>"` for data commands.
CLAUDEEOF
```

This file is safe to commit — it contains no secrets (API keys stay in `.env`).

### Step 6: Set API secrets (only manual step)

Tell the user, including the full file path and a clickable link:

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

### Step 7: Validate

After the user confirms they've set the secrets, run `setup_check`:

```bash
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli setup_check
```

If `ready` is true:
"Setup complete! Run `/podcast-episode <url>` to create your first episode."

If something is still missing, show what's wrong and help fix it.
