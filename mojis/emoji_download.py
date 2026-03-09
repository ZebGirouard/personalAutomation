#!/usr/bin/env python3
"""Download custom emoji from a Slack workspace.

See README.md for setup instructions, or run with --help for auth details.
Requires: pip install requests browser_cookie3
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def resolve_bot_token(args_token):
    """Resolve from --token flag or $SLACK_BOT_TOKEN env var."""
    token = args_token or os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("Error: provide --token or set $SLACK_BOT_TOKEN", file=sys.stderr)
        print("  Get it: https://api.slack.com/apps -> your app -> OAuth & Permissions -> Bot User OAuth Token", file=sys.stderr)
        sys.exit(1)
    return token


def resolve_user_token(args_token):
    """Resolve from --user-token flag or $SLACK_USER_TOKEN env var."""
    token = args_token or os.environ.get("SLACK_USER_TOKEN")
    if not token:
        print("Error: provide --user-token or set $SLACK_USER_TOKEN", file=sys.stderr)
        print("  Get it: https://api.slack.com/apps -> your app -> OAuth & Permissions -> User OAuth Token", file=sys.stderr)
        sys.exit(1)
    return token


def read_d_cookie_from_chrome():
    """Auto-read the Slack 'd' cookie from Chrome's cookie store.

    Requires: pip install browser_cookie3
    No manual step -- reads directly from Chrome's local storage.
    Just be logged into Slack in Chrome (not just the desktop app).
    """
    try:
        import browser_cookie3
    except ImportError:
        print("Error: browser_cookie3 not installed. Run: pip install browser_cookie3", file=sys.stderr)
        sys.exit(1)

    try:
        cj = browser_cookie3.chrome(domain_name=".slack.com")
        for cookie in cj:
            if cookie.name == "d" and "slack.com" in cookie.domain:
                return cookie.value
    except Exception as exc:
        print(f"Error reading Chrome cookies: {exc}", file=sys.stderr)
        print("  Make sure Chrome is installed and you're logged into Slack in Chrome.", file=sys.stderr)
        sys.exit(1)

    print("Error: no Slack 'd' cookie found in Chrome.", file=sys.stderr)
    print("  Make sure you're logged into Slack in Chrome (not just the desktop app).", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Emoji list (bot token -- all custom emoji in workspace)
# ---------------------------------------------------------------------------

def fetch_all_custom_emoji(token):
    """Return (dict of {name: url}, dict of {original: [aliases]})."""
    resp = requests.post(
        "https://slack.com/api/emoji.list",
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        print(f"Error from emoji.list: {data.get('error')}", file=sys.stderr)
        sys.exit(1)

    raw = data.get("emoji", {})
    resolved = {}
    aliases = {}
    for name, url in raw.items():
        if url.startswith("alias:"):
            original = url.removeprefix("alias:")
            aliases.setdefault(original, []).append(name)
        else:
            resolved[name] = url

    return resolved, aliases


# ---------------------------------------------------------------------------
# Uploaded emoji (session auth -- emoji.adminList with xoxc + d cookie)
# ---------------------------------------------------------------------------

def fetch_uploaded_emoji(session_token, d_cookie, user_id):
    """Paginate emoji.adminList to find emoji uploaded by user_id.

    Requires:
      - session_token: xoxc-... (MANUAL: Chrome DevTools -> Network -> any /api/ request -> "token" in payload)
      - d_cookie: auto-read from Chrome via browser_cookie3
    """
    page = 1
    mine = []
    total = 0

    while True:
        resp = requests.post(
            "https://slack.com/api/emoji.adminList",
            data={"count": 500, "page": page, "token": session_token},
            headers={"Cookie": f"d={d_cookie}"},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("ok"):
            print(f"Error from emoji.adminList: {data.get('error')}", file=sys.stderr)
            if data.get("error") == "not_authed":
                print("  The d cookie may be expired. Log into Slack in Chrome and retry.", file=sys.stderr)
            if data.get("error") == "not_allowed_token_type":
                print("  The session token (xoxc-) is required, not a bot/user token.", file=sys.stderr)
                print("  Get it: Chrome DevTools -> Network -> filter '/api/' -> find 'token' in any request payload", file=sys.stderr)
            sys.exit(1)

        emoji = data.get("emoji", [])
        if not emoji:
            break

        total += len(emoji)
        for e in emoji:
            if e.get("user_id") == user_id:
                mine.append({
                    "name": e["name"],
                    "url": e.get("url", ""),
                    "aliases": e.get("synonyms", []),
                    "uploaded_by": e.get("user_id", ""),
                    "is_alias": e.get("is_alias", 0) == 1,
                    "alias_for": e.get("alias_for", ""),
                })

        paging = data.get("paging", {})
        print(f"  Page {page}: {len(emoji)} emoji scanned (found {len(mine)} yours so far)")
        if page >= paging.get("pages", 1):
            break
        page += 1
        time.sleep(0.5)

    print(f"  Scanned {total} total, {len(mine)} uploaded by {user_id}.")
    return mine


# ---------------------------------------------------------------------------
# Reacted emoji (user token -- reactions.list)
# ---------------------------------------------------------------------------

def fetch_reacted_emoji_names(user_token, user_id):
    """Paginate reactions.list and return set of emoji names the user has used.

    Requires:
      - user_token: xoxp-... with reactions:read scope
        ($SLACK_USER_TOKEN or --user-token)
    """
    headers = _auth_headers(user_token)
    page = 1
    names = set()
    total_items = 0

    while True:
        resp = requests.get(
            "https://slack.com/api/reactions.list",
            params={"user": user_id, "count": 100, "page": page},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("ok"):
            print(f"Error from reactions.list: {data.get('error')}", file=sys.stderr)
            sys.exit(1)

        items = data.get("items", [])
        if not items:
            break

        total_items += len(items)
        for item in items:
            msg = item.get("message", {})
            for reaction in msg.get("reactions", []):
                if user_id in reaction.get("users", []):
                    names.add(reaction["name"])

        paging = data.get("paging", {})
        if page >= paging.get("pages", 1):
            break
        page += 1
        time.sleep(0.3)

    print(f"  Scanned {total_items} reacted messages across {page} pages.")
    return names


# ---------------------------------------------------------------------------
# Image download
# ---------------------------------------------------------------------------

def download_image(url, dest):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)


def download_emoji_images(emoji_list, images_dir):
    """Download images for a list of emoji dicts (must have 'name' and 'url')."""
    count = len(emoji_list)
    print(f"Downloading {count} images ...")
    for i, e in enumerate(emoji_list):
        url = e["url"]
        if not url:
            continue
        ext = Path(urlparse(url).path).suffix or ".png"
        dest = images_dir / f"{e['name']}{ext}"
        if dest.exists():
            continue
        try:
            download_image(url, dest)
        except Exception as exc:
            print(f"  WARN: failed to download {e['name']}: {exc}")
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{count} downloaded")
            time.sleep(0.5)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def run_export(args):
    user_id = args.user_id
    mode = args.mode
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    images_dir = output / "images"
    images_dir.mkdir(exist_ok=True)

    # Load existing manifest if present -- export is additive-only
    manifest_path = output / "manifest.json"
    existing_emoji = []
    existing_names = set()
    if manifest_path.exists():
        with open(manifest_path) as f:
            existing = json.load(f)
        existing_emoji = existing.get("emoji", [])
        existing_names = {e["name"] for e in existing_emoji}
        print(f"Existing manifest: {len(existing_names)} emoji (will only add new ones).")

    new_emoji = []

    if mode in ("uploaded", "both"):
        # --- Uploaded emoji: session auth (xoxc + d cookie) ---
        session_token = args.session_token or os.environ.get("SLACK_SESSION_TOKEN")
        if not session_token:
            print("Error: --session-token is required for 'uploaded' mode.", file=sys.stderr)
            print("  Get it: Chrome DevTools -> Network -> filter '/api/' -> find 'token' in any request payload", file=sys.stderr)
            sys.exit(1)

        print("Reading d cookie from Chrome ...")
        d_cookie = read_d_cookie_from_chrome()
        print("  Got d cookie.")

        print(f"Fetching emoji uploaded by {user_id} ...")
        uploaded = fetch_uploaded_emoji(session_token, d_cookie, user_id)
        real_uploaded = [e for e in uploaded if not e["is_alias"]]
        for e in real_uploaded:
            if e["name"] in existing_names:
                continue
            new_emoji.append({
                "name": e["name"],
                "url": e["url"],
                "aliases": e["aliases"],
                "source": "uploaded",
            })

    if mode in ("used", "both"):
        # --- Used emoji: bot token + user token ---
        bot_token = resolve_bot_token(args.token)
        user_token = resolve_user_token(args.user_token)

        print("Fetching workspace custom emoji ...")
        custom_emoji, alias_map = fetch_all_custom_emoji(bot_token)
        print(f"  {len(custom_emoji)} custom emoji in workspace.")

        print(f"Fetching reactions for {user_id} ...")
        reacted_names = fetch_reacted_emoji_names(user_token, user_id)
        print(f"  {len(reacted_names)} unique emoji used.")

        # Intersect with custom emoji
        my_names = reacted_names & set(custom_emoji.keys())
        for original, alias_list in alias_map.items():
            for alias in alias_list:
                if alias in reacted_names and original in custom_emoji:
                    my_names.add(original)
        print(f"  {len(my_names)} are custom emoji (builtins excluded).")

        # Deduplicate against existing manifest + newly-added uploaded emoji
        already = existing_names | {e["name"] for e in new_emoji}
        for name in sorted(my_names):
            if name in already:
                continue
            new_emoji.append({
                "name": name,
                "url": custom_emoji[name],
                "aliases": alias_map.get(name, []),
                "source": "used",
            })

    if not new_emoji:
        print("No new emoji to add.")
        return

    # Download images for new emoji only
    download_emoji_images(new_emoji, images_dir)

    # Merge with existing manifest
    all_emoji = existing_emoji + new_emoji
    manifest = {
        "source_workspace": "unknown",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "emoji": all_emoji,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone. {len(new_emoji)} new emoji added ({len(all_emoji)} total in manifest).")
    print(f"  Manifest: {manifest_path}")
    print(f"  Images:   {images_dir}")


# ---------------------------------------------------------------------------
# Review (gallery)
# ---------------------------------------------------------------------------

def run_review(args):
    input_dir = Path(args.input)
    manifest_path = input_dir / "manifest.json"
    images_dir = input_dir / "images"

    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    emoji_list_data = manifest["emoji"]

    gallery_path = input_dir / "gallery.html"
    rows = []
    for e in emoji_list_data:
        name = e["name"]
        candidates = list(images_dir.glob(f"{name}.*"))
        if not candidates:
            continue
        img_path = candidates[0].name
        source = e.get("source", "")
        badge = f' <span style="color:#888;font-size:11px">({source})</span>' if source else ""
        rows.append(
            f'<div style="display:inline-block;text-align:center;margin:6px;width:90px;vertical-align:top">'
            f'<img src="images/{img_path}" style="width:48px;height:48px;object-fit:contain"><br>'
            f'<span style="font-size:11px;word-break:break-all">{name}</span>{badge}'
            f'</div>'
        )

    html = f"""<!DOCTYPE html>
