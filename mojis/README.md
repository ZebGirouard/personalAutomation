# Slack Emoji Migration Tool

Export custom emoji from one Slack workspace and upload them to another.

## Prerequisites

```
pip install requests browser_cookie3
```

## Setup (one-time per Slack workspace)

You create a **new Slack app in each org** you want to export from or upload to.
The bot/user tokens are org-specific -- update your env vars when switching orgs.

1. Go to https://api.slack.com/apps -> **Create New App** -> From Scratch
   - Pick the workspace you're working with
2. OAuth & Permissions -> **Bot Token Scopes**: `emoji:read`, `reactions:read`
3. OAuth & Permissions -> **User Token Scopes**: `reactions:read`
4. Install to workspace (may need admin approval)
5. Copy both tokens from the OAuth & Permissions page and save in `~/.zshrc`:
   ```bash
   export SLACK_BOT_TOKEN='xoxb-...'   # Bot User OAuth Token
   export SLACK_USER_TOKEN='xoxp-...'  # User OAuth Token
   # ^^^ UPDATE THESE when you switch to a new org's Slack app
   ```

## Export

```bash
# Export emoji you uploaded AND emoji you've used
python mojis/emoji_migrate.py export \
  --mode both \
  --session-token xoxc-YOUR-SESSION-TOKEN \
  --user-id YOUR_MEMBER_ID \
  --output ./my-emoji
# Find your member ID: Slack profile -> ... menu -> Copy member ID
```

### Export modes

| Mode | What it grabs | Auth needed |
|------|--------------|-------------|
| `uploaded` | Emoji you uploaded | `--session-token` |
| `used` | Emoji you've reacted with | `--token` + `--user-token` (or env vars) |
| `both` | Union of both (default) | All three |

### Where to get the session token (xoxc-)

This is the only manual step per export session:

1. Open Slack in **Chrome** (the workspace you're exporting FROM)
2. DevTools (`Cmd+Opt+I`) -> **Network** tab
3. Filter for `/api/` -> click any request
4. In the request payload, find `"token": "xoxc-..."`
5. Copy the full `xoxc-...` value

The `d` cookie is auto-read from Chrome -- no manual step needed.

## Upload

```bash
python mojis/emoji_migrate.py upload \
  --workspace neworg \
  --session-token xoxc-DESTINATION-SESSION-TOKEN \
  --input ./my-emoji
```

- `--workspace` -- destination Slack subdomain (e.g. `neworg` for `neworg.slack.com`)
- `--session-token` -- `xoxc-` token from the **destination** workspace (same DevTools method)
- `--input` -- directory containing `manifest.json` (default: `./my-emoji`)

The `d` cookie is auto-read from Chrome. Make sure you're logged into the **destination** workspace in Chrome.

Supports resume -- tracks uploaded emoji in `.uploaded` so you can re-run safely.
