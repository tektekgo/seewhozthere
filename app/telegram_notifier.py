"""
SeeWhozThere® Telegram Notifier

Sends two types of messages:
  1. Instant alert  — fired immediately when an unknown face is detected.
                      Includes inline buttons to identify the person directly
                      from Telegram without opening the web dashboard.
  2. Daily summary  — a digest of the day's activity, sent at a configured time.

Inline Button Behaviour
-----------------------
When an unknown face is detected the alert message carries an InlineKeyboardMarkup
with one button per known person (up to MAX_IDENTIFY_BUTTONS), plus:
  • "Keep Unknown"     — dismisses the buttons and leaves the sighting as-is.
  • "Add as New Person" — prompts the user to reply with a name; the bot then
                          creates a new visitor record and links the sighting.

Callback data format
--------------------
  id_<sighting_id>_<visitor_id>   → assign sighting to existing visitor
  keep_<sighting_id>              → keep sighting as Unknown, remove buttons
  new_<sighting_id>               → enter "add new person" flow

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
    TELEGRAM_ALERT_COOLDOWN_MINUTES,
    TELEGRAM_KNOWN_VISITOR_COOLDOWN_MINUTES,
)

# Maximum number of "It's <Name>" buttons to show per alert.

# ─── Alert cooldown tracker ───────────────────────────────────────────────────
# Prevents alert flooding: tracks the last time a Telegram alert was sent
# per camera (for unknown faces) and per visitor name (for known faces).
# Key: camera_name or visitor_name  →  Value: unix timestamp of last alert
_last_unknown_alert: dict = {}   # camera_name -> float (epoch seconds)
_last_known_alert: dict = {}     # visitor_name -> float (epoch seconds)
_alert_lock = threading.Lock()


def _should_send_unknown_alert(camera_name: str) -> bool:
    """Return True if enough time has passed since the last unknown-face alert
    for this camera. Thread-safe."""
    cooldown_secs = TELEGRAM_ALERT_COOLDOWN_MINUTES * 60
    if cooldown_secs <= 0:
        return True
    with _alert_lock:
        last = _last_unknown_alert.get(camera_name, 0)
        if time.time() - last >= cooldown_secs:
            _last_unknown_alert[camera_name] = time.time()
            return True
        return False


def _should_send_known_alert(visitor_name: str) -> bool:
    """Return True if enough time has passed since the last known-visitor alert
    for this visitor. Thread-safe."""
    cooldown_secs = TELEGRAM_KNOWN_VISITOR_COOLDOWN_MINUTES * 60
    if cooldown_secs <= 0:
        return True
    with _alert_lock:
        last = _last_known_alert.get(visitor_name, 0)
        if time.time() - last >= cooldown_secs:
            _last_known_alert[visitor_name] = time.time()
            return True
        return False


# Maximum number of "It's <Name>" buttons to show per alert.
# Buttons are ordered by most-recently-seen so the most frequent visitors
# appear first.  Any additional known people are omitted to keep the UI clean.
MAX_IDENTIFY_BUTTONS = 6


# ─── Low-level Telegram helpers ──────────────────────────────────────────────

def _api_url(method: str) -> str:
    return f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"


def _is_configured() -> bool:
    """Return True if both bot_token and chat_id are set."""
    return bool(TELEGRAM_BOT_TOKEN.strip()) and bool(TELEGRAM_CHAT_ID.strip())


def send_message(text: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
    """
    Send a plain-text message.

    Args:
        text:         HTML-formatted message text.
        reply_markup: Optional InlineKeyboardMarkup dict.

    Returns:
        The Telegram Message object (dict) on success, or None on failure.
    """
    if not _is_configured():
        return None
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        resp = requests.post(_api_url("sendMessage"), json=payload, timeout=10)
        if resp.ok:
            return resp.json().get("result")
        print(f"[Telegram] sendMessage failed: {resp.text}")
        return None
    except Exception as e:
        print(f"[Telegram] sendMessage error: {e}")
        return None


def send_photo(
    image_path: str,
    caption: str = "",
    reply_markup: Optional[dict] = None,
) -> Optional[dict]:
    """
    Send a photo with an optional caption and optional inline keyboard.

    Returns:
        The Telegram Message object (dict) on success, or None on failure.
    """
    if not _is_configured():
        return None
    if not image_path or not os.path.exists(image_path):
        return send_message(caption, reply_markup=reply_markup)
    try:
        data: dict = {
            "chat_id": TELEGRAM_CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML",
        }
        if reply_markup:
            import json as _json
            data["reply_markup"] = _json.dumps(reply_markup)
        with open(image_path, "rb") as f:
            resp = requests.post(
                _api_url("sendPhoto"),
                data=data,
                files={"photo": f},
                timeout=15,
            )
        if resp.ok:
            return resp.json().get("result")
        print(f"[Telegram] sendPhoto failed: {resp.text}")
        return None
    except Exception as e:
        print(f"[Telegram] sendPhoto error: {e}")
        return None


def edit_message_reply_markup(chat_id: str, message_id: int, reply_markup: Optional[dict]) -> bool:
    """Replace (or remove) the inline keyboard on an existing message."""
    if not _is_configured():
        return False
    payload: dict = {"chat_id": chat_id, "message_id": message_id}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    else:
        payload["reply_markup"] = {}   # empty dict removes the keyboard
    try:
        resp = requests.post(_api_url("editMessageReplyMarkup"), json=payload, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"[Telegram] editMessageReplyMarkup error: {e}")
        return False


def edit_message_caption(chat_id: str, message_id: int, caption: str) -> bool:
    """Edit the caption of an existing photo message."""
    if not _is_configured():
        return False
    try:
        resp = requests.post(
            _api_url("editMessageCaption"),
            json={
                "chat_id": chat_id,
                "message_id": message_id,
                "caption": caption,
                "parse_mode": "HTML",
                "reply_markup": {},   # remove inline keyboard
            },
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        print(f"[Telegram] editMessageCaption error: {e}")
        return False


def answer_callback_query(callback_query_id: str, text: str = "", alert: bool = False) -> bool:
    """Acknowledge a callback query (removes the loading spinner in Telegram)."""
    if not _is_configured():
        return False
    try:
        resp = requests.post(
            _api_url("answerCallbackQuery"),
            json={"callback_query_id": callback_query_id, "text": text, "show_alert": alert},
            timeout=10,
        )
        return resp.ok
    except Exception as e:
        print(f"[Telegram] answerCallbackQuery error: {e}")
        return False


# ─── Inline keyboard builder ─────────────────────────────────────────────────

def _build_identify_keyboard(sighting_id: int) -> dict:
    """
    Build an InlineKeyboardMarkup for an unknown-face alert.

    The keyboard shows up to MAX_IDENTIFY_BUTTONS known-person buttons
    (ordered by most-recently-seen), then "Keep Unknown" and "Add as New Person".
    """
    from app.database import get_db

    db = get_db()
    visitors = db.get_all_visitors()

    # Fetch last-seen timestamps so we can sort by recency
    recency: dict = {}
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT visitor_id, MAX(timestamp) AS last_seen
            FROM sightings
            WHERE visitor_id IS NOT NULL
            GROUP BY visitor_id
            """
        )
        for row in cursor.fetchall():
            recency[row["visitor_id"]] = row["last_seen"] or ""
        conn.close()
    except Exception:
        pass

    # Sort visitors: those seen most recently first
    visitors_sorted = sorted(
        visitors,
        key=lambda v: recency.get(v["id"], ""),
        reverse=True,
    )

    buttons: list = []

    # One button per known person (capped at MAX_IDENTIFY_BUTTONS)
    for visitor in visitors_sorted[:MAX_IDENTIFY_BUTTONS]:
        buttons.append([
            {
                "text": f"It's {visitor['name']}",
                "callback_data": f"id_{sighting_id}_{visitor['id']}",
            }
        ])

    # Control buttons on the last row
    buttons.append([
        {
            "text": "\U0001f6ab Keep Unknown",
            "callback_data": f"keep_{sighting_id}",
        },
        {
            "text": "\u2795 Add as New Person",
            "callback_data": f"new_{sighting_id}",
        },
    ])

    # False positive row — lets user delete non-face detections with one tap
    buttons.append([
        {
            "text": "\U0001f5d1\ufe0f False Positive \u2014 Delete",
            "callback_data": f"wrongdel_{sighting_id}",
        },
    ])
    return {"inline_keyboard": buttons}