<html><head><title>Emoji Gallery ({len(rows)} emoji)</title>
<style>body {{ font-family: -apple-system, sans-serif; padding: 20px; }}
.header {{ margin-bottom: 20px; }}
</style></head><body>
<div class="header">
<h2>Emoji Gallery — {len(rows)} emoji</h2>
<p>Review these emoji. To remove unwanted ones:</p>
<ol>
<li>Open the <code>images/</code> folder in Finder (link below)</li>
<li>Delete any images you don't want (Cmd+Delete)</li>
<li>Run: <code>python emoji_download.py sync --input {input_dir}</code></li>
</ol>
<p><a href="file://{images_dir.resolve()}">Open images folder in Finder</a></p>
</div>
{"".join(rows)}
</body></html>"""

    with open(gallery_path, "w") as f:
        f.write(html)

    print(f"Gallery: {gallery_path}")
    print(f"  {len(rows)} emoji displayed.")
    print(f"\nOpening in browser ...")
    os.system(f'open "{gallery_path}"')
    print(f"\nAfter deleting unwanted images, run:")
    print(f"  python emoji_download.py sync --input {input_dir}")


# ---------------------------------------------------------------------------
# Sync (prune manifest to match remaining images)
# ---------------------------------------------------------------------------

def run_sync(args):
    input_dir = Path(args.input)
    manifest_path = input_dir / "manifest.json"
    images_dir = input_dir / "images"

    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    before = len(manifest["emoji"])
    kept = []
    removed = []
    for e in manifest["emoji"]:
        candidates = list(images_dir.glob(f"{e['name']}.*"))
        if candidates:
            kept.append(e)
        else:
            removed.append(e["name"])

    manifest["emoji"] = kept
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Synced manifest: {before} -> {len(kept)} emoji ({len(removed)} removed).")
    if removed and len(removed) <= 20:
        print(f"  Removed: {', '.join(removed)}")
    elif removed:
        print(f"  Removed: {', '.join(removed[:20])} ... and {len(removed) - 20} more")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

HELP_EPILOG = """
AUTH GUIDE
==========

