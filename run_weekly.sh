#!/bin/zsh
# Weekly review update — fetch + classify + push
# Runs every Monday via cron

cd /Users/daniela.herreno/Developer/app-review-intel

echo "=== $(date) === Starting weekly review update ==="

# Step 1: Fetch new reviews and push raw data
/usr/bin/python3 fetch_reviews.py

# Step 2: Classify any unclassified reviews and push final version
/Users/daniela.herreno/.local/bin/claude -p "run /update-reviews" \
  --allowedTools "Bash,Read,Edit,Write" \
  --dangerously-skip-permissions

echo "=== $(date) === Done ==="
