# Substack -> ElevenLabs -> Spotify (Automated Starter)

This project converts your Substack posts into spoken audio with ElevenLabs, publishes a podcast RSS feed, and makes it consumable on Spotify.

## What this pipeline does

1. Reads your Substack RSS feed.
2. Finds new posts.
3. Converts each post to speech with ElevenLabs.
4. Saves MP3 files in `output/public/audio/`.
5. Builds a podcast RSS feed at `output/public/feed.xml`.
6. (Optional via GitHub Actions) runs daily and republishes automatically.

## Quick start (local)

1. Create your env file:
   - `cp .env.example .env`
2. Fill required values in `.env`:
   - `ELEVENLABS_API_KEY`
   - `ELEVENLABS_VOICE_ID`
   - `PUBLIC_BASE_URL` (where `output/public` is hosted)
3. Install deps:
   - `python3 -m venv .venv && source .venv/bin/activate`
   - `pip install -r requirements.txt`
4. Run:
   - `python scripts/substack_to_spotify.py`

## Make it fully automatic with GitHub Actions

This repo includes `.github/workflows/podcast.yml` (daily run at 08:00 UTC).

Set these GitHub repository settings:

- Secrets:
  - `ELEVENLABS_API_KEY`
  - `ELEVENLABS_VOICE_ID`
- Variables:
  - `PUBLIC_BASE_URL` (example: `https://<your-user>.github.io/<your-repo>`)
  - `SUBSTACK_FEED_URL` (default: `https://ovidiueftimie.substack.com/feed`)
  - `PODCAST_TITLE`
  - `PODCAST_DESCRIPTION`
  - `PODCAST_LINK`
  - `PODCAST_AUTHOR`
  - `PODCAST_EMAIL`
  - Optional: `ELEVENLABS_MODEL_ID`, `MAX_POSTS_PER_RUN`, `PODCAST_IMAGE_URL`, etc.

Then enable GitHub Pages for this repo so `output/public` is deployed.

## Connect to Spotify (one-time)

1. Open Spotify for Creators.
2. Add/import podcast by RSS URL:
   - `https://<your-public-base-url>/feed.xml`
3. Verify ownership and publish.

After that, new episodes appear automatically when the RSS feed updates.

## Notes

- If posts are long, the script splits text into chunks before TTS.
- For multi-chunk episodes, the script tries `ffmpeg` concat when available; otherwise it falls back to byte-append.
- Generated state is kept in `data/state.json` and episode index in `data/episodes.json`.
