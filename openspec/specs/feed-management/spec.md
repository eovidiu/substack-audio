# Feed Management

## Purpose

Maintain the podcast episode list and generate a standards-compliant RSS feed with iTunes podcast extensions. Enforce append-only invariant to protect subscriber feeds.

## Source Files

- `substack_audio/feed.py` — RSS feed generation, audio URL construction
- `substack_audio/cli.py` — `update_feed`, `list_episodes` commands
- `substack_audio/util.py` — JSON persistence, date parsing

## Requirements

### Requirement: Append-Only Episode List

The system SHALL never delete, reorder, or modify existing episodes. New episodes are appended. This is a critical invariant — violating it breaks podcast subscribers' feeds and can cause episodes to disappear from Spotify/Apple Podcasts.

#### Scenario: New episode added
- **WHEN** `update_feed` is called with a new GUID
- **THEN** append the episode to `data/episodes.json`
- **AND** rebuild `output/public/feed.xml` with ALL episodes

#### Scenario: Re-generation of existing episode
- **WHEN** `update_feed` is called with a GUID that already exists
- **THEN** replace ONLY that entry (same GUID, updated audio)
- **AND** preserve all other episodes unchanged

#### Scenario: Feed rebuild
- **WHEN** `feed.xml` is regenerated
- **THEN** include every episode from `episodes.json` with original data intact

### Requirement: Episode Data Structure

Each episode SHALL contain: `guid`, `title`, `description`, `author`, `link`, `pub_date_iso`, `audio_file`, `audio_url`, `audio_size_bytes`.

#### Scenario: Episode entry
- **WHEN** episode is stored
- **THEN** persist all fields to `data/episodes.json`
- **AND** `guid` is the article URL (used for duplicate detection)

### Requirement: RSS Feed Generation

The system SHALL generate an RSS 2.0 feed with iTunes podcast extensions via `feedgen`.

#### Scenario: Feed metadata
- **WHEN** `build_feed(episodes, output_feed, cfg)` is called
- **THEN** set feed title, description, language, author+email from config
- **AND** set iTunes metadata: author, summary, explicit="no", type="episodic"
- **AND** set feed self-link and site link
- **AND** set cover image if `PODCAST_IMAGE_URL` is provided

#### Scenario: Episode ordering
- **WHEN** episodes are added to feed
- **THEN** sort by `pub_date_iso` descending (newest first)

#### Scenario: Episode enclosure
- **WHEN** episode is added to feed
- **THEN** set enclosure with audio_url, audio_size_bytes, type="audio/mpeg"

### Requirement: Audio URL Construction

The system SHALL construct audio URLs from the base URL and filename.

#### Scenario: URL building
- **WHEN** `build_audio_url("https://user.github.io/podcast", "2026-02-15-episode.mp3")` is called
- **THEN** return `"https://user.github.io/podcast/audio/2026-02-15-episode.mp3"`

### Requirement: State Tracking

The system SHALL track processed GUIDs in `data/state.json` to prevent accidental re-processing.

#### Scenario: New episode processed
- **WHEN** `update_feed` completes
- **THEN** add the GUID to `processed_guids` in `state.json`

#### Scenario: Duplicate check
- **WHEN** `list_episodes` is called
- **THEN** return all episodes and `processed_guids_count`
- **AND** caller can check if a GUID already exists

### Requirement: List Episodes Command

The system SHALL return all episodes and state via `list_episodes`.

#### Scenario: Episodes exist
- **WHEN** `list_episodes --project-root <path>` is called
- **THEN** return `{episodes: [...], episode_count: N, processed_guids_count: N}`