# ─── Instant alerts ──────────────────────────────────────────────────────────

def send_unknown_face_alert(
    camera_name: str,
    snapshot_path: Optional[str] = None,
    sighting_id: Optional[int] = None,
):
    """
    Fire an instant alert when an unknown face is detected.

    If sighting_id is provided the message will include an inline keyboard so
    the user can identify the person directly from Telegram.

    Args:
        camera_name:   Name of the camera that triggered the detection.
        snapshot_path: Absolute or relative path to the face snapshot image.
        sighting_id:   Database ID of the sighting record (enables inline buttons).
    """
    if not _is_configured():
        return
    # Cooldown check — suppress if we already alerted for this camera recently
    if not _should_send_unknown_alert(camera_name):
        remaining = int(TELEGRAM_ALERT_COOLDOWN_MINUTES * 60 - (time.time() - _last_unknown_alert.get(camera_name, 0)))
        print(f"[Telegram] Unknown-face alert suppressed for {camera_name} (cooldown: {remaining}s remaining)")
        return
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%I:%M:%S %p %Z")
    caption = (
        f"<b>\U0001f6a8 Unknown visitor detected</b>\n"
        f"Camera: {camera_name}\n"
        f"Time: {now}\n"
        f"\u2014 SeeWhozThere\u00ae"
    )
    reply_markup = None
    if sighting_id is not None:
        try:
            reply_markup = _build_identify_keyboard(sighting_id)
        except Exception as e:
            print(f"[Telegram] Could not build keyboard: {e}")
    if snapshot_path and os.path.exists(snapshot_path):
        msg = send_photo(snapshot_path, caption, reply_markup=reply_markup)
    else:
        msg = send_message(caption, reply_markup=reply_markup)
    if msg and sighting_id is not None:
        # Register the message so the callback handler can edit it later
        _callback_handler.register_message(sighting_id, msg)
    print(f"[Telegram] Sent unknown-face alert for {camera_name}"
          + (f" (sighting #{sighting_id})" if sighting_id else ""))


