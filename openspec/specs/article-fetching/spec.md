# Article Fetching

## Purpose

Fetch Substack articles by URL and parse content from HTML, RSS, and JSON sources. Handle Cloudflare protection with multi-strategy fallback.

## Source Files

- `substack_audio/fetch.py` — HTTP fetch with retry and Cloudflare bypass
- `substack_audio/parse.py` — HTML/RSS/JSON parsing, text extraction, item selection

## Requirements

### Requirement: Single Article Fetch

The system SHALL fetch a Substack article by URL and return structured metadata plus content.

Returns: `{title, author, pub_date, description, link, content_html, content_text, word_count}`.

#### Scenario: Valid Substack URL
- **WHEN** `fetch_article_by_url(url)` is called with a valid Substack post URL
- **THEN** return dict with title (from og:title or h1), author (from meta), pub_date (from time tag), description (from og:description), content_html, content_text, word_count

#### Scenario: Content div detection
- **WHEN** parsing article HTML
- **THEN** try content containers in order: `div.body.markup`, `div.available-content`, `div.post-content`, `article` tag
- **AND** use first match found

#### Scenario: HTTP error
- **WHEN** server returns non-2xx status
- **THEN** raise `requests.HTTPError`

### Requirement: Feed Fetch with Retry Cascade

The system SHALL fetch RSS/XML feeds using a three-strategy cascade to handle Cloudflare and transient failures.

#### Scenario: Normal fetch succeeds
- **WHEN** `fetch_feed_xml(url)` is called
- **THEN** try `curl` first (bypasses Cloudflare more often than requests)
- **AND** return feed XML string

#### Scenario: Curl fails, requests succeeds
- **WHEN** curl returns error
- **THEN** retry via `requests.Session` up to 3 times
- **AND** use exponential backoff (`attempt * 2` seconds)
- **AND** retry on status codes: 403, 429, 500, 502, 503, 504

#### Scenario: All standard methods fail
- **WHEN** both curl and requests fail
- **THEN** try `cloudscraper` as last resort
- **AND** if all fail, raise `RuntimeError`

### Requirement: HTML to Text Conversion

The system SHALL strip HTML to plain text, removing scripts, styles, and structural markup.

#### Scenario: Normal HTML
- **WHEN** `strip_html_to_text(html)` is called
- **THEN** remove `<script>`, `<style>`, `<noscript>` tags
- **AND** extract text with newline separators
- **AND** strip each line, filter empty lines
- **AND** join with double newlines

### Requirement: RSS Feed Parsing

The system SHALL parse RSS XML into a list of item dicts with standard fields.

#### Scenario: Standard RSS feed
- **WHEN** `parse_rss(feed_xml)` is called
- **THEN** extract per-item: title, link, guid, pub_date, description_html, content_html, author
- **AND** use `content:encoded` for full content when available

#### Scenario: Missing guid
- **WHEN** RSS item has no `<guid>` element
- **THEN** fall back to link, then title as guid

### Requirement: Item Selection

The system SHALL filter feed items by selector strings with multiple match strategies.

Selector formats: `guid:<id>`, `link:<url>`, `title:<text>`, or plain substring.

#### Scenario: GUID selector
- **WHEN** selector is `guid:12345`
- **THEN** match items where guid equals `12345` exactly (case-insensitive)

#### Scenario: Plain text selector
- **WHEN** selector is `ai agents`
- **THEN** match items where title, guid, or link contains `ai agents` (case-insensitive substring)
