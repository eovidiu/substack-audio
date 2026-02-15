# Deployment

## Purpose

Push commits to GitHub via HTTPS and deploy the podcast feed to GitHub Pages via GitHub Actions.

## Source Files

- `commands/podcast-episode.md` — Git push in episode workflow (step 7)
- `commands/setup.md` — Git push in setup workflow (step 7)
- `.github/workflows/podcast.yml` — GitHub Actions deploy workflow

## Requirements

### Requirement: HTTPS Push with Token

The system SHALL push to GitHub via HTTPS using a GitHub Personal Access Token from `.env`.

#### Scenario: Successful push
- **WHEN** push is requested
- **THEN** read `GITHUB_TOKEN` from `.env` via `grep`
- **AND** temporarily set remote URL to `https://<token>@github.com/<user>/<repo>.git`
- **AND** `git push origin main`
- **AND** immediately reset remote URL to `https://github.com/<user>/<repo>.git`

#### Scenario: Token not set
- **WHEN** `GITHUB_TOKEN` is missing or equals `your_github_token_here`
- **THEN** show error with instructions to create a fine-grained token
- **AND** do not attempt push

#### Scenario: Token never persisted
- **WHEN** push completes (success or failure)
- **THEN** remote URL MUST be reset to remove the token
- **AND** token MUST NOT remain in `.git/config`

### Requirement: GitHub Token Scope

The system SHALL require a fine-grained GitHub Personal Access Token with minimal permissions.

#### Scenario: Token creation instructions
- **WHEN** user needs to create a token
- **THEN** direct to github.com/settings/tokens?type=beta
- **AND** specify: repository access = only the podcast repo
- **AND** specify: permissions = Contents: Read and write
- **AND** no other permissions needed

### Requirement: GitHub Pages Deployment

The system SHALL deploy `output/public/` to GitHub Pages via GitHub Actions.

#### Scenario: Push triggers deploy
- **WHEN** a push lands on `main` branch
- **AND** changes are in `output/public/**`
- **THEN** GitHub Actions workflow triggers

#### Scenario: Workflow steps
- **WHEN** workflow runs
- **THEN** checkout repo
- **AND** `actions/configure-pages@v5` auto-enables GitHub Pages
- **AND** `actions/upload-pages-artifact@v3` uploads `output/public`
- **AND** `actions/deploy-pages@v4` deploys to Pages

#### Scenario: Manual deploy
- **WHEN** `workflow_dispatch` is triggered
- **THEN** deploy runs regardless of file changes

#### Scenario: First-time Pages activation
- **WHEN** workflow runs for the first time on a new repo
- **THEN** `actions/configure-pages@v5` auto-enables Pages (no manual settings step needed)
- **AND** placeholder `output/public/index.html` ensures workflow triggers on initial push

### Requirement: Post-Push Verification

The system SHALL verify that push succeeded before reporting success.

#### Scenario: Push verification
- **WHEN** `git push` completes
- **THEN** check `git log --oneline -1` to confirm latest commit
