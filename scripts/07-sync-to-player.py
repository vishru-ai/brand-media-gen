#!/usr/bin/env python3
"""
Sync generated content stores to a signage player's review queue.

Reads the per-type JSON stores under output/text/ (each: {group: [entries]},
every entry carrying id/mood/model/review fields) and POSTs them to the
player's `/api/generated/sync` endpoint in batches. Items land there as
review="pending" and only go live after a human approves them in the phone
app — the player preserves existing review decisions on re-sync, so running
this repeatedly (e.g. from cron after each generation run) is safe.

Usage:
  python scripts/07-sync-to-player.py --player http://192.168.1.50:8080
  python scripts/07-sync-to-player.py --player http://player:8080 --token <pairing token>
  python scripts/07-sync-to-player.py --player ... --types quotes,jokes,facts

Stdlib only — runs on the generation box with no extra deps.
"""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
TEXT_DIR = PROJECT_DIR / "output" / "text"


def load_items(types_filter=None):
    """Flatten every store file into sync items: {type, group, entry}."""
    items = []
    for store_path in sorted(TEXT_DIR.glob("*.json")):
        content_type = store_path.stem
        if types_filter and content_type not in types_filter:
            continue
        try:
            store = json.loads(store_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ! skipping {store_path.name}: {e}", file=sys.stderr)
            continue
        for group, entries in store.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict) and entry.get("id"):
                    items.append({"type": content_type, "group": group, "entry": entry})
    return items


def post_json(player, token, path, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{player.rstrip('/')}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


def post_batch(player, token, batch):
    return post_json(player, token, "/api/generated/sync", {"items": batch})


def sync_programs(player, token):
    """Push the industry programs (signage_programs.py) so the player's card
    rotation honors dayparts/weights per the screen's industry."""
    sys.path.insert(0, str(PROJECT_DIR / "scripts"))
    try:
        import signage_programs as sp
    except ImportError as e:
        print(f"  ! programs not synced (couldn't import signage_programs: {e})", file=sys.stderr)
        return
    programs = {
        industry: [
            {
                "type": seg.type,
                "group": seg.group or "",
                "dayparts": list(seg.dayparts),
                "bands": list(seg.bands),
                "default": seg.default,
                "weight": seg.weight,
            }
            for seg in segments
        ]
        for industry, segments in sp.PROGRAMS.items()
    }
    result = post_json(player, token, "/api/generated/programs", {"programs": programs})
    print(f"programs: {result.get('stored', 0)} industries synced")


def main():
    p = argparse.ArgumentParser(description="Sync generated content to a player's review queue.")
    p.add_argument("--player", required=True, help="Player base URL, e.g. http://192.168.1.50:8080")
    p.add_argument("--token", default="", help="Pairing token (required when the player enforces auth)")
    p.add_argument("--types", default="", help="Comma-separated content types to sync (default: all)")
    p.add_argument("--batch", type=int, default=200, help="Items per request (default: 200)")
    args = p.parse_args()

    types_filter = {t.strip() for t in args.types.split(",") if t.strip()} or None
    items = load_items(types_filter)
    if not items:
        print(f"nothing to sync (no stores under {TEXT_DIR})")
        return

    total = {"received": 0, "new": 0, "updated": 0, "skipped": 0}
    pending = 0
    for i in range(0, len(items), args.batch):
        batch = items[i : i + args.batch]
        result = post_batch(args.player, args.token, batch)
        for key in total:
            total[key] += result.get(key, 0)
        pending = result.get("pending_total", pending)
        print(f"  synced {i + len(batch)}/{len(items)}")

    print(
        f"done: {total['received']} sent, {total['new']} new, "
        f"{total['updated']} updated, {total['skipped']} skipped; "
        f"{pending} now pending review on the player"
    )

    sync_programs(args.player, args.token)


if __name__ == "__main__":
    main()
