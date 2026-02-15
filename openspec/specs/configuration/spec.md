# Configuration

## Purpose

Manage environment variables, plugin config persistence, and setup validation. Foundation for all other capabilities.

## Source Files

- `substack_audio/config.py` — env var access helpers
- `substack_audio/cli.py` — `setup_check`, `get_config`, `save_config` commands

## Requirements

### Requirement: Environment Variable Resolution

The system SHALL read configuration from environment variables with type-safe accessors.

- `env(name, default="")` returns string value; empty string treated as missing.
- `env_bool(name, default=False)` coerces to bool (`1`, `true`, `yes`, `on` → True).
- `parse_csv(value)` splits comma-separated string into trimmed list.

#### Scenario: Variable exists with value
- **WHEN** `env("PODCAST_TITLE")` is called
- **AND** `PODCAST_TITLE=My Podcast` is set
- **THEN** return `"My Podcast"`

#### Scenario: Variable is empty string
- **WHEN** `env("PODCAST_TITLE")` is called
- **AND** `PODCAST_TITLE=` is set (empty)
- **THEN** return the default value, not empty string

#### Scenario: Boolean coercion
- **WHEN** `env_bool("TARGET_INCLUDE_PROCESSED")` is called
- **AND** value is `"true"` or `"1"` or `"yes"` or `"on"` (case-insensitive)
- **THEN** return `True`

### Requirement: Dotenv Loading Chain

The system SHALL load `.env` files in a specific order, with later files overriding earlier ones.

#### Scenario: Two .env files exist
- **WHEN** CLI starts
- **THEN** load `.env` from plugin directory first
- **AND** load `.env` from podcast repo path (from `data/config.json`) second
- **AND** podcast repo values override plugin values

#### Scenario: No podcast repo configured
- **WHEN** `data/config.json` has no `podcast_repo_path`
- **THEN** load only the plugin directory `.env`

### Requirement: Plugin Config Persistence

The system SHALL persist plugin configuration in `data/config.json` within the plugin directory.

#### Scenario: Save podcast repo path
- **WHEN** `save_config --podcast-repo-path "/path/to/repo"` is called
- **THEN** resolve path to absolute via `.resolve()`
- **AND** persist to `data/config.json`

#### Scenario: Get config
- **WHEN** `get_config` is called
- **THEN** return JSON with all stored config fields
- **AND** include `podcast_repo_path` and `github_username` if set

### Requirement: Setup Validation

The system SHALL validate that all required configuration is present via `setup_check`.

Required fields: `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `PUBLIC_BASE_URL`.

Recommended fields: `PODCAST_TITLE`, `PODCAST_AUTHOR`, `PODCAST_DESCRIPTION`, `PODCAST_LINK`, `PODCAST_EMAIL`, `PODCAST_IMAGE_URL`.

#### Scenario: All required fields set
- **WHEN** `setup_check` is called
- **AND** all required env vars have non-empty values
- **THEN** return `{"ready": true, "missing": [], ...}`

#### Scenario: Missing required field
- **WHEN** `ELEVENLABS_API_KEY` is not set
- **THEN** return `{"ready": false, "missing": [{"env_var": "ELEVENLABS_API_KEY", ...}]}`

#### Scenario: Secret masking
- **WHEN** `setup_check` returns config values
- **AND** `ELEVENLABS_API_KEY` is set
- **THEN** show it as `"***"` in the response, not the actual key
