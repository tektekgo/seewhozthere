#!/usr/bin/env python3
"""
SeeWhozThere® Automated Snapshot Cleanup Utility

This script safely removes old snapshot images and their corresponding
database sighting records to free up disk space on the Raspberry Pi.

It does NOT delete:
- Known visitor profiles
- Visitor thumbnail images
- Face encodings used by the AI model

After a successful run, a summary notification is sent via Telegram.

Usage:
  python3 cleanup_snapshots.py --days 7
"""

import os
import sqlite3
import argparse
import configparser
import urllib.request
import json
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SeeWhozThere-Cleanup")

# Paths
PROJECT_ROOT = Path(__file__).parent.resolve()
DB_PATH = PROJECT_ROOT / "data" / "seewhozthere.db"
SNAPSHOTS_DIR = PROJECT_ROOT / "data" / "snapshots"
CONFIG_PATH = PROJECT_ROOT / "config.ini"


def load_telegram_config():
    """Read bot_token and chat_id from config.ini."""
    config = configparser.RawConfigParser()
    config.read(CONFIG_PATH)
    try:
        bot_token = config.get("TELEGRAM", "bot_token").strip()
        chat_id = config.get("TELEGRAM", "chat_id").strip()
        return bot_token, chat_id
    except (configparser.NoSectionError, configparser.NoOptionError):
        return None, None


def send_telegram_message(bot_token: str, chat_id: str, text: str):
    """Send a message via the Telegram Bot API."""
    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured — skipping notification.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info("Telegram notification sent successfully.")
            else:
                logger.warning(f"Telegram API returned status {resp.status}.")
    except Exception as e:
        logger.warning(f"Could not send Telegram notification: {e}")


def cleanup_old_sightings(days_to_keep: int):
    """
    Delete sightings and snapshots older than the specified number of days.
    Returns a summary dict of what was done, or None on error.
    """
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return None

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")

    logger.info("Starting SeeWhozThere® cleanup...")
    logger.info(f"Target: Remove sightings and snapshots older than {cutoff_str} ({days_to_keep} days)")

    files_deleted = 0
    bytes_freed = 0
    records_deleted = 0

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Find all sightings older than the cutoff date
        cursor.execute(
            "SELECT id, snapshot_path FROM sightings WHERE timestamp < ?",
            (cutoff_str,)
        )
        old_sightings = cursor.fetchall()

        if not old_sightings:
            logger.info("No old sightings found. Disk space is safe!")
            conn.close()
            return {
                "files_deleted": 0,
                "mb_freed": 0.0,
                "records_deleted": 0,
                "days_kept": days_to_keep,
                "nothing_to_do": True
            }

        logger.info(f"Found {len(old_sightings)} old sightings to remove.")

        # 2. Delete the physical snapshot files
        for row in old_sightings:
            snapshot_path = row['snapshot_path']
            if not snapshot_path:
                continue

            if snapshot_path.startswith('data/'):
                full_path = PROJECT_ROOT / snapshot_path
            else:
                full_path = SNAPSHOTS_DIR / os.path.basename(snapshot_path)

            if full_path.exists() and full_path.is_file():
                try:
                    size = full_path.stat().st_size
                    full_path.unlink()
                    files_deleted += 1
                    bytes_freed += size
                except Exception as e:
                    logger.warning(f"Could not delete file {full_path}: {e}")

        mb_freed = bytes_freed / (1024 * 1024)
        logger.info(f"Deleted {files_deleted} snapshot images, freeing {mb_freed:.2f} MB.")

        # 3. Delete the records from the database
        cursor.execute(
            "DELETE FROM sightings WHERE timestamp < ?",
            (cutoff_str,)
        )
        records_deleted = cursor.rowcount
        conn.commit()

        # 4. Optimize the database (VACUUM reclaims empty space)
        logger.info("Vacuuming database to reclaim space...")
        cursor.execute("VACUUM")
        conn.commit()

        logger.info(f"Successfully removed {records_deleted} sighting records from the database.")

    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

    return {
        "files_deleted": files_deleted,
        "mb_freed": round(mb_freed, 2),
        "records_deleted": records_deleted,
        "days_kept": days_to_keep,
        "nothing_to_do": False
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SeeWhozThere® Snapshot Cleanup")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days of history to keep (default: 7)"
    )
    args = parser.parse_args()

    result = cleanup_old_sightings(args.days)

    # Load Telegram credentials from config.ini
    bot_token, chat_id = load_telegram_config()
    run_time = datetime.now().strftime("%b %d, %Y at %I:%M %p")

    if result is None:
        # Something went wrong — send a failure alert
        message = (
            "⚠️ <b>SeeWhozThere® — Cleanup Failed</b>\n\n"
            f"🕑 {run_time}\n\n"
            "The automated snapshot cleanup encountered an error.\n"
            "Please check the cleanup log on your Raspberry Pi:\n"
            "<code>cat ~/projects/seewhozthere/cleanup.log</code>\n\n"
            "<i>— SeeWhozThere®</i>"
        )
        send_telegram_message(bot_token, chat_id, message)

    elif result["nothing_to_do"]:
        # Nothing old enough to delete — send a brief status
        message = (
            "🧹 <b>SeeWhozThere® — Storage Cleanup</b>\n\n"
            f"✅ Ran on {run_time}\n"
            f"📁 Nothing to delete — all snapshots are within the last {result['days_kept']} days.\n\n"
            "<i>— SeeWhozThere®</i>"
        )
        send_telegram_message(bot_token, chat_id, message)

    else:
        # Successful cleanup — send a full summary
        message = (
            "🧹 <b>SeeWhozThere® — Storage Cleanup Complete</b>\n\n"
            f"🕑 {run_time}\n"
            f"🗑️ Snapshots deleted: <b>{result['files_deleted']}</b>\n"
            f"💾 Disk space freed: <b>{result['mb_freed']} MB</b>\n"
            f"📋 Database records removed: <b>{result['records_deleted']}</b>\n"
            f"📅 History kept: last <b>{result['days_kept']} days</b>\n\n"
            "<i>— SeeWhozThere®</i>"
        )
        send_telegram_message(bot_token, chat_id, message)
