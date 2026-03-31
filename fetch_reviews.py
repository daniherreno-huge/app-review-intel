#!/usr/bin/env python3
"""
App Review Intel — Weekly fetcher
Runs every Monday, updates the HTML dashboard with new App Store + Google Play
reviews, then fires a macOS notification.
"""

import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

HTML_PATH = Path(__file__).parent / "app_review_miner.html"
CUTOFF_DAYS = 7  # how far back to fetch reviews

APPS = {
    "vail": {
        "appstore_id": "395375487",
        "gplay_id": "com.vailresorts.epicmix",
        "name": "My Epic / Vail",
    },
    "ikon": {
        "appstore_id": "1482191120",
        "gplay_id": "com.alterramtnco.ikonpass",
        "name": "Ikon Pass",
    },
}


def stars(rating: int) -> str:
    return "★" * rating + "☆" * (5 - rating)


def fetch_appstore_reviews(app_id: str, since_date) -> list:
    reviews = []
    for page in range(1, 11):
        url = (
            f"https://itunes.apple.com/us/rss/customerreviews/"
            f"page={page}/id={app_id}/sortBy=mostRecent/json"
        )
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  [App Store] page {page} error: {e}", file=sys.stderr)
            break

        entries = data.get("feed", {}).get("entry", [])
        if not entries:
            break

        found_old = False
        for entry in entries:
            if "im:rating" not in entry:
                continue
            rating = int(entry["im:rating"]["label"])
            title = entry["title"]["label"]
            content = entry["content"]["label"]
            date_str = entry["updated"]["label"][:10]
            date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if date < since_date:
                found_old = True
                continue

            reviews.append({
                "rating": rating,
                "title": title,
                "content": content,
                "date": date_str,
            })

        if found_old:
            break

    return reviews


def fetch_gplay_reviews(package_id: str, since_date) -> list:
    try:
        from google_play_scraper import reviews as gplay_reviews, Sort
    except ImportError:
        print("  [Google Play] google-play-scraper not installed, skipping.", file=sys.stderr)
        return []

    results = []
    try:
        entries, _ = gplay_reviews(
            package_id,
            lang="en",
            country="us",
            sort=Sort.NEWEST,
            count=200,
        )
        for entry in entries:
            date = entry["at"].date()
            if date < since_date:
                continue
            rating = entry["score"]
            title = (entry.get("userName") or "")[:40]
            content = (entry.get("content") or "").strip()
            date_str = date.isoformat()
            if not content:
                continue
            results.append({
                "rating": rating,
                "title": title or content[:30],
                "content": content,
                "date": date_str,
            })
    except Exception as e:
        print(f"  [Google Play] error: {e}", file=sys.stderr)

    return results


def format_review_lines(reviews: list) -> str:
    lines = []
    for r in reviews:
        title = r["title"].replace("|", "-").replace("`", "'").strip()
        content = r["content"].replace("|", "-").replace("`", "'").strip()
        if not title and not content:
            continue
        lines.append(f"{stars(r['rating'])} | {r['date']} | {title} | {content}")
    return "\n".join(lines)


def update_html(app_key: str, new_lines: str):
    html = HTML_PATH.read_text(encoding="utf-8")

    pattern = rf"({re.escape(app_key)}:\s*`)(.*?)(`)"

    def replacer(m):
        existing = m.group(2).strip()
        combined = new_lines + ("\n" + existing if existing else "")
        # Deduplicate by first 80 chars of each line
        seen: set = set()
        deduped = []
        for line in combined.split("\n"):
            key = line[:80]
            if key and key not in seen:
                seen.add(key)
                deduped.append(line)
        # Cap at 300 reviews to keep the file manageable
        return m.group(1) + "\n".join(deduped[:300]) + m.group(3)

    updated = re.sub(pattern, replacer, html, flags=re.DOTALL)
    HTML_PATH.write_text(updated, encoding="utf-8")


def notify(title: str, message: str):
    script = f'display notification "{message}" with title "{title}" sound name "default"'
    subprocess.run(["osascript", "-e", script], check=False)


def main():
    since_date = (datetime.now() - timedelta(days=CUTOFF_DAYS)).date()
    print(f"Fetching reviews since {since_date}...\n")

    totals = {}
    for app_key, app in APPS.items():
        print(f"→ {app['name']}")
        ios = fetch_appstore_reviews(app["appstore_id"], since_date)
        android = fetch_gplay_reviews(app["gplay_id"], since_date)
        all_reviews = sorted(ios + android, key=lambda r: r["date"], reverse=True)
        print(f"  iOS: {len(ios)}  Android: {len(android)}")
        totals[app_key] = len(all_reviews)

        if all_reviews:
            update_html(app_key, format_review_lines(all_reviews))

    total_new = sum(totals.values())
    vail_n = totals.get("vail", 0)
    ikon_n = totals.get("ikon", 0)

    # Commit and push to GitHub so the Pages URL is always current
    repo_dir = HTML_PATH.parent
    today = datetime.now().strftime("%Y-%m-%d")
    subprocess.run(["git", "-C", str(repo_dir), "add", "app_review_miner.html"], check=False)
    subprocess.run(
        ["git", "-C", str(repo_dir), "commit", "-m", f"Weekly review update {today} — {total_new} new reviews"],
        check=False,
    )
    subprocess.run(["git", "-C", str(repo_dir), "push"], check=False)
    print("  Pushed to GitHub.")

    notify(
        "App Review Intel",
        f"{total_new} new reviews this week (Vail: {vail_n} · Ikon: {ikon_n}) — dashboard updated",
    )

    dashboard = HTML_PATH.resolve()
    subprocess.run(["open", str(dashboard)], check=False)

    print(f"\nDone. {total_new} new reviews. Dashboard opened.")


if __name__ == "__main__":
    main()
