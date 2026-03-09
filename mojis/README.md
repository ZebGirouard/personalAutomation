# Slack Emoji Tools

Download custom emoji from one Slack workspace, upload to another.

## Prerequisites

```
pip install requests browser_cookie3
```

## Setup (one-time per Slack workspace)

You create a **new Slack app in each org** you want to export from.
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

## Download (emoji_download.py)

### Export
```bash
python mojis/emoji_download.py export \
  --mode both \
  --session-token xoxc-YOUR-SESSION-TOKEN \
  --user-id YOUR_MEMBER_ID \
  --output ./my-emoji
# Find your member ID: Slack profile -> ... menu -> Copy member ID
```

Export is **additive-only** -- re-running only adds new emoji, never removes curated ones.

| Mode | What it grabs | Auth needed |
|------|--------------|-------------|
| `uploaded` | Emoji you uploaded | `--session-token` |
| `used` | Emoji you've reacted with | `--token` + `--user-token` (or env vars) |
| `both` | Union of both (default) | All three |

### Review
```bash
python mojis/emoji_download.py review --input ./my-emoji
```
Opens an HTML gallery. Delete unwanted images in Finder, then sync.

### Sync
```bash
python mojis/emoji_download.py sync --input ./my-emoji
```
Prunes the manifest to match remaining images after manual curation.

## Upload (emoji_upload.py)

```bash
python mojis/emoji_upload.py \
  --workspace neworg \
  --session-token xoxc-DESTINATION-SESSION-TOKEN \
  --input ./my-emoji
```

- `--workspace` -- destination subdomain (e.g. `neworg` for `neworg.slack.com`)
- Supports resume -- safe to re-run if interrupted
- Make sure you're logged into the **destination** workspace in Chrome

## Where to get the session token (xoxc-)

This is the only manual step, grab a fresh one each session:

1. Open Slack in **Chrome** (source or destination workspace as needed)
2. DevTools (`Cmd+Opt+I`) -> **Network** tab
3. Filter for `/api/` -> click any request
4. In the request payload, find `"token": "xoxc-..."` -> copy the full value

The `d` cookie is auto-read from Chrome -- no manual step needed.
