# Substack Audio Plugin — Directives

These rules are mandatory for all sessions using this plugin.

## Feed Integrity

**NEVER delete, reorder, or modify existing episodes in `episodes.json` or `feed.xml`.**

- New episodes are **appended only**. Existing entries must not be touched.
- When rebuilding `feed.xml`, all existing episodes must appear with their original data intact.
- The only allowed modification to an existing episode is re-generating its audio (same GUID), which replaces that single entry in-place.
- If `episodes.json` or `feed.xml` already exist in the user's repository, load and preserve them before adding anything.

Violating this rule breaks podcast subscribers' feeds and can cause episodes to disappear from Spotify/Apple Podcasts.

## Secret Handling

**NEVER ask the user to type API keys, tokens, or passwords into the chat.**

- Direct users to set secrets in the **Connector environment variables** (Claude Desktop > Plugins > Substack audio > Connectors > Edit) or in a `.env` file they edit themselves.
- If a secret is missing, explain where to set it — do not prompt for the value.

## Git Operations

- Always verify git authentication is working before attempting to push (`git remote -v` and `git push --dry-run`).
- Use the user's existing git credentials on their machine. Do not ask them to leave Claude Desktop to run terminal commands.
- Never force-push. Never push to a branch other than what the user specifies.
- After pushing, verify the push succeeded before reporting success.
