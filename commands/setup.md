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
- **Automate everything possible.** Run commands via Bash.

## Sandbox Environment

Claude Desktop CoWorks runs inside an **Ubuntu 22.04 Linux VM** (not macOS).

- `python3`, `pip`, `git`, `curl`, `wget` are available out of the box
- No tools need to be installed. Everything uses built-in system tools.
- Plugin cache is mounted **read-only**
- `open` command does not exist — use `file://` links and show paths instead
- No `sudo` access
- **The VM has NO SSH keys.** Git push uses HTTPS with a GitHub Personal Access Token stored in `.env`.
- **Shell variables do NOT persist between Bash tool calls.** Each Bash call is a new shell. Always re-discover `PLUGIN_DIR` in each Bash call or combine dependent commands into a single call.

## How Commands Work

All plugin commands run via `python3` with `PYTHONPATH` set to the plugin directory.

```bash
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli <command> [args]
```

## Workflow

### Step 1: Find plugin and install Python dependencies

Find plugin and install deps in a **single Bash call**:

```bash
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"
echo "Plugin directory: $PLUGIN_DIR"
python3 -m pip install --user -r "$PLUGIN_DIR/requirements.txt" 2>&1 | tail -5
PYTHONPATH="$PLUGIN_DIR" python3 -c "import substack_audio; print('ok')"
```

If `find /` is too slow, try narrower paths first:
```bash
find "$HOME" /sessions /mnt -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1
```

### Step 2: Git identity and GitHub username

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

#### 2b. GitHub username

Ask the user: "What's your GitHub username? (This is your login, e.g. 'eovidiu', not your display name)"

Store this as `GH_USER`.

**REMEMBER: GH_USER (e.g. "eovidiu") ≠ GIT_NAME (e.g. "Ovidiu"). Use GH_USER for all GitHub URLs and Pages URLs. Use GIT_NAME only for podcast author name.**

### Step 3: Podcast repo setup

The user needs a GitHub repo for their podcast data. This is NOT the plugin repo.

**Ask two things:**

1. "Do you have a GitHub repository set up for this podcast? If so, what's the repo name on GitHub?"
2. "Where on your Mac do you want the podcast folder? Give me the full path (e.g. `/Users/you/work/my-podcast`)."

Store the user's chosen path as `PODCAST_DIR`.

**If no repo — create one:**

Ask the user for a repo name (e.g., `my-podcast`).

Tell the user:

> Please create a new **public** repository called **<repo-name>** on GitHub:
> https://github.com/new
>
> **Check "Add a README file"** so the repo is initialized. Let me know when it's created.

**Wait for the user to confirm.**

**If yes — use existing repo:**

Just get the repo name (e.g., `my-podcast`).

**In both cases**, clone into the user-chosen folder and scaffold:

```bash
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"

# Clone into user-chosen location (parent must exist)
PODCAST_DIR="<user-chosen-path>"
mkdir -p "$(dirname "$PODCAST_DIR")"
git clone https://github.com/<GH_USER>/<repo-name>.git "$PODCAST_DIR"
cd "$PODCAST_DIR"

mkdir -p data output/public/audio .github/workflows

cp "$PLUGIN_DIR/.github/workflows/podcast.yml" .github/workflows/

# Placeholder so the Pages deploy workflow triggers on first push
echo '<html><body><p>Podcast coming soon.</p></body></html>' > output/public/index.html

git add .
git commit -m "Initial setup: GitHub Pages deploy workflow"

echo "Repo ready at: $PODCAST_DIR"
```

**The scaffolded folder is on the user's Mac.** They can open it in Finder, edit `.env` there, etc.

Check for existing episodes (for existing repos):
```bash
ls "<PODCAST_DIR>/data/episodes.json" 2>/dev/null && echo "Found existing episodes — they will be preserved."
```

Save the podcast repo path:
```bash
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli save_config --podcast-repo-path "<PODCAST_DIR>"
```

### Step 4: Collect podcast details and build .env

At this point you have:
- **GIT_NAME** (display name from Step 2a, e.g. "Ovidiu") → default for `PODCAST_AUTHOR`
- **GIT_EMAIL** (from Step 2a) → default for `PODCAST_EMAIL`
- **GH_USER** (GitHub login from Step 2b, e.g. "eovidiu") → used in `PUBLIC_BASE_URL`
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

Write the `.env` file:

```bash
cat > "<PODCAST_DIR>/.env" << 'ENVEOF'
# ElevenLabs — edit these two values:
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

# GitHub — needed to push from this VM:
GITHUB_TOKEN=your_github_token_here
ENVEOF
```

Add `.env` to `.gitignore` and commit:
```bash
cd "<PODCAST_DIR>"
grep -qxF '.env' .gitignore 2>/dev/null || echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .gitignore"
```

### Step 5: Write CLAUDE.md in the podcast repo