TOKENS YOU NEED:

  1. Bot token ($SLACK_BOT_TOKEN or --token):
     xoxb-... with 'emoji:read' and 'reactions:read' scopes.
     -> https://api.slack.com/apps -> Create New App (one per workspace/org)
     -> OAuth & Permissions -> Bot Token Scopes -> add emoji:read, reactions:read
     -> Install to Workspace -> copy "Bot User OAuth Token"

  2. User token ($SLACK_USER_TOKEN or --user-token):
     xoxp-... with 'reactions:read' scope.
     -> Same app -> OAuth & Permissions -> User Token Scopes -> add reactions:read
     -> Reinstall if needed -> copy "User OAuth Token"

  3. Session token (--session-token):
     xoxc-... grabbed from browser DevTools.
     -> Open Slack in Chrome -> DevTools (Cmd+Opt+I) -> Network tab
     -> Filter for "/api/" -> click any request
     -> In the request payload, find "token": "xoxc-..."
     NOTE: This token rotates -- grab a fresh one each session.

  4. d cookie (AUTO-READ from Chrome):
     No manual step! Just be logged into Slack in Chrome.

  5. User ID (--user-id):
     -> Slack profile -> "..." menu -> "Copy member ID"

EXPORT MODES:
  uploaded  -- emoji YOU uploaded (needs session-token)
  used      -- emoji you've reacted with (needs bot-token + user-token)
  both      -- union of uploaded + used
