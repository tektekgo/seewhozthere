"""
SeeWhozThere Telegram Notifier

Sends two types of messages:
  1. Instant alert  — fired immediately when an unknown face is detected.
  2. Daily summary  — a digest of the day's activity, sent at a configured time.

Configuration (config.ini):
  [TELEGRAM]
  bot_token = 123456789:ABCdef...
  chat_id   = 987654321

  [SCHEDULER]
  enabled    = true
  send_time  = 20:00        ; 24-hour HH:MM in the configured timezone
  service    = telegram
"""

import io
import os
import time
import threading
import requests
from datetime import datetime, date
from typing import Optional

import pytz

from app.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TIMEZONE,
    SCHEDULER_ENABLED,
    SCHEDULER_SEND_TIME,
    SCHEDULER_SERVICE,
)


# ─── Low-level Telegram helpers ──────────────────────────────────────────────

def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"


def _is_configured() -> bool:
    """Return True if both bot_token and chat_id are set."""
    return bool(TELEGRAM_BOT_TOKEN.strip()) and bool(TELEGRAM_CHAT_ID.strip())


def send_message(text: str) -> bool:
    """Send a plain-text message. Returns True on success."""
    if not _is_configured():
        return False
    try:
        resp = requests.post(
            _api_url("sendMessage"),
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        print(f"[Telegram] sendMessage failed: {e}")
        return False


def send_photo(image_path: str, caption: str = "") -> bool:
    """Send a photo with an optional caption. Returns True on success."""
    if not _is_configured():
        return False
    if not image_path or not os.path.exists(image_path):
        return send_message(caption)  # Fall back to text-only
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                _api_url("sendPhoto"),
                data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": f},
                timeout=15,
            )
        return resp.ok
    except Exception as e:
        print(f"[Telegram] sendPhoto failed: {e}")
        return False


# ─── Instant alert ───────────────────────────────────────────────────────────

def send_unknown_face_alert(camera_name: str, snapshot_path: Optional[str] = None):
    """
    Fire an instant alert when an unknown face is detected.

    Args:
        camera_name:   Name of the camera that triggered the detection.
        snapshot_path: Absolute or relative path to the face snapshot image.
    """
    if not _is_configured():
        return

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%H:%M:%S")

    caption = (
        f"<b>Unknown visitor detected</b>\n"
        f"Camera: {camera_name}\n"
        f"Time: {now}"
    )

    if snapshot_path and os.path.exists(snapshot_path):
        send_photo(snapshot_path, caption)
    else:
        send_message(caption)

    print(f"[Telegram] Sent unknown-face alert for {camera_name}")


def send_known_face_alert(visitor_name: str, camera_name: str, snapshot_path: Optional[str] = None):
    """
    Fire an instant alert when a known visitor is recognised.

    Args:
        visitor_name:  Name of the recognised visitor.
        camera_name:   Name of the camera.
        snapshot_path: Path to the face snapshot image.
    """
    if not _is_configured():
        return

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%H:%M:%S")

    caption = (
        f"<b>{visitor_name} spotted</b>\n"
        f"Camera: {camera_name}\n"
        f"Time: {now}"
    )

    if snapshot_path and os.path.exists(snapshot_path):
        send_photo(snapshot_path, caption)
    else:
        send_message(caption)

    print(f"[Telegram] Sent known-face alert for {visitor_name} on {camera_name}")


# ─── Daily summary ────────────────────────────────────────────────────────────

def send_daily_summary():
    """
    Send a daily activity summary via Telegram.
    Reads today's sightings directly from the database.
    """
    if not _is_configured():
        print("[Telegram] Daily summary skipped — not configured.")
        return

    from app.database import get_db

    db = get_db()
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).date()

    # Fetch today's sightings
    summary = db.get_today_summary()
    stats = db.get_statistics()

    total_sightings = sum(v.get("sighting_count", 0) for v in summary)
    known_count = sum(1 for v in summary if v.get("visitor_id") and v["visitor_id"] != 0)
    unknown_count = len(summary) - known_count

    lines = [
        f"<b>SeeWhozThere Daily Summary</b>",
        f"Date: {today.strftime('%A, %B %d %Y')}",
        "",
        f"Total sightings today: <b>{total_sightings}</b>",
        f"Known visitors: <b>{known_count}</b>",
        f"Unknown visitors: <b>{unknown_count}</b>",
        f"Total known people in database: <b>{stats.get('total_visitors', 0)}</b>",
    ]

    if summary:
        lines.append("")
        lines.append("<b>Who was seen:</b>")
        for v in summary[:10]:  # Cap at 10 to avoid message length limits
            name = v.get("name", "Unknown")
            count = v.get("sighting_count", 0)
            first = v.get("first_seen")
            first_str = first.strftime("%H:%M") if first and hasattr(first, "strftime") else str(first or "")
            lines.append(f"  • {name} — {count} time(s), first at {first_str}")
        if len(summary) > 10:
            lines.append(f"  … and {len(summary) - 10} more")

    message = "\n".join(lines)
    success = send_message(message)
    if success:
        print(f"[Telegram] Daily summary sent for {today}")
    else:
        print(f"[Telegram] Failed to send daily summary for {today}")


# ─── Scheduler thread ─────────────────────────────────────────────────────────

class DailySummaryScheduler:
    """
    Background thread that fires send_daily_summary() once per day at the
    configured time (SCHEDULER_SEND_TIME in HH:MM format).
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_sent_date: Optional[date] = None

    def start(self):
        if not SCHEDULER_ENABLED:
            print("[Telegram Scheduler] Disabled in config.")
            return
        if SCHEDULER_SERVICE.lower() != "telegram":
            print(f"[Telegram Scheduler] Service is '{SCHEDULER_SERVICE}', not 'telegram'. Skipping.")
            return
        if not _is_configured():
            print("[Telegram Scheduler] Bot token or chat ID not configured. Skipping.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="TelegramScheduler")
        self._thread.start()
        print(f"[Telegram Scheduler] Started. Will send daily summary at {SCHEDULER_SEND_TIME} ({TIMEZONE}).")

    def stop(self):
        self._stop_event.set()

    def _run(self):
        try:
            hour, minute = [int(x) for x in SCHEDULER_SEND_TIME.split(":")]
        except ValueError:
            print(f"[Telegram Scheduler] Invalid send_time '{SCHEDULER_SEND_TIME}'. Use HH:MM format.")
            return

        tz = pytz.timezone(TIMEZONE)

        while not self._stop_event.is_set():
            now = datetime.now(tz)
            today = now.date()

            if (
                now.hour == hour
                and now.minute == minute
                and self._last_sent_date != today
            ):
                self._last_sent_date = today
                try:
                    send_daily_summary()
                except Exception as e:
                    print(f"[Telegram Scheduler] Error sending daily summary: {e}")

            # Sleep 30 seconds between checks (accurate to within 30s of target time)
            self._stop_event.wait(30)


# Module-level singleton
_scheduler = DailySummaryScheduler()


def start_scheduler():
    """Start the daily summary scheduler. Call once at application startup."""
    _scheduler.start()


def stop_scheduler():
    """Stop the daily summary scheduler."""
    _scheduler.stop()