Write a `CLAUDE.md` with full project context, then commit:

```bash
cat > "<PODCAST_DIR>/CLAUDE.md" << 'CLAUDEEOF'
# Podcast Project — Context for Claude

## Environment

- **Podcast repo:** <PODCAST_DIR>
- **GitHub username:** <GH_USER>
- **Git identity:** <GIT_NAME> <<GIT_EMAIL>>

## Setup (run once per session if deps are missing)

```
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"
python3 -m pip install --user -r "$PLUGIN_DIR/requirements.txt"
```

## CLI Commands

```
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli <command> [args]
```

Available commands:
- `setup_check` — Check if all required config is set
- `fetch_article <url>` — Fetch a Substack article
- `generate_audio --title "..." --pub-date "..." --text-file /path --project-root "<PODCAST_DIR>"` — Generate MP3
- `update_feed --title "..." --description "..." --author "..." --link "..." --guid "..." --pub-date-iso "..." --audio-file "..." --audio-url "..." --audio-size-bytes N --project-root "<PODCAST_DIR>"` — Add episode to feed
- `list_episodes --project-root "<PODCAST_DIR>"` — List all episodes
- `cleanup --project-root "<PODCAST_DIR>"` — Remove orphaned .part*.mp3 files
- `get_config` / `save_config` — Persistent plugin config

## Git Push

Push via HTTPS using `GITHUB_TOKEN` from `.env`. The push command temporarily sets the token in the remote URL, pushes, then resets it. Never persist the token in `.git/config`.

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

- **NEVER delete or reorder existing episodes.** Append only.
- **NEVER ask the user to paste API keys.** Secrets live in `.env`.
- **NEVER clone or pull the plugin code repo.**
- Always use `--project-root "<PODCAST_DIR>"` for data commands.
CLAUDEEOF
```

```bash
cd "<PODCAST_DIR>"
git add CLAUDE.md
git commit -m "Add CLAUDE.md with project context"
```

### Step 6: Set API secrets

Tell the user:

> I've created your `.env` file with all the podcast settings pre-filled. There are **three values** you need to set manually (I can't handle API keys in this chat).
>
> **File location:** `<PODCAST_DIR>/.env`
> **Click to open:** [Open .env file](file://<PODCAST_DIR>/.env)
>
> 1. Replace `your_key_here` with your ElevenLabs API key
>    - Get it at [elevenlabs.io](https://elevenlabs.io) > Profile > API Keys
> 2. Replace `your_voice_id_here` with your ElevenLabs Voice ID
>    - In ElevenLabs > Voices > pick a voice > copy the Voice ID
>    - Suggestions: "Rachel" (warm female) or "Adam" (deep male)
> 3. Replace `your_github_token_here` with a GitHub Personal Access Token
>    - Go to [github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta) > **Generate new token**
>    - Token name: anything (e.g. "podcast-plugin")
>    - Repository access: **Only select repositories** → pick your podcast repo
>    - Permissions: **Contents → Read and write**
>    - That's it — no other permissions needed
>    - Copy the token and paste it in `.env`
> 4. Save the file
>
> Let me know when you're done and I'll verify everything works.

### Step 7: Validate and push

After the user confirms secrets are set, run `setup_check`:

```bash
PLUGIN_DIR="$(find / -path "*/substack-audio/pyproject.toml" -maxdepth 8 2>/dev/null | head -1 | xargs dirname)"
PYTHONPATH="$PLUGIN_DIR" python3 -m substack_audio.cli setup_check
```

If `ready` is true, configure the git remote with the GitHub token and push:

```bash
cd "<PODCAST_DIR>"

# Read token from .env (never echo it)
GITHUB_TOKEN="$(grep '^GITHUB_TOKEN=' .env | cut -d= -f2-)"
GH_USER="<GH_USER>"
REPO_NAME="<repo-name>"

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "your_github_token_here" ]; then
  echo "ERROR: GITHUB_TOKEN not set in .env. Please add your GitHub Personal Access Token."
  exit 1
fi

# Set remote URL with token for HTTPS push (token is in .env, not in git config)
git remote set-url origin "https://${GITHUB_TOKEN}@github.com/${GH_USER}/${REPO_NAME}.git"

# Push all local commits
git push -u origin main

# Reset remote URL to remove token from git config (security: don't persist token in .git/config)
git remote set-url origin "https://github.com/${GH_USER}/${REPO_NAME}.git"

echo "Pushed successfully!"
```

After push succeeds:

> Setup complete! Your podcast repo is at **<PODCAST_DIR>** and has been pushed to GitHub.
>
> **Your podcast will be live at:**
> **https://<GH_USER>.github.io/<repo-name>/**
>
> GitHub Pages auto-enables when the workflow runs (may take 1-2 minutes after the first push).
>
> Run `/podcast-episode <url>` to create your first episode!

If `setup_check` shows something missing, help fix it before pushing.
