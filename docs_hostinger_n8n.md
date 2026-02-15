# Best Approach: Fully Automated with Hostinger + n8n (instead of GitHub Actions)

Given Substack blocking GitHub-hosted runner IPs, the most reliable setup is:

1. Keep generation logic in `scripts/substack_to_spotify.py`.
2. Run it from your own Hostinger server (or your Hostinger n8n host).
3. Schedule with n8n Cron.
4. Publish generated files (`output/public/feed.xml` and `output/public/audio/*.mp3`) to a public folder on your Hostinger domain.
5. Use that public URL as `PUBLIC_BASE_URL` and submit `<PUBLIC_BASE_URL>/feed.xml` to Spotify.

## Why this is best for your case

- Avoids GitHub runner IP blocks from Substack.
- Keeps full automation (no manual trigger).
- Keeps hosting and automation in one place (Hostinger + n8n).
- Still uses ElevenLabs officially via Python SDK.

## Recommended architecture

- **n8n Cron node**: trigger every 6h or daily.
- **n8n Execute Command node**: run the Python script.
- **Hostinger public web root**: serves `feed.xml` and MP3 files.
- **Spotify**: reads RSS feed URL from Hostinger.

## n8n Execute Command example

```bash
cd /workspace/substack-audio
source .venv/bin/activate
python scripts/substack_to_spotify.py
rsync -av --delete output/public/ /home/<hostinger-user>/domains/<your-domain>/public_html/podcast/
```

Then use:

- `PUBLIC_BASE_URL=https://<your-domain>/podcast`
- Feed URL for Spotify: `https://<your-domain>/podcast/feed.xml`

## Environment variables (server-side)

Set these where n8n can access them (or in `.env` on the same machine):

- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`
- `PUBLIC_BASE_URL`
- `SUBSTACK_FEED_URL`
- `PODCAST_TITLE`
- `PODCAST_DESCRIPTION`
- `PODCAST_LINK`
- `PODCAST_AUTHOR`
- `PODCAST_LANGUAGE`
- optional: `PODCAST_EMAIL`, `PODCAST_IMAGE_URL`, `MAX_POSTS_PER_RUN`

## Minimal n8n flow

1. **Cron** (e.g. every day at 08:00)
2. **Execute Command** (run script + sync to public folder)
3. **HTTP Request** (GET `https://<your-domain>/podcast/feed.xml`)
4. **IF** (`statusCode == 200`) -> success notification
5. **Else** -> error notification (email/telegram/slack)
