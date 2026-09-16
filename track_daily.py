"""
CLI Automated Daily Tracking Script for SocialIQ.
Can be run manually or scheduled via cron / macOS launchd / Windows Task Scheduler
to capture daily snapshots of social media accounts into SQLite database.

Usage examples:
    # Track specific handles:
    python track_daily.py --platform Instagram --handles shopee_id tokopedia bliblidotcom

    # Automatically refresh all handles currently stored in database:
    python track_daily.py
"""

from __future__ import annotations
import argparse
import datetime
import logging
import sys

from services.data_fetcher import LiveWebScraperService
from services.storage import storage_service
from utils.helpers import clean_handle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("track_daily")


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Social Media Metric Snapshot Tracker")
    parser.add_argument(
        "--platform",
        type=str,
        default="Instagram",
        help="Target platform (Instagram, Threads, TikTok)",
    )
    parser.add_argument(
        "--handles",
        nargs="*",
        default=[],
        help="List of handles to scrape and record (e.g. --handles shopee_id tokopedia)",
    )
    args = parser.parse_args()

    platform = args.platform.capitalize()
    handles_to_track = [clean_handle(h) for h in args.handles if clean_handle(h)]

    # If no handles provided, query existing handles tracked in SQLite DB
    if not handles_to_track:
        logger.info("No handles specified. Scanning database for previously tracked accounts...")
        existing_df = storage_service.export_history_df()
        if not existing_df.empty and "handle" in existing_df.columns:
            handles_to_track = sorted(list(set(existing_df["handle"].dropna().tolist())))
            logger.info("Found %d tracked accounts in database: %s", len(handles_to_track), handles_to_track)
        else:
            logger.warning(
                "Database is empty and no handles were provided. "
                "Please run with: python track_daily.py --handles <handle1> <handle2>"
            )
            return

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=7)

    logger.info("Starting daily snapshot collection for %d accounts on %s (Date: %s)", len(handles_to_track), platform, today)
    scraper = LiveWebScraperService(enable_backfill=False)

    success_count = 0
    for handle in handles_to_track:
        logger.info("--> Fetching live metrics for @%s ...", handle)
        try:
            res = scraper.fetch_account_data(
                platform=platform,
                raw_account=handle,
                start_date=start_date,
                end_date=today,
                enable_backfill=False,
            )
            followers = res.get("followers", 0)
            posts_count = len(res.get("posts", []))
            logger.info("✓ @%s: %s followers, %d posts parsed. Snapshot saved.", handle, f"{followers:,}", posts_count)
            success_count += 1
        except Exception as e:
            logger.error("✗ Failed to track @%s: %s", handle, e)

    logger.info("Daily tracking finished. Successfully updated %d/%d accounts.", success_count, len(handles_to_track))


if __name__ == "__main__":
    main()
