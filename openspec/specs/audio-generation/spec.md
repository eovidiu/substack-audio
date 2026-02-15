# Audio Generation

## Purpose

Convert narrative text to MP3 audio via ElevenLabs TTS API, handling text chunking, multi-part concatenation, and cleanup.

## Source Files

- `substack_audio/tts.py` — text splitting, ElevenLabs API call, MP3 concatenation
- `substack_audio/cli.py` — `generate_audio` and `cleanup` commands

## Requirements

### Requirement: Text Chunking

The system SHALL split text into chunks that respect paragraph boundaries, each within the configured character limit.

Default limit: 4500 characters (configurable via `ELEVENLABS_TEXT_LIMIT`).

#### Scenario: Text fits in one chunk
- **WHEN** text length <= max_len
- **THEN** return single chunk (no splitting)

#### Scenario: Multi-paragraph text exceeding limit
- **WHEN** text exceeds max_len
- **THEN** split on paragraph boundaries (`\n\n`)
- **AND** combine paragraphs to fill chunks up to max_len

#### Scenario: Single paragraph exceeds limit
- **WHEN** one paragraph exceeds max_len
- **THEN** split at word boundaries using `rfind(" ", 0, max_len)`

### Requirement: ElevenLabs TTS Invocation

The system SHALL call the ElevenLabs API to convert each text chunk to speech.

#### Scenario: Successful generation
- **WHEN** `elevenlabs_tts(client, voice_id, model_id, output_format, text)` is called
- **THEN** call `client.text_to_speech.convert()` with provided parameters
- **AND** return MP3 bytes

#### Scenario: Missing API key
- **WHEN** `ELEVENLABS_API_KEY` is not set
- **THEN** exit with error JSON before making any API calls

#### Scenario: API error
- **WHEN** ElevenLabs API returns an error (auth, rate limit, server)
- **THEN** propagate the exception (no automatic retry at TTS level)

### Requirement: MP3 Concatenation

The system SHALL concatenate multi-part MP3 files into a single output file.

#### Scenario: Single part
- **WHEN** only one chunk was generated
- **THEN** copy the single part file directly to output (no concat needed)

#### Scenario: ffmpeg available
- **WHEN** multiple parts exist and ffmpeg is installed
- **THEN** use `ffmpeg -f concat -safe 0 -c copy` for lossless concatenation

#### Scenario: ffmpeg not available
- **WHEN** multiple parts exist and ffmpeg is not found
- **THEN** fall back to sequential byte-append of MP3 files

### Requirement: Output File Naming

The system SHALL name audio files as `{YYYY-MM-DD}-{slug}.mp3`.

#### Scenario: Normal title
- **WHEN** title is "Building AI Agents" and date is 2026-02-15
- **THEN** output file is `2026-02-15-building-ai-agents.mp3`

#### Scenario: Slug generation
- **WHEN** `slugify(text)` is called
- **THEN** lowercase, remove non-alphanumeric chars, replace spaces/dashes with single dash
- **AND** limit to 80 characters
- **AND** return `"untitled"` if result is empty

### Requirement: Part File Cleanup

The system SHALL remove temporary `.part*.mp3` files after concatenation, and provide a cleanup command for orphans.

#### Scenario: After successful concatenation
- **WHEN** final MP3 is written
- **THEN** delete all `.part*.mp3` files for this episode

#### Scenario: Cleanup command
- **WHEN** `cleanup --project-root <path>` is called
- **THEN** find and remove all `.part*.mp3` files in `output/public/audio/`
- **AND** return JSON with list of removed files and count

### Requirement: Generate Audio Command Output

The system SHALL return structured JSON from `generate_audio`.

#### Scenario: Successful generation
- **WHEN** audio generation completes
- **THEN** return `{audio_file, audio_path, audio_url, audio_size_bytes, chunks_processed}`

#### Scenario: Empty text file
- **WHEN** `--text-file` points to an empty file
- **THEN** exit with error JSON, exit code 1
