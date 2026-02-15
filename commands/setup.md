---
description: Configure the Substack Audio plugin for first use
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - mcp__substack-audio__setup_check
---

# Substack Audio Setup

Guide the user through configuring this plugin so they can generate podcast episodes.

## Workflow

### Step 1: Check current state
Call the `setup_check` MCP tool to see what's configured and what's missing.

If `ready` is true and `warnings` is empty, tell the user: "You're all set! Run `/podcast-episode <url>` to create an episode."

If `ready` is true but there are warnings, show the recommended settings that are still empty. Ask if they want to set them now or skip.

If `ready` is false, proceed to Step 2.

### Step 2: Walk through missing required values

For each item in `missing`, explain what it is, where to get it, and ask the user for the value.

**ELEVENLABS_API_KEY**:
- Sign up at [elevenlabs.io](https://elevenlabs.io)
- Go to your Profile (bottom-left) > API Keys
- Copy the API key

**ELEVENLABS_VOICE_ID**:
- In ElevenLabs, go to the Voices section
- Pick a voice you like (or clone your own)
- The Voice ID is in the URL or the voice settings panel
- Suggest: "Rachel" for a warm, professional female voice, or "Adam" for a deep male voice

**PUBLIC_BASE_URL**:
- This is where the podcast files will be hosted
- Easiest option: GitHub Pages
- Steps: Create a GitHub repo, enable Pages (Settings > Pages > Source: GitHub Actions)
- The URL will be `https://<username>.github.io/<repo-name>`
- The repo needs the `.github/workflows/podcast.yml` workflow from this plugin

### Step 3: Walk through recommended values

For each item in `warnings`, explain what it does and ask for a value:

- **PODCAST_TITLE**: Name of the podcast (shows in Spotify, Apple Podcasts, etc.)
- **PODCAST_AUTHOR**: Your name or pen name
- **PODCAST_DESCRIPTION**: A sentence or two describing the podcast
- **PODCAST_LINK**: URL to your Substack or website
- **PODCAST_EMAIL**: Contact email for podcast directories
- **PODCAST_IMAGE_URL**: URL to a square cover image (1400x1400 to 3000x3000 pixels). Can be hosted anywhere — Substack profile image works.

### Step 4: Create the .env file

Once all values are collected, create a `.env` file in the working directory:

```
ELEVENLABS_API_KEY=<value>
ELEVENLABS_VOICE_ID=<value>
PUBLIC_BASE_URL=<value>
PODCAST_TITLE=<value>
PODCAST_AUTHOR=<value>
PODCAST_DESCRIPTION=<value>
PODCAST_LINK=<value>
PODCAST_EMAIL=<value>
PODCAST_IMAGE_URL=<value>
```

**Important**: If a `.env` file already exists, read it first and merge — don't overwrite existing values unless the user explicitly provides new ones.

### Step 5: Verify the connector

Remind the user to check their connector settings in Claude Desktop:
- The `--directory` argument should point to their working directory (where the `.env` file lives)
- The `PROJECT_ROOT` env var should be set to the same path
- If they haven't done this yet, walk them through it

### Step 6: Initialize directories

Create the required directories if they don't exist:
```bash
mkdir -p data output/public/audio
```

### Step 7: Validate

Call `setup_check` again to confirm everything is set. If ready, tell the user:
"Setup complete! Run `/podcast-episode <url>` to create your first episode."

If something is still missing, show what's wrong and help fix it.