def send_known_face_alert(
    visitor_name: str,
    camera_name: str,
    snapshot_path: Optional[str] = None,
    sighting_id: Optional[int] = None,
):
    """
    Fire an instant alert when a known visitor is recognised.

    Args:
        visitor_name:  Name of the recognised visitor.
        camera_name:   Name of the camera.
        snapshot_path: Path to the face snapshot image.
    """
    if not _is_configured():
        return
    # Cooldown check — suppress repeated alerts for the same known visitor
    if not _should_send_known_alert(visitor_name):
        remaining = int(TELEGRAM_KNOWN_VISITOR_COOLDOWN_MINUTES * 60 - (time.time() - _last_known_alert.get(visitor_name, 0)))
        print(f"[Telegram] Known-face alert suppressed for {visitor_name} (cooldown: {remaining}s remaining)")
        return
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).strftime("%I:%M:%S %p %Z")
    caption = (
        f"<b>{visitor_name} spotted</b>\n"
        f"Camera: {camera_name}\n"
        f"Time: {now}\n"
        f"\u2014 SeeWhozThere\u00ae"
    )
    # Build correction keyboard if we have a sighting_id
    reply_markup = None
    if sighting_id is not None:
        try:
            reply_markup = _build_correction_keyboard(sighting_id)
        except Exception as e:
            print(f"[Telegram] Could not build correction keyboard: {e}")
    if snapshot_path and os.path.exists(snapshot_path):
        msg = send_photo(snapshot_path, caption, reply_markup=reply_markup)
    else:
        msg = send_message(caption, reply_markup=reply_markup)
    # Register message so callback handler can edit it when user taps a button
    if msg and sighting_id is not None:
        _callback_handler.register_message(sighting_id, msg)
    print(f"[Telegram] Sent known-face alert for {visitor_name} on {camera_name}"
          + (f" (sighting #{sighting_id})" if sighting_id else ""))


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

    summary = db.get_today_summary()
    stats = db.get_statistics()

    total_sightings = sum(v.get("sighting_count", 0) for v in summary)
    known_count = sum(1 for v in summary if v.get("visitor_id") and v["visitor_id"] != 0)
    unknown_count = len(summary) - known_count

    lines = [
        f"<b>SeeWhozThere\u00ae Daily Summary</b>",
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
        for v in summary[:10]:
            name = v.get("name", "Unknown")
            count = v.get("sighting_count", 0)
            first = v.get("first_seen")
            first_str = first.strftime("%H:%M") if first and hasattr(first, "strftime") else str(first or "")
            lines.append(f"  \u2022 {name} \u2014 {count} time(s), first at {first_str}")
        if len(summary) > 10:
            lines.append(f"  \u2026 and {len(summary) - 10} more")

    message = "\n".join(lines)
    result = send_message(message)
    if result:
        print(f"[Telegram] Daily summary sent for {today}")
    else:
        print(f"[Telegram] Failed to send daily summary for {today}")


# ─── Callback / polling handler ───────────────────────────────────────────────

class TelegramCallbackHandler:
    """
    Lightweight long-polling loop that listens for InlineKeyboard callback
    queries and handles identification actions without requiring a public
    webhook URL.

    The handler runs as a daemon thread so it does not block the main process.
    It uses getUpdates with a 30-second timeout (long-polling) to minimise
    CPU usage while remaining responsive.

    Pending-message registry
    ------------------------
    When an unknown-face alert is sent, the Telegram message_id is stored in
    _pending keyed by sighting_id.  When the user taps a button the handler
    looks up the message_id so it can edit the caption / remove the keyboard.
    """

    POLL_TIMEOUT = 30          # seconds for long-poll
    RETRY_DELAY  = 5           # seconds to wait after a network error
    # How long (seconds) to remember a pending message before discarding it
    PENDING_TTL  = 3600 * 6   # 6 hours

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._offset: int = 0
        # sighting_id -> {"chat_id": str, "message_id": int, "ts": float}
        self._pending: dict = {}
        self._pending_lock = threading.Lock()
        # sighting_id -> waiting for a text reply to use as new person name
        self._awaiting_name: dict = {}   # sighting_id -> callback_query_id
        self._awaiting_lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def register_message(self, sighting_id: int, telegram_message: dict):
        """
        Store the Telegram message metadata for a sighting so the callback
        handler can edit it later.

        Args:
            sighting_id:      Database sighting ID.
            telegram_message: The 'result' dict returned by sendPhoto/sendMessage.
        """
        chat_id = str(telegram_message.get("chat", {}).get("id", TELEGRAM_CHAT_ID))
        message_id = telegram_message.get("message_id")
        if message_id:
            with self._pending_lock:
                self._pending[sighting_id] = {
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "ts": time.time(),
                }

    def start(self):
        if not _is_configured():
            print("[Telegram Callback] Bot not configured — callback polling disabled.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="TelegramCallbackPoller",
        )
        self._thread.start()
        print("[Telegram Callback] Polling loop started.")

    def stop(self):
        self._stop_event.set()

    # ── Internal polling loop ─────────────────────────────────────────────────

    def _run(self):
        print("[Telegram Callback] Entering long-poll loop.")
        while not self._stop_event.is_set():
            try:
                updates = self._get_updates()
                for update in updates:
                    self._offset = update["update_id"] + 1
                    self._dispatch(update)
            except Exception as e:
                print(f"[Telegram Callback] Poll error: {e}")
                self._stop_event.wait(self.RETRY_DELAY)

    def _get_updates(self) -> list:
        """Fetch pending updates via long-polling."""
        try:
            resp = requests.post(
                _api_url("getUpdates"),
                json={
                    "offset": self._offset,
                    "timeout": self.POLL_TIMEOUT,
                    "allowed_updates": ["callback_query", "message"],
                },
                timeout=self.POLL_TIMEOUT + 10,
            )
            if resp.ok:
                return resp.json().get("result", [])
            print(f"[Telegram Callback] getUpdates failed: {resp.text}")
            return []
        except requests.exceptions.Timeout:
            return []   # normal long-poll timeout — just loop again
        except Exception as e:
            print(f"[Telegram Callback] getUpdates error: {e}")
            time.sleep(self.RETRY_DELAY)
            return []

    def _dispatch(self, update: dict):
        """Route an incoming update to the appropriate handler."""
        if "callback_query" in update:
            self._handle_callback_query(update["callback_query"])
        elif "message" in update:
            self._handle_message(update["message"])

    # ── Callback query handler ────────────────────────────────────────────────

    def _handle_callback_query(self, cq: dict):
        """Process an InlineKeyboard button tap."""
        cq_id   = cq["id"]
        data    = cq.get("data", "")
        chat_id = str(cq["message"]["chat"]["id"])
        msg_id  = cq["message"]["message_id"]

        print(f"[Telegram Callback] Received callback: {data!r}")

        # ── id_<sighting_id>_<visitor_id> ─────────────────────────────────────
        if data.startswith("id_"):
            parts = data.split("_")
            if len(parts) == 3:
                sighting_id = int(parts[1])
                visitor_id  = int(parts[2])
                self._identify_sighting(cq_id, sighting_id, visitor_id, chat_id, msg_id)
            else:
                answer_callback_query(cq_id, "Invalid callback data.", alert=True)

        # ── keep_<sighting_id> ────────────────────────────────────────────────
        elif data.startswith("keep_"):
            sighting_id = int(data.split("_", 1)[1])
            self._keep_unknown(cq_id, sighting_id, chat_id, msg_id)

        # ── new_<sighting_id> ─────────────────────────────────────────────────
        elif data.startswith("new_"):
            sighting_id = int(data.split("_", 1)[1])
            self._start_add_new_person(cq_id, sighting_id, chat_id, msg_id)

        # ── correct_<sighting_id> ───────────────────────────────────────────────
        elif data.startswith("correct_"):
            sighting_id = int(data.split("_", 1)[1])
            self._correct_sighting(cq_id, sighting_id, chat_id, msg_id)

        # ── wrongdel_<sighting_id> ─────────────────────────────────────────────
        elif data.startswith("wrongdel_"):
            sighting_id = int(data.split("_", 1)[1])
            self._wrongdel_sighting(cq_id, sighting_id, chat_id, msg_id)

        # ── wrong_<sighting_id> ────────────────────────────────────────────────
        elif data.startswith("wrong_"):
            sighting_id = int(data.split("_", 1)[1])
            self._wrong_sighting(cq_id, sighting_id, chat_id, msg_id)

        else:
            answer_callback_query(cq_id, "Unknown action.", alert=True)

    # ── Message handler (used for "Add as New Person" name reply) ─────────────

    def _handle_message(self, msg: dict):
        """Handle a plain text reply, used for the 'Add as New Person' flow."""
        chat_id = str(msg.get("chat", {}).get("id", ""))
        text    = (msg.get("text") or "").strip()

        if not text or not chat_id:
            return

        # Check if any sighting is awaiting a name reply from this chat
        with self._awaiting_lock:
            match_id = None
            for sid, info in list(self._awaiting_name.items()):
                if info.get("chat_id") == chat_id:
                    match_id = sid
                    break

        if match_id is None:
            return   # Not a reply we're waiting for

        with self._awaiting_lock:
            info = self._awaiting_name.pop(match_id, None)

        if info is None:
            return

        self._finish_add_new_person(match_id, text, chat_id, info.get("message_id"))

    # ── Action implementations ────────────────────────────────────────────────

    def _identify_sighting(
        self,
        cq_id: str,
        sighting_id: int,
        visitor_id: int,
        chat_id: str,
        msg_id: int,
    ):
        """Assign a known visitor to an unknown sighting."""
        try:
            from app.database import get_db
            import numpy as np

            db = get_db()
            visitor = db.get_visitor(visitor_id)
            if not visitor:
                answer_callback_query(cq_id, "Visitor not found.", alert=True)
                return

            # Fetch snapshot path for encoding extraction
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT snapshot_path FROM sightings WHERE id = ?", (sighting_id,))
            row = cursor.fetchone()
            conn.close()
            snapshot_path = dict(row)["snapshot_path"] if row else None

            # Update sighting
            success = db.identify_sighting(sighting_id, visitor_id)
            if not success:
                answer_callback_query(cq_id, "Sighting not found.", alert=True)
                return

            # Attempt to save face encoding if visitor has none
            if not visitor.get("face_encoding") and snapshot_path:
                try:
                    import cv2 as _cv2
                    from app.face_recognition_engine import get_face_recognition_engine as _get_fre
                    img = _cv2.imread(snapshot_path)
                    if img is not None:
                        fre = _get_fre()
                        encoding = fre.encode_face(img)
                        encoding_bytes = encoding.astype(np.float32).tobytes()
                        thumb = visitor.get("thumbnail_path") or snapshot_path
                        db.update_visitor(visitor_id, face_encoding=encoding_bytes, thumbnail_path=thumb)
                        try:
                            from app.hailo_processor_v2 import get_processor
                            get_processor().reload_known_faces()
                        except Exception:
                            pass
                        print(f"[Telegram Callback] Saved encoding for {visitor['name']}")
                except Exception as enc_err:
                    print(f"[Telegram Callback] Encoding extraction failed: {enc_err}")

            visitor_name = visitor["name"]
            answer_callback_query(cq_id, f"Identified as {visitor_name} ✓")

            # Edit the Telegram message to confirm identification
            tz = pytz.timezone(TIMEZONE)
            now = datetime.now(tz).strftime("%H:%M:%S")
            new_caption = (
                f"<b>\u2705 Identified: {visitor_name}</b>\n"
                f"Updated at: {now}\n"
                f"\u2014 SeeWhozThere\u00ae"
            )
            edit_message_caption(chat_id, msg_id, new_caption)

            # Clean up pending registry
            with self._pending_lock:
                self._pending.pop(sighting_id, None)

            print(f"[Telegram Callback] Sighting #{sighting_id} identified as {visitor_name}")

        except Exception as e:
            print(f"[Telegram Callback] _identify_sighting error: {e}")
            answer_callback_query(cq_id, "Error updating identification.", alert=True)

    def _correct_sighting(self, cq_id: str, sighting_id: int, chat_id: str, msg_id: int):
        """Confirm the known-face identification is correct and dismiss buttons."""
        try:
            answer_callback_query(cq_id, "Confirmed \u2705")
            tz = pytz.timezone(TIMEZONE)
            now = datetime.now(tz).strftime("%I:%M:%S %p %Z")
            new_caption = (
                f"<b>\u2705 Identification confirmed</b>\n"
                f"Updated at: {now}\n"
                f"\u2014 SeeWhozThere\u00ae"
            )
            edit_message_caption(chat_id, msg_id, new_caption)
            edit_message_reply_markup(chat_id, msg_id, None)
            with self._pending_lock:
                self._pending.pop(sighting_id, None)
            print(f"[Telegram Callback] Sighting #{sighting_id} confirmed correct.")
        except Exception as e:
            print(f"[Telegram Callback] _correct_sighting error: {e}")
            answer_callback_query(cq_id, "Error.", alert=True)

    def _wrong_sighting(self, cq_id: str, sighting_id: int, chat_id: str, msg_id: int):
        """Unlink visitor from sighting (mark as Unknown) and dismiss buttons."""
        try:
            from app.database import get_db
            db = get_db()
            db.unlink_sighting(sighting_id)
            answer_callback_query(cq_id, "Marked as Unknown \u274c")
            tz = pytz.timezone(TIMEZONE)
            now = datetime.now(tz).strftime("%I:%M:%S %p %Z")
            new_caption = (
                f"<b>\u274c Wrong ID \u2014 Marked as Unknown</b>\n"
                f"Updated at: {now}\n"
                f"\u2014 SeeWhozThere\u00ae"
            )
            edit_message_caption(chat_id, msg_id, new_caption)
            edit_message_reply_markup(chat_id, msg_id, None)
            with self._pending_lock:
                self._pending.pop(sighting_id, None)
            print(f"[Telegram Callback] Sighting #{sighting_id} unlinked (marked Unknown).")
        except Exception as e:
            print(f"[Telegram Callback] _wrong_sighting error: {e}")
            answer_callback_query(cq_id, "Error.", alert=True)

    def _wrongdel_sighting(self, cq_id: str, sighting_id: int, chat_id: str, msg_id: int):
        """Delete the sighting entirely and dismiss buttons."""
        try:
            from app.database import get_db
            db = get_db()
            db.delete_sighting(sighting_id)
            answer_callback_query(cq_id, "Sighting deleted \U0001f5d1")
            tz = pytz.timezone(TIMEZONE)
            now = datetime.now(tz).strftime("%I:%M:%S %p %Z")
            new_caption = (
                f"<b>\U0001f5d1 False positive \u2014 Sighting deleted</b>\n"
                f"Removed at: {now}\n"
                f"\u2014 SeeWhozThere\u00ae"
            )
            edit_message_caption(chat_id, msg_id, new_caption)
            edit_message_reply_markup(chat_id, msg_id, None)
            with self._pending_lock:
                self._pending.pop(sighting_id, None)
            print(f"[Telegram Callback] Sighting #{sighting_id} deleted.")
        except Exception as e:
            print(f"[Telegram Callback] _wrongdel_sighting error: {e}")
            answer_callback_query(cq_id, "Error.", alert=True)

    def _keep_unknown(self, cq_id: str, sighting_id: int, chat_id: str, msg_id: int):
        """Dismiss the buttons and keep the sighting as Unknown."""
        answer_callback_query(cq_id, "Kept as Unknown.")
        edit_message_reply_markup(chat_id, msg_id, None)
        with self._pending_lock:
            self._pending.pop(sighting_id, None)
        print(f"[Telegram Callback] Sighting #{sighting_id} kept as Unknown.")

    def _start_add_new_person(self, cq_id: str, sighting_id: int, chat_id: str, msg_id: int):
        """Begin the 'Add as New Person' flow by asking for a name."""
        answer_callback_query(cq_id, "Reply with the person's name.")
        # Remove the keyboard so the user knows we're waiting
        edit_message_reply_markup(chat_id, msg_id, None)
        # Send a follow-up prompt
        send_message(
            f"Please reply with the <b>name</b> for this new person.\n"
            f"(Sighting #{sighting_id})"
        )
        with self._awaiting_lock:
            self._awaiting_name[sighting_id] = {
                "chat_id": chat_id,
                "message_id": msg_id,
                "ts": time.time(),
            }
        print(f"[Telegram Callback] Waiting for name for sighting #{sighting_id}")

    def _finish_add_new_person(self, sighting_id: int, name: str, chat_id: str, msg_id: Optional[int]):
        """Create a new visitor record and link the sighting to it."""
        try:
            from app.database import get_db
            import numpy as np

            db = get_db()

            # Fetch snapshot path
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT snapshot_path FROM sightings WHERE id = ?", (sighting_id,))
            row = cursor.fetchone()
            conn.close()
            snapshot_path = dict(row)["snapshot_path"] if row else None

            # Create visitor (handle duplicate names gracefully)
            try:
                visitor_id = db.add_visitor(name, thumbnail_path=snapshot_path)
            except Exception:
                # Name already exists — fetch existing
                existing = db.get_visitor_by_name(name)
                if existing:
                    visitor_id = existing["id"]
                else:
                    send_message(f"\u274c Could not create visitor '{name}'. Please try again.")
                    return

            # Link sighting
            db.identify_sighting(sighting_id, visitor_id)

            # Attempt to extract and save face encoding
            if snapshot_path:
                try:
                    import cv2 as _cv2
                    from app.face_recognition_engine import get_face_recognition_engine as _get_fre
                    img = _cv2.imread(snapshot_path)
                    if img is not None:
                        fre = _get_fre()
                        encoding = fre.encode_face(img)
                        encoding_bytes = encoding.astype(np.float32).tobytes()
                        db.update_visitor(visitor_id, face_encoding=encoding_bytes)
                        try:
                            from app.hailo_processor_v2 import get_processor
                            get_processor().reload_known_faces()
                        except Exception:
                            pass
                except Exception as enc_err:
                    print(f"[Telegram Callback] Encoding extraction failed: {enc_err}")

            send_message(
                f"\u2705 <b>{name}</b> has been added and the sighting has been linked.\n"
                f"SeeWhozThere\u00ae will now recognise them automatically."
            )
            print(f"[Telegram Callback] Added new person '{name}' for sighting #{sighting_id}")

        except Exception as e:
            print(f"[Telegram Callback] _finish_add_new_person error: {e}")
            send_message(f"\u274c Error adding new person: {e}")

    # ── Housekeeping ──────────────────────────────────────────────────────────

    def _expire_pending(self):
        """Remove stale entries from the pending registry."""
        now = time.time()
        with self._pending_lock:
            stale = [k for k, v in self._pending.items() if now - v["ts"] > self.PENDING_TTL]
            for k in stale:
                del self._pending[k]
        with self._awaiting_lock:
            stale = [k for k, v in self._awaiting_name.items() if now - v["ts"] > self.PENDING_TTL]
            for k in stale:
                del self._awaiting_name[k]


# Module-level singleton — shared across the whole process
_callback_handler = TelegramCallbackHandler()


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

            self._stop_event.wait(30)


# Module-level singleton
_scheduler = DailySummaryScheduler()


def start_scheduler():
    """Start the daily summary scheduler AND the callback polling loop."""
    _scheduler.start()
    _callback_handler.start()


def stop_scheduler():
    """Stop the daily summary scheduler and the callback polling loop."""
    _scheduler.stop()
    _callback_handler.stop()
