#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "→ Creating Python virtual environment..."
python3 -m venv "$DIR/.venv"

echo "→ Installing dependencies..."
"$DIR/.venv/bin/pip" install --quiet --upgrade pip
"$DIR/.venv/bin/pip" install --quiet requests google-play-scraper

echo "→ Registering Monday 9 AM schedule with launchd..."
PLIST_SRC="$DIR/com.appreviews.weekly.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.appreviews.weekly.plist"

# Unload first if already loaded (ignore error if not)
launchctl unload "$PLIST_DEST" 2>/dev/null || true
cp "$PLIST_SRC" "$PLIST_DEST"
launchctl load "$PLIST_DEST"

echo ""
echo "✓ Done! The script will run every Monday at 9:00 AM."
echo "  Dashboard: $DIR/app_review_miner.html"
echo "  Logs:      $DIR/logs/"
echo ""
echo "  To run it manually right now:"
echo "  $DIR/.venv/bin/python3 $DIR/fetch_reviews.py"
