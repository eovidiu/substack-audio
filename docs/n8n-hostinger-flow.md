# n8n (Hostinger) Automation: Substack ➜ ElevenLabs ➜ Podcast RSS ➜ Spotify

This guide shows a practical **fully automated flow** you can run from your n8n instance on Hostinger.

## Important architecture note

Spotify does not accept direct "upload API" for regular podcasters. The supported pattern is:

1. Generate MP3
2. Publish MP3 at a public URL
3. Update your podcast RSS feed (`feed.xml`) with the new episode
4. Spotify crawls the RSS and picks up the new episode

So your automation goal is "Substack to RSS feed update"; Spotify is the consumer.

---

## Recommended n8n workflow

### Workflow trigger

- **Node:** `Cron`
- **Schedule:** every 30 minutes or hourly

### 1) Get latest Substack post

- **Node:** `HTTP Request`
- **Method:** `GET`
- **URL:** `https://ovidiueftimie.substack.com/feed`
- **Headers:**
  - `User-Agent: Mozilla/5.0 (compatible; RSSReader/1.0)`
  - `Accept: application/rss+xml, application/xml;q=0.9, */*;q=0.8`

### 2) Parse feed and pick newest unprocessed post

- **Node:** `RSS Feed Read`
  - Input from previous HTTP response
- **Node:** `IF`
  - Check if `guid`/`link` exists in a datastore table (`processed_posts`)

### 3) Fetch full article body

- **Node:** `HTTP Request`
- **URL:** `{{$json["link"]}}`
- **Then Node:** `HTML Extract`
  - Extract main article HTML/text (Substack post body)

### 4) Clean + prepare TTS text

- **Node:** `Code` (JavaScript)
  - Strip HTML tags
  - Remove image captions/buttons
  - Add intro/outro sentence
  - Chunk text to ~1,000–2,000 chars per part

### 5) Generate audio with ElevenLabs

- **Node:** `HTTP Request`
- **Method:** `POST`
- **URL:** `https://api.elevenlabs.io/v1/text-to-speech/<VOICE_ID>`
- **Headers:**
  - `xi-api-key: <from n8n credentials>`
  - `Content-Type: application/json`
  - `Accept: audio/mpeg`
- **Body:**
  - `text`, `model_id`, `output_format`

Run this in a loop for each chunk, then merge chunks:

- **Node:** `Merge` + optional `Execute Command` (`ffmpeg`) to concatenate parts.

### 6) Publish MP3

Pick one host:

- Hostinger object storage / S3-compatible bucket
- Bunny storage
- Cloudflare R2
- GitHub Pages (good for MVP)

- **Node:** `S3` (or generic `HTTP Request` upload)
- Save as `audio/<slug>.mp3`
- Capture public URL

### 7) Update RSS feed

- **Node:** `HTTP Request` (download current `feed.xml`)
- **Node:** `Code` or `XML` transform
  - Insert new `<item>` with:
    - `title`
    - `link`
    - `guid`
    - `pubDate`
    - `<enclosure url="...mp3" length="..." type="audio/mpeg"/>`
- **Node:** upload updated `feed.xml` back to host

### 8) Mark as processed

- **Node:** `Data Store` / DB insert
  - Save `guid`, `slug`, `published_at`

### 9) Notify yourself

- **Node:** Telegram/Email/Slack
  - "Episode published: <title>"

---

## Minimal data table design

`processed_posts`:

- `guid` (unique)
- `post_url`
- `slug`
- `audio_url`
- `published_at`
- `status`

---

## Reliability safeguards to add

1. **Idempotency**: do not republish same `guid`.
2. **Retry**: 403/429/5xx retry with backoff for Substack + ElevenLabs.
3. **Quota guard**: skip post if estimated credits exceed threshold.
4. **Timeout split**: for very long posts, process async in chunks.
5. **Error branch**: notify on failure with post URL and stack trace.

---

## Fastest MVP on your current project

If you already use this repo's script (`scripts/substack_to_spotify.py`), use n8n mainly as an orchestrator:

1. Cron trigger in n8n
2. `Execute Command` node on Hostinger:
   - `python /path/to/substack-audio/scripts/substack_to_spotify.py`
3. Notify success/failure

This is the quickest route because feed generation and state tracking are already implemented.
