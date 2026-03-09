#!/usr/bin/env python3
"""Upload custom emoji to a Slack workspace from a previously exported manifest.

See README.md for setup instructions, or run with --help for auth details.
Requires: pip install requests browser_cookie3
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def read_d_cookie_from_chrome():
    """Auto-read the Slack 'd' cookie from Chrome's cookie store.

    Requires: pip install browser_cookie3
    No manual step -- reads directly from Chrome's local storage.
    Just be logged into the DESTINATION workspace in Chrome.
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
    print("  Make sure you're logged into the DESTINATION workspace in Chrome.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_emoji_image(workspace, cookie, xoxc_token, name, image_path):
    with open(image_path, "rb") as f:
        resp = requests.post(
            f"https://{workspace}.slack.com/api/emoji.add",
            headers={"Cookie": f"d={cookie}"},
            data={"mode": "data", "name": name, "token": xoxc_token},
            files={"image": (image_path.name, f)},
        )
    resp.raise_for_status()
    return resp.json()


def upload_alias(workspace, cookie, xoxc_token, alias_name, original_name):
    resp = requests.post(
        f"https://{workspace}.slack.com/api/emoji.add",
        headers={"Cookie": f"d={cookie}"},
        data={
            "mode": "alias",
            "name": alias_name,
            "alias_for": original_name,
            "token": xoxc_token,
        },
    )
    resp.raise_for_status()
    return resp.json()


def run_upload(args):
    workspace = args.workspace
    xoxc = args.session_token or os.environ.get("SLACK_SESSION_TOKEN")
    input_dir = Path(args.input)
    manifest_path = input_dir / "manifest.json"
    images_dir = input_dir / "images"

    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found.", file=sys.stderr)
        sys.exit(1)

    if not xoxc:
        print("Error: --session-token is required for upload.", file=sys.stderr)
        print("  Get it: open DESTINATION workspace in Chrome -> DevTools (Cmd+Opt+I) -> Network tab", file=sys.stderr)
        print("  -> filter '/api/' -> click any request -> find 'token' in request payload", file=sys.stderr)
        sys.exit(1)

    # Auto-read d cookie from Chrome
    print("Reading d cookie from Chrome ...")
    d_cookie = read_d_cookie_from_chrome()
    print("  Got d cookie. Make sure you're logged into the DESTINATION workspace in Chrome.")

    with open(manifest_path) as f:
        manifest = json.load(f)

    # Resume support -- tracks successfully uploaded emoji so re-runs skip them
    uploaded_file = input_dir / ".uploaded"
    already_uploaded = set()
    if uploaded_file.exists():
        already_uploaded = set(uploaded_file.read_text().splitlines())

    emoji_list_data = manifest["emoji"]
    to_upload = [e for e in emoji_list_data if e["name"] not in already_uploaded]
    print(f"Uploading {len(to_upload)} emoji ({len(already_uploaded)} already done) ...")

    with open(uploaded_file, "a") as tracker:
        for i, e in enumerate(to_upload):
            name = e["name"]
            candidates = list(images_dir.glob(f"{name}.*"))
            if not candidates:
                print(f"  SKIP {name}: no image file found")
                continue

            image_path = candidates[0]
            result = upload_emoji_image(workspace, d_cookie, xoxc, name, image_path)

            if result.get("ok"):
                print(f"  OK   {name}")
                tracker.write(name + "\n")
                tracker.flush()
            elif result.get("error") == "error_name_taken":
                print(f"  EXISTS {name}")
                tracker.write(name + "\n")
                tracker.flush()
            elif result.get("error") == "ratelimited":
                wait = int(result.get("retry_after", 5))
                print(f"  RATE LIMITED -- waiting {wait}s ...")
                time.sleep(wait)
                result = upload_emoji_image(workspace, d_cookie, xoxc, name, image_path)
                if result.get("ok") or result.get("error") == "error_name_taken":
                    tracker.write(name + "\n")
                    tracker.flush()
                else:
                    print(f"  FAIL {name}: {result.get('error')}")
            else:
                print(f"  FAIL {name}: {result.get('error')}")

            if (i + 1) % 10 == 0:
                time.sleep(1)

    # Aliases
    print("Creating aliases ...")
    for e in emoji_list_data:
        for alias in e.get("aliases", []):
            if alias in already_uploaded:
                continue
            result = upload_alias(workspace, d_cookie, xoxc, alias, e["name"])
            if result.get("ok"):
                print(f"  ALIAS {alias} -> {e['name']}")
            elif result.get("error") == "error_name_taken":
                print(f"  EXISTS {alias}")
            else:
                print(f"  FAIL alias {alias}: {result.get('error')}")
            time.sleep(0.5)

    print("Done.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

HELP_EPILOG = """
AUTH GUIDE
==========

You need TWO things, both from the DESTINATION workspace:

  1. Session token (--session-token):
     xoxc-... grabbed from browser DevTools.
     -> Open the DESTINATION Slack workspace in Chrome
     -> DevTools (Cmd+Opt+I) -> Network tab
     -> Filter for "/api/" -> click any request
     -> In the request payload, find "token": "xoxc-..."
     NOTE: This token rotates -- grab a fresh one each session.

  2. d cookie (AUTO-READ from Chrome):
     No manual step! Just be logged into the DESTINATION workspace in Chrome.

RESUME SUPPORT:
  Tracks uploaded emoji in .uploaded file. Safe to re-run if interrupted --
  already-uploaded emoji will be skipped.
"""


def main():
    parser = argparse.ArgumentParser(
        description="Upload custom emoji to a Slack workspace",
        epilog=HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--workspace", required=True,
                        help="Destination workspace subdomain (e.g. 'neworg' for neworg.slack.com)")
    parser.add_argument("--session-token", default=None,
                        help="Session token xoxc- from DESTINATION workspace (Chrome DevTools)")
    parser.add_argument("--input", default="./my-emoji",
                        help="Input directory with manifest.json + images/ (default: ./my-emoji)")

    args = parser.parse_args()
    run_upload(args)


if __name__ == "__main__":
    main()
