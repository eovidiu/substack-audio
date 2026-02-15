---
description: Convert a Substack article URL into a full podcast episode
argument-hint: <substack-article-url>
allowed-tools:
  - Read
  - Bash
  - Glob
  - mcp__substack-audio__setup_check
  - mcp__substack-audio__fetch_article
  - mcp__substack-audio__generate_audio
  - mcp__substack-audio__update_feed
  - mcp__substack-audio__list_episodes
  - mcp__substack-audio__cleanup
---

# Podcast Episode Creator

Create a podcast episode from: $ARGUMENTS

## Workflow

### Step 0: Pre-flight check
Call the `setup_check` MCP tool. If `ready` is false, show the user what's missing with the setup instructions and **stop** — do not proceed until the configuration is complete. Suggest running `/setup` for a guided walkthrough.

If `warnings` is non-empty, mention the recommended settings but continue.

### Step 1: Fetch the article
Use the `fetch_article` MCP tool with the provided URL. Display the article title, author, word count.

### Step 2: Check for duplicates
Use `list_episodes` to check if this article (by URL/guid) has already been processed. If it has, warn and ask whether to regenerate.

### Step 3: Create the narrative
Using the **narrative-writer** skill, create a condensed 10-12 minute audio narrative from the article text. The narrative must:
- Be 1500-1800 words (proportionally shorter for short articles)
- Address the listener directly
- Capture core ideas with concrete examples
- Open with a hook, close with resonance

**Present the full narrative text to the user for review. Do NOT proceed until the user approves it.**

### Step 4: Generate audio
After narrative approval, use `generate_audio` with:
- `text`: the approved narrative
- `title`: the article title
- `pub_date`: the article's publication date

This calls ElevenLabs and costs API credits. The tool will return the audio file path, URL, and size.

### Step 5: Update the feed
Use `update_feed` with:
- `title`: article title
- `description`: first ~250 chars of the narrative
- `author`: article author
- `link`: original article URL
- `guid`: the article URL (as unique identifier)
- `pub_date_iso`: article publication date in ISO format
- `audio_file`, `audio_url`, `audio_size_bytes`: from step 4

### Step 6: Report results
Show:
- Episode title
- Audio file and URL
- File size
- Total episodes in feed

### Step 7: Ask about saving to project folder
Ask: "Would you like me to copy the generated files (audio, feed, episode data) to your project folder for version control?"

If yes, ask for the target folder path (or use the current working directory). Then copy:
```bash
mkdir -p <target>/data <target>/output/public/audio
cp <plugin-cache>/output/public/audio/<audio_file> <target>/output/public/audio/
cp <plugin-cache>/output/public/feed.xml <target>/output/public/
cp <plugin-cache>/data/episodes.json <target>/data/
cp <plugin-cache>/data/state.json <target>/data/
```

The source paths come from the `generate_audio` and `update_feed` tool responses.

### Step 8: Ask about git
Ask: "Ready to commit and push the new episode to GitHub? This will update the feed on GitHub Pages."

If confirmed, run from the target project folder:
```bash
cd <target>
git add data/episodes.json data/state.json output/public/feed.xml output/public/audio/
git commit -m "Add episode: <title>"
git push origin main
```

### Step 9: Cleanup
After a successful git push, call the `cleanup` tool to remove any leftover temporary audio chunks (`.part*.mp3` files) from the output directory.
