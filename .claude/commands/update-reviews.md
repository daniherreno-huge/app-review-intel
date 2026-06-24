# /update-reviews

Fetch new app reviews, classify them with LLM, and push the updated dashboard to GitHub.

## Context

- Main HTML file: `index.html` in the repo root
- Review data is embedded in the HTML as template-literal strings under `vail:` and `ikon:` keys
- Each review line format: `★★★☆☆ | YYYY-MM-DD | title | content | platform | category`
- `platform` is `ios` or `android`; `category` is one of the known categories below
- Lines with only 5 fields (no category) are **unclassified** and need to be tagged

## Valid categories

`crash`, `gps_tracking`, `pass_display`, `regression`, `slow_performance`, `bad_ux`, `notification_spam`, `feature_request`, `competitor_better`, `positive`, `none`

## Steps

### Step 1 — Fetch new reviews

Run from the repo root:

```bash
python3 fetch_reviews.py
```

This fetches the last 7 days of reviews from App Store and Google Play, prepends them to `index.html`, deduplicates, and pushes to GitHub. New reviews come in without a category.

### Step 2 — Extract unclassified reviews

Read `index.html` and extract all review lines that are missing a category. A line is unclassified if splitting by ` | ` gives exactly 5 fields (stars, date, title, content, platform) or if the 6th field is not one of the valid categories.

Do this separately for `vail` and `ikon` blocks. Write unclassified lines to temp files:
- `/tmp/vail_unclassified.txt`
- `/tmp/ikon_unclassified.txt`

If both files are empty, print "All reviews already classified. Nothing to do." and stop.

### Step 3 — Classify with LLM

For each app that has unclassified reviews, split into chunks of 50 lines and run a Workflow to classify them in parallel. Each agent receives a batch and must return each line with the correct category appended, separated by ` | `.

**Classification prompt per agent:**
```
You are classifying app store reviews for a ski/resort mobile app.

For each review line below, append the correct category at the end, separated by " | ".

Valid categories:
- crash — app crashes, freezes, won't open, force closes
- gps_tracking — GPS fails, stats not recording, vertical/distance wrong, tracking drops
- pass_display — season pass won't load, lift scan fails, pass not showing, offline access
- regression — something that worked before is now broken after an update
- slow_performance — app is slow, laggy, takes long to load
- bad_ux — confusing navigation, poor UI, hard to use, missing info
- notification_spam — too many notifications, unwanted alerts
- feature_request — asking for a new feature or improvement that doesn't exist yet
- competitor_better — mentions another app (Ikon, OnTheSnow, Strava, EpicMix, etc.) as better
- positive — overall positive experience, praise, high rating with good feedback
- none — doesn't fit any category above

Input lines (keep each line intact, only append the category):
{lines}

Return the same lines with category appended. One line per review. No explanation.
```

### Step 4 — Write categories back

For each classified line returned by the agents, match it to the original unclassified line by comparing the first 80 characters (normalized: convert Unicode quotes `'` `'` `"` `"` to straight quotes). When matched, append the category to the original line in `index.html`.

Use Python to do the find-and-replace in `index.html`. Be careful to only replace exact matches inside the correct app block.

### Step 5 — Commit and push

```bash
git add index.html
git commit -m "Classify new reviews — $(date +%Y-%m-%d)"
git push
```

Print a summary: how many reviews were classified for each app.

## Notes

- If `fetch_reviews.py` fails (missing dependencies, network error), stop and report the error — don't proceed to classification.
- If classification returns a line with an invalid category, use `none`.
- Always normalize Unicode apostrophes/quotes when matching lines.
- The `fetch_reviews.py` script already handles the GitHub push for the raw reviews. The final push in Step 5 is for the classified version.