"""


def main():
    parser = argparse.ArgumentParser(
        description="Download custom emoji from a Slack workspace",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # -- export --
    exp = sub.add_parser("export", help="Export emoji from a workspace (additive-only)")
    exp.add_argument("--mode", choices=["uploaded", "used", "both"], default="both",
                     help="What to export (default: both)")
    exp.add_argument("--user-id", required=True,
                     help="Your Slack member ID (profile -> ... -> Copy member ID)")
    exp.add_argument("--token", default=None,
                     help="Bot token xoxb- (or $SLACK_BOT_TOKEN)")
    exp.add_argument("--user-token", default=None,
                     help="User token xoxp- (or $SLACK_USER_TOKEN)")
    exp.add_argument("--session-token", default=None,
                     help="Session token xoxc- (from Chrome DevTools Network tab)")
    exp.add_argument("--output", default="./my-emoji",
                     help="Output directory (default: ./my-emoji)")

    # -- review --
    rev = sub.add_parser("review", help="Open HTML gallery to visually review exported emoji")
    rev.add_argument("--input", default="./my-emoji",
                     help="Input directory with manifest.json (default: ./my-emoji)")

    # -- sync --
    syn = sub.add_parser("sync", help="Prune manifest to match remaining images (after deleting in Finder)")
    syn.add_argument("--input", default="./my-emoji",
                     help="Input directory with manifest.json (default: ./my-emoji)")

    args = parser.parse_args()
    if args.command == "export":
        run_export(args)
    elif args.command == "review":
        run_review(args)
    elif args.command == "sync":
        run_sync(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
