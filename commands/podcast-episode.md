---
description: Convert a Substack article URL into a full podcast episode
argument-hint: <substack-article-url>
allowed-tools:
  - Read
  - Bash
  - Glob
  - mcp__substack-audio__fetch_article
  - mcp__substack-audio__generate_audio
  - mcp__substack-audio__update_feed
  - mcp__substack-audio__list_episodes
---

# Podcast Episode Creator

Create a podcast episode from: $ARGUMENTS

## Workflow

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

### Step 7: Ask about git
Ask: "Ready to commit and push the new episode to GitHub? This will update the feed on GitHub Pages."

If confirmed, run:
```bash
git add data/episodes.json data/state.json output/public/feed.xml output/public/audio/
git commit -m "Add episode: <title>"
git push origin main
```
