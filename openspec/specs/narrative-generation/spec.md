# Narrative Generation

## Purpose

Transform article text into a spoken-word narrative suitable for podcast audio. The narrative is a condensed, listener-addressed retelling — not a transcript or summary.

## Source Files

- `skills/narrative-writer/SKILL.md` — Narrative generation rules and quality checklist

## Requirements

### Requirement: Narrative Length

The system SHALL produce narratives of 1500-1800 words, proportionally adjusted for article length.

#### Scenario: Standard article (1500-5000 words)
- **WHEN** article is 1500-5000 words
- **THEN** generate 1500-1800 word narrative (~10-12 min at 150 wpm)

#### Scenario: Short article (under 1500 words)
- **WHEN** article is under 1500 words
- **THEN** narrative is proportionally shorter (never pad with filler)

#### Scenario: Long article (over 5000 words)
- **WHEN** article exceeds 5000 words
- **THEN** prioritize 3 ideas deeply over 10 superficially

### Requirement: Narrative Voice

The system SHALL write in direct address to the listener, using second person ("you").

#### Scenario: Voice style
- **WHEN** generating narrative
- **THEN** use direct address ("you", "your")
- **AND** match the original article's energy and tone
- **AND** use short sentences, active voice, concrete language

#### Scenario: Prohibited patterns
- **WHEN** generating narrative
- **THEN** exclude meta-commentary ("the author argues", "this article discusses")
- **AND** exclude filler transitions ("Now let's move on to")
- **AND** exclude AI-isms ("It's worth noting", "Interestingly")
- **AND** exclude podcast cliches ("Stay tuned", "Don't forget to subscribe")

### Requirement: Narrative Structure

The system SHALL follow a specific structural arc: hook, thesis, body, close.

#### Scenario: Opening
- **WHEN** narrative begins
- **THEN** open with a hook (question, surprising fact, or compelling framing)
- **AND** state core thesis within 200 words

#### Scenario: Body
- **WHEN** building the narrative body
- **THEN** group ideas thematically (not by article structure)
- **AND** preserve concrete examples and data from the original

#### Scenario: Closing
- **WHEN** ending the narrative
- **THEN** close with a resonant insight or forward-looking implication
- **AND** avoid summarizing what was just said

### Requirement: User Approval Gate

The system SHALL present the narrative to the user and wait for explicit approval before proceeding to audio generation.

#### Scenario: Narrative presented
- **WHEN** narrative is generated
- **THEN** present the full text to the user
- **AND** do NOT proceed to audio generation until user approves

#### Scenario: User requests changes
- **WHEN** user asks for modifications
- **THEN** revise narrative and present again for approval
