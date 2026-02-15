---
description: Convert a Substack article URL into a full podcast episode
argument-hint: <substack-article-url>
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
---

# Podcast Episode Creator

Create a podcast episode from: $ARGUMENTS

## Critical Rules

- **NEVER delete or reorder existing episodes** in episodes.json or feed.xml. Append only.
- **NEVER ask the user to paste API keys** into this chat. Secrets live in `.env`.
- **NEVER clone or pull the plugin's code repo.** All code is already here in the plugin cache.
- The plugin code directory is READ-ONLY. User data lives in their **podcast repo**.

## How Commands Work

All commands run via Bash using the CLI:

```bash
PLUGIN_DIR="$(dirname "$(find ~ -path "*/substack-audio/pyproject.toml" -maxdepth 6 2>/dev/null | head -1)")"
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli <command> [args]
```

Store `PLUGIN_DIR` at the start and reuse it throughout.

## Workflow

### Step 0: Pre-flight check

Find the plugin directory and run setup check:

```bash
PLUGIN_DIR="$(dirname "$(find ~ -path "*/substack-audio/pyproject.toml" -maxdepth 6 2>/dev/null | head -1)")"
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli setup_check
```

If `ready` is false, show what's missing and **stop** — suggest running `/setup`.

Get the podcast repo path from saved config:
```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli get_config
```

The `podcast_repo_path` field tells you where user data lives. If not set, ask the user for their podcast repo path and save it:
```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli save_config --podcast-repo-path "<path>"
```

### Step 1: Fetch the article

```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli fetch_article "<url>"
```

Parse the JSON output. Display the article title, author, word count.

### Step 2: Check for duplicates

```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli list_episodes --project-root "<podcast-repo>"
```

Check if this article URL appears as a `guid` in the episodes list. If it has, warn the user and ask whether to regenerate.

### Step 3: Create the narrative

Using the **narrative-writer** skill, create a condensed 10-12 minute audio narrative from the article text. The narrative must:
- Be 1500-1800 words (proportionally shorter for short articles)
- Address the listener directly
- Capture core ideas with concrete examples
- Open with a hook, close with resonance

**Present the full narrative text to the user for review. Do NOT proceed until the user approves it.**

### Step 4: Generate audio

After narrative approval, save the narrative text to a temporary file and generate audio:

```bash
# Save narrative to temp file (avoid shell escaping issues with long text)
cat > /tmp/narrative.txt << 'NARRATIVE_EOF'
<narrative text here>
NARRATIVE_EOF

uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli generate_audio \
  --title "<article title>" \
  --pub-date "<pub date ISO>" \
  --text-file /tmp/narrative.txt \
  --project-root "<podcast-repo>"
```

This calls ElevenLabs and costs API credits. The tool returns JSON with `audio_file`, `audio_path`, `audio_url`, and `audio_size_bytes`.

### Step 5: Update the feed

```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli update_feed \
  --title "<article title>" \
  --description "<first ~250 chars of narrative>" \
  --author "<article author>" \
  --link "<article url>" \
  --guid "<article url>" \
  --pub-date-iso "<pub date ISO>" \
  --audio-file "<audio_file from step 4>" \
  --audio-url "<audio_url from step 4>" \
  --audio-size-bytes <size from step 4> \
  --project-root "<podcast-repo>"
```

### Step 6: Report results

Show:
- Episode title
- Audio file and URL
- File size
- Total episodes in feed

### Step 7: Git commit and push

First, verify git auth:
```bash
git -C "<podcast-repo>" push --dry-run origin main 2>&1
```

If the dry-run fails, help the user fix auth:
```bash
which gh && gh auth status
```

Once auth is confirmed, ask: "Ready to commit and push the new episode to GitHub? This will update the feed on GitHub Pages."

If confirmed:
```bash
cd "<podcast-repo>"
git add data/episodes.json data/state.json output/public/feed.xml output/public/audio/
git commit -m "Add episode: <title>"
git push origin main
```

After push, verify:
```bash
git -C "<podcast-repo>" log --oneline -1
```

### Step 8: Cleanup

After a successful git push, clean up temporary files:

```bash
uv run --directory "$PLUGIN_DIR" python -m substack_audio.cli cleanup --project-root "<podcast-repo>"
rm -f /tmp/narrative.txt
```
