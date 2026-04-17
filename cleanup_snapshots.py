#!/usr/bin/env python3
"""
SeeWhozThere® Automated Snapshot Cleanup Utility

This script safely removes old snapshot images and their corresponding
database sighting records to free up disk space on the Raspberry Pi.

It does NOT delete:
- Known visitor profiles
- Visitor thumbnail images
- Face encodings used by the AI model

Usage:
  python3 cleanup_snapshots.py --days 7
"""

import os
import sqlite3
import argparse
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

def cleanup_old_sightings(days_to_keep: int):
    """
    Delete sightings and snapshots older than the specified number of days.
    """
    if not DB_PATH.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info(f"Starting SeeWhozThere® cleanup...")
    logger.info(f"Target: Remove sightings and snapshots older than {cutoff_str} ({days_to_keep} days)")

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
            logger.info("No old sightings found to clean up. Disk space is safe!")
            conn.close()
            return

        logger.info(f"Found {len(old_sightings)} old sightings to remove.")

        # 2. Delete the physical snapshot files
        files_deleted = 0
        bytes_freed = 0
        
        for row in old_sightings:
            snapshot_path = row['snapshot_path']
            if not snapshot_path:
                continue
                
            # Handle both relative paths ('data/snapshots/...') and absolute paths
            if snapshot_path.startswith('data/'):
                full_path = PROJECT_ROOT / snapshot_path
            else:
                # Fallback for just filenames
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
        logger.info(f"Deleted {files_deleted} snapshot images, freeing {mb_freed:.2f} MB of disk space.")

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
        
        logger.info(f"Successfully removed {records_deleted} sighting records from the database.")
        
    except sqlite3.Error as e:
        logger.error(f"Database error occurred: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SeeWhozThere® Snapshot Cleanup")
    parser.add_argument(
        "--days", 
        type=int, 
        default=7,
        help="Number of days of history to keep (default: 7)"
    )
    args = parser.parse_args()
    
    cleanup_old_sightings(args.days)
