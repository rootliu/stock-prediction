#!/usr/bin/env python3
"""Daily sentiment archive — writes one JSON snapshot per day.

Runs once per day (via cron). Calls `survey_event_sentiment(now)` and
persists the result to `ml-service/data/sentiment_snapshots/YYYY-MM-DD.json`
so later stages can build historical sentiment features.

Usage:
    python scripts/archive_sentiment.py           # today's snapshot
    python scripts/archive_sentiment.py --force   # re-run even if exists

Suggested cron (mac):
    0 19 * * * /usr/bin/python3 \\
        /Users/rootliu/code/stock-prediction/scripts/archive_sentiment.py \\
        >> /tmp/sentiment_archive.log 2>&1
"""

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_SERVICE = REPO_ROOT / "ml-service"
if str(ML_SERVICE) not in sys.path:
    sys.path.insert(0, str(ML_SERVICE))


def _snapshot_path(snap_dir: Path, date_str: str) -> Path:
    return snap_dir / f"{date_str}.json"


def run_once(force: bool = False, window_days: int = 7,
             max_items_per_feed: int = 6) -> dict:
    import pandas as pd  # local import for cleaner errors
    from models.event_sentiment import survey_event_sentiment

    snap_dir = ML_SERVICE / "data" / "sentiment_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)

    now = pd.Timestamp.now(tz="UTC").tz_convert(None)
    date_str = now.strftime("%Y-%m-%d")
    out_path = _snapshot_path(snap_dir, date_str)

    if out_path.exists() and not force:
        print(f"[skip] {out_path} already exists; use --force to overwrite")
        return {"skipped": True, "path": str(out_path)}

    try:
        survey = survey_event_sentiment(
            now=now,
            window_days=window_days,
            max_items_per_feed=max_items_per_feed,
        )
        payload = {
            "snapshot_date": date_str,
            "snapshot_time_utc": datetime.now(timezone.utc).isoformat(),
            "window_days": window_days,
            "feature_summary": survey.get("feature_summary", {}),
            "article_count": len(survey.get("articles", [])),
            "top_bull": [
                {"title": a.get("title"), "site": a.get("site"),
                 "bull_score": a.get("bull_score"), "tags": a.get("tags")}
                for a in survey.get("top_bull", [])
            ],
            "top_bear": [
                {"title": a.get("title"), "site": a.get("site"),
                 "bear_score": a.get("bear_score"), "tags": a.get("tags")}
                for a in survey.get("top_bear", [])
            ],
            "error": None,
        }
    except Exception as exc:
        payload = {
            "snapshot_date": date_str,
            "snapshot_time_utc": datetime.now(timezone.utc).isoformat(),
            "window_days": window_days,
            "feature_summary": {},
            "article_count": 0,
            "top_bull": [],
            "top_bear": [],
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"[ok] wrote {out_path} (articles={payload['article_count']}, "
          f"error={bool(payload['error'])})")
    return {"skipped": False, "path": str(out_path), "payload": payload}


def main():
    parser = argparse.ArgumentParser(description="Archive daily sentiment snapshot")
    parser.add_argument("--force", action="store_true",
                        help="overwrite today's snapshot even if exists")
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--max-items-per-feed", type=int, default=6)
    args = parser.parse_args()
    run_once(force=args.force, window_days=args.window_days,
             max_items_per_feed=args.max_items_per_feed)


if __name__ == "__main__":
    main()
