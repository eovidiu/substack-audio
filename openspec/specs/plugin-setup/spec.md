# Plugin Setup

## Purpose

Guide first-time configuration of the Substack Audio plugin: install dependencies, resolve identities, scaffold the podcast repo, collect metadata, and validate the setup.

## Source Files

- `commands/setup.md` — Step-by-step setup workflow
- `substack_audio/cli.py` — `setup_check`, `save_config` commands

## Requirements

### Requirement: Plugin Discovery and Dependency Installation

The system SHALL find the plugin directory and install Python dependencies in a single Bash call.

#### Scenario: Plugin found
- **WHEN** setup starts
- **THEN** search for `*/substack-audio/pyproject.toml` via `find`
- **AND** install deps via `pip install --user -r requirements.txt`
- **AND** verify import with `python3 -c "import substack_audio; print('ok')"`
- **AND** combine all in one Bash call (variables don't persist between calls)

#### Scenario: Plugin not found
- **WHEN** `find /` returns no results
- **THEN** try narrower paths: `$HOME`, `/sessions`, `/mnt`

### Requirement: Identity Resolution

The system SHALL resolve git identity and GitHub username as two separate values.

- **GIT_NAME** (e.g. "Ovidiu") — display name for commits and podcast author default
- **GH_USER** (e.g. "eovidiu") — GitHub login for repo URLs and Pages URLs

#### Scenario: Git identity exists
- **WHEN** `git config --global user.name` returns a value
- **THEN** present to user for confirmation

#### Scenario: GitHub username
- **WHEN** GitHub username is needed
- **THEN** ask the user: "What's your GitHub username? (your login, not display name)"
- **AND** never use GIT_NAME for GitHub URLs

### Requirement: Podcast Repo Scaffold

The system SHALL clone or create a podcast repo and set up the directory structure.

#### Scenario: New repo
- **WHEN** user has no existing repo
- **THEN** instruct user to create a public repo on github.com/new with README
- **AND** wait for confirmation before proceeding

#### Scenario: Clone and scaffold
- **WHEN** repo exists on GitHub
- **THEN** `git clone` via HTTPS into CoWorks working folder
- **AND** create directories: `data/`, `output/public/audio/`, `.github/workflows/`
- **AND** copy `podcast.yml` from plugin
- **AND** create placeholder `output/public/index.html`
- **AND** commit initial setup

### Requirement: Environment File Generation

The system SHALL collect podcast metadata and generate a `.env` file with pre-filled values and secret placeholders.

#### Scenario: Metadata collection
- **WHEN** building .env
- **THEN** ask user for: title, author (default: GIT_NAME), description, website URL, email (default: GIT_EMAIL), cover image URL, voice model
- **AND** compute `PUBLIC_BASE_URL=https://<GH_USER>.github.io/<repo-name>`

#### Scenario: Secret placeholders
- **WHEN** .env is written
- **THEN** include `ELEVENLABS_API_KEY=your_key_here`, `ELEVENLABS_VOICE_ID=your_voice_id_here`, `GITHUB_TOKEN=your_github_token_here`
- **AND** add `.env` to `.gitignore`

### Requirement: Secret Handling

The system SHALL never accept API keys, tokens, or passwords in the chat. Users edit `.env` directly.

#### Scenario: Secrets needed
- **WHEN** secrets must be configured
- **THEN** tell user to open `.env` in their working folder on their Mac
- **AND** provide instructions for obtaining each secret (ElevenLabs, GitHub token)
- **AND** never show VM-internal paths; use relative paths like `<repo-name>/.env`

### Requirement: CLAUDE.md Generation

The system SHALL generate a `CLAUDE.md` file in the podcast repo with full project context for future sessions.

#### Scenario: CLAUDE.md content
- **WHEN** CLAUDE.md is generated
- **THEN** include: podcast repo path, GitHub username, git identity, CLI command reference, podcast configuration, critical rules

### Requirement: Setup Validation and Initial Push

The system SHALL validate configuration and push initial commits to GitHub.

#### Scenario: Validation passes
- **WHEN** user confirms secrets are set
- **THEN** run `setup_check`
- **AND** if `ready=true`, push to GitHub using GITHUB_TOKEN from .env

#### Scenario: Validation fails
- **WHEN** `setup_check` returns `ready=false`
- **THEN** show missing fields and help fix before pushing

### Requirement: Path Display

The system SHALL never show VM-internal paths to the user. Always use paths relative to the user's working folder.

#### Scenario: File location reference
- **WHEN** telling user about `.env` or any file location
- **THEN** show `<repo-name>/.env`, not `/sessions/abc-xyz/repo-name/.env`
