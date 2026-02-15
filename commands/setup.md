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

## Important: Secret Handling

**NEVER ask the user to paste API keys or secrets into this chat.** The LLM must not see credentials.

Instead, direct the user to set secrets in one of these places:
1. **Connector env vars** in Claude Desktop (Plugins > Substack audio > Connectors > Edit)
2. **A `.env` file** that they edit themselves in a text editor

When a secret is needed, tell the user exactly which field to set and where, but do NOT ask them to type the value here.

## Workflow

### Step 1: Check current state
Call the `setup_check` MCP tool to see what's configured and what's missing.

If `ready` is true and `warnings` is empty, tell the user: "You're all set! Run `/podcast-episode <url>` to create an episode."

If `ready` is true but there are warnings, show the recommended settings that are still empty. Ask if they want to set them now or skip.

If `ready` is false, proceed to Step 2.

### Step 2: Required secrets (user sets these outside the chat)

For secrets, do NOT collect values. Instead, give the user clear instructions:

**ELEVENLABS_API_KEY**:
Tell the user:
> Go to [elevenlabs.io](https://elevenlabs.io) > Profile (bottom-left) > API Keys > Copy your key.
> Then paste it into your **Connector settings** (Plugins > Substack audio > Connectors > Edit > Environment Variables > `ELEVENLABS_API_KEY`).

**ELEVENLABS_VOICE_ID**:
Tell the user:
> In ElevenLabs, go to Voices, pick a voice, and copy the Voice ID from the URL or settings panel.
> Suggestions: "Rachel" (warm, professional female) or "Adam" (deep male).
> Paste the Voice ID into your **Connector settings** under `ELEVENLABS_VOICE_ID`.

After giving instructions, ask the user to confirm when they've set both values, then re-run `setup_check` to verify.

### Step 3: Voice model selection

Ask the user which ElevenLabs model they want to use:
- **eleven_v3_conversational** (default) — Latest v3 model with enhanced quality
- **eleven_multilingual_v2** — Proven multilingual model, good for non-English content
- **eleven_flash_v2_5** — Faster generation, slightly lower quality

If they pick something other than the default, tell them to update `ELEVENLABS_MODEL_ID` in the Connector env vars.

### Step 4: Non-secret configuration

These values are safe to collect in the chat. Ask the user for each:

**PUBLIC_BASE_URL**:
- This is where podcast files will be hosted
- Easiest option: GitHub Pages
- Steps: Create a GitHub repo, enable Pages (Settings > Pages > Source: GitHub Actions)
- The URL will be `https://<username>.github.io/<repo-name>`
- The repo needs the `.github/workflows/podcast.yml` workflow from this plugin

**PODCAST_TITLE**: Name of the podcast (shows in Spotify, Apple Podcasts, etc.)
**PODCAST_AUTHOR**: Your name or pen name
**PODCAST_DESCRIPTION**: A sentence or two describing the podcast
**PODCAST_LINK**: URL to your Substack or website
**PODCAST_EMAIL**: Contact email for podcast directories
**PODCAST_IMAGE_URL**: URL to a square cover image (1400x1400 to 3000x3000 pixels). Can be hosted anywhere.

For each value the user provides, tell them to set it in the Connector env vars. The plugin reads all config from environment variables — no `.env` file is needed if the Connector is configured.

### Step 5: Git setup

Ask the user:
1. "Do you have a GitHub repository set up for this podcast?"
2. "Is git authentication configured on this machine? (e.g., can you push to GitHub?)"

If they have a repo:
- Ask for the repo URL (e.g., `https://github.com/username/repo`)
- Check if the repo has existing episodes by looking for `data/episodes.json` and `output/public/feed.xml`
- If it does, warn: "I found existing episodes. These will be preserved — new episodes are always appended, never replacing existing ones."

If git auth is not configured, walk them through:
```
gh auth login
```
Or suggest setting up a GitHub personal access token.

### Step 6: Initialize directories

Create the required directories if they don't exist:
```bash
mkdir -p data output/public/audio
```

### Step 7: Validate

Call `setup_check` again to confirm everything is set. If ready, tell the user:
"Setup complete! Run `/podcast-episode <url>` to create your first episode."

If something is still missing, show what's wrong and help fix it.
