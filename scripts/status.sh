#!/usr/bin/env bash
# Show current generation status. Run on the box (or via ssh host "bash .../status.sh").
#
# Usage:
#   bash scripts/status.sh              # summary
#   bash scripts/status.sh --tail 30    # summary + last N log lines
#   bash scripts/status.sh --watch      # refresh every 30s (Ctrl-C to stop)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_DIR/output/brands"
PROGRESS_FILE="$OUTPUT_DIR/progress.json"
PID_FILE="$OUTPUT_DIR/run.pid"

TAIL_LINES=0
WATCH_MODE=false

for arg in "$@"; do
    case "$arg" in
        --tail)   shift; TAIL_LINES="${1:-20}" ;;
        --watch)  WATCH_MODE=true ;;
        --help|-h)
            echo "Usage: $0 [--tail N] [--watch]"
            exit 0
            ;;
    esac
done

print_status() {
    echo ""
    echo "=== Vishru Brand Generation Status  $(date '+%Y-%m-%d %H:%M:%S') ==="

    # ── Process check ──────────────────────────────────────────────────────────
    if [[ -f "$PID_FILE" ]]; then
        PID="$(cat "$PID_FILE")"
        if kill -0 "$PID" 2>/dev/null; then
            echo "Process : RUNNING  (PID $PID)"
        else
            echo "Process : STOPPED  (PID $PID — no longer alive)"
        fi
    else
        echo "Process : not started  (no run.pid)"
    fi

    # ── File count (ground truth) ──────────────────────────────────────────────
    if [[ -d "$OUTPUT_DIR" ]]; then
        FILE_COUNT=$(find "$OUTPUT_DIR" -name "*.jpg" | wc -l | tr -d ' ')
        echo "Files   : $FILE_COUNT .jpg files in output/brands/"
    fi

    # ── Progress JSON ──────────────────────────────────────────────────────────
    if [[ ! -f "$PROGRESS_FILE" ]]; then
        echo "Progress: no progress.json yet — generation hasn't started"
        echo ""
        return
    fi

    # Parse with python3 (always available in venv)
    python3 - "$PROGRESS_FILE" <<'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    p = json.load(f)

done      = p.get("done", 0)
total     = p.get("total", 0)
remaining = p.get("remaining", 0)
pct       = int(done / total * 100) if total else 0
bar_len   = 30
filled    = int(bar_len * done / total) if total else 0
bar       = "█" * filled + "░" * (bar_len - filled)

last      = p.get("last", "—")
saved_at  = p.get("last_saved_at", "—")
elapsed   = p.get("elapsed_min", 0)
avg       = p.get("avg_sec_per_image", 0)
eta       = p.get("eta_min", 0)

print(f"Progress: [{bar}] {done}/{total} ({pct}%)")
print(f"Last    : {last}  @ {saved_at}")
print(f"Speed   : ~{avg:.0f}s/image  |  Elapsed: {elapsed:.1f}m  |  ETA: ~{eta:.0f}m")

if last == "COMPLETE":
    print("Status  : ✓ COMPLETE")
PYEOF

    # ── Active log file ────────────────────────────────────────────────────────
    LATEST_LOG=$(find "$OUTPUT_DIR" -name "run-*.log" | sort | tail -1)
    if [[ -n "$LATEST_LOG" ]]; then
        echo "Log     : $LATEST_LOG"
        if [[ "$TAIL_LINES" -gt 0 ]]; then
            echo ""
            echo "── last $TAIL_LINES lines ──────────────────────────────────"
            tail -n "$TAIL_LINES" "$LATEST_LOG"
        fi
    fi

    echo ""
}

if $WATCH_MODE; then
    while true; do
        clear
        print_status
        echo "Refreshing every 30s  (Ctrl-C to stop)"
        sleep 30
    done
else
    print_status
fi
