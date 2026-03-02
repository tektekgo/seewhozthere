# SeeWhozThere — Development Progress Log

This document tracks what has been built, what is in progress, and what is next. It exists to ensure continuity across sessions regardless of interruptions.

---

## Current Status (as of 2026-03-01)

### Completed Features

| Feature | File(s) | Notes |
|---|---|---|
| Face detection (Hailo AI HAT+) | `app/hailo_processor_v2.py` | Fully working on Pi |
| Web dashboard (React + FastAPI) | `app/main.py`, `frontend/` | Accessible at port 7222 |
| Login / session auth | `app/main.py` | Passphrase-based, HMAC-signed cookie |
| Snapshot cooldown | `app/hailo_processor_v2.py`, `config.ini` | `[DETECTION] snapshot_cooldown_seconds = 15` |
| Telegram instant alerts | `app/telegram_notifier.py` | Sends photo + camera + time on detection |
| Telegram daily summary | `app/telegram_notifier.py` | Scheduler thread in web server, configurable time |
| Setup guide | `SETUP.md` | Complete from-scratch instructions for new users |
| Docs reorganization | `docs/` | All dev docs moved out of root |
| Future enhancements doc | `docs/future-enhancements.md` | Docker plan with draft Dockerfile |

### In Progress: Known Visitor Face Labelling

**Goal:** When you click "Name" on an unknown face in the History page and type a name, the system should:
1. Link that sighting to the visitor in the database (already works)
2. Extract the face encoding from that snapshot image (MISSING — this is the gap)
3. Save the encoding to the `visitors.face_encoding` column (MISSING)
4. Reload the known faces in the detection service so future appearances match (MISSING)

**Why this matters:** Without step 2–4, labelling a face in the UI has no effect on future detections. The person will still appear as "Unknown" next time.

---

## Architecture Overview

### Backend (Python / FastAPI)

```
app/
  main.py                  — FastAPI web server, all API endpoints
  config.py                — Reads config.ini, exports settings
  database.py              — SQLite wrapper (visitors + sightings tables)
  hailo_processor_v2.py    — Detection loop, one thread per camera
  hailo_face_detector_v4.py — Hailo NPU inference wrapper
  face_recognition_engine.py — Face encoding generation + matching
  telegram_notifier.py     — Telegram alerts + daily summary scheduler
  analytics.py             — Aggregation queries for charts
```

### Frontend (React + Vite + TailwindCSS)

```
frontend/src/
  pages/
    History.tsx            — Detection history, labelling UI (FULLY BUILT)
    Index.tsx              — Main dashboard
    Login.tsx              — Login page
  lib/
    api.ts                 — All API calls to FastAPI backend
```

### Database Schema

```sql
visitors (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE,
  face_encoding BLOB,      -- numpy float32 array serialized as bytes
  thumbnail_path TEXT,
  created_at, updated_at
)

sightings (
  id INTEGER PRIMARY KEY,
  visitor_id INTEGER,      -- NULL = unknown face
  camera_name TEXT,
  timestamp TIMESTAMP,
  confidence REAL,
  snapshot_path TEXT       -- path to saved JPEG, e.g. data/snapshots/front_door_20260301_...jpg
)
```

### Face Recognition Flow

1. Detection loop calls `face_recognition_engine.encode_face(face_image)` → numpy float32 array
2. Array compared against all known encodings in `hailo_processor_v2.known_encodings` dict
3. If match found (cosine similarity > threshold), visitor_id is set on the sighting
4. Known encodings are loaded at startup via `_load_known_faces()` and can be reloaded via `reload_known_faces()`

---

## What Needs to Be Done Next (Face Labelling)

### Backend Change: Enhance `/api/sightings/{id}/identify`

**Current behaviour:** Updates `sightings.visitor_id = visitor_id`. That's it.

**Required behaviour:**
1. Load the snapshot image from `sighting.snapshot_path`
2. Run `face_recognition_engine.encode_face(image)` on it
3. If encoding succeeds:
   - If visitor has no encoding yet → save it as the primary encoding
   - If visitor already has an encoding → optionally average/append (keep it simple: only save if no encoding exists yet)
4. Update `visitors.face_encoding` in the database
5. Call `processor.reload_known_faces()` so the running detection loop picks up the new encoding immediately (no restart needed)

### New API endpoint: `POST /api/sightings/{id}/label`

Cleaner than modifying the existing `identify` endpoint. Accepts:
- `visitor_id` (int, existing visitor) OR `visitor_name` (str, create new visitor)
- Extracts encoding from snapshot
- Returns `{ success, visitor_id, visitor_name, encoding_saved }`

### Frontend Change: Update `api.identifySighting` → `api.labelSighting`

The `NameDialog` in `History.tsx` already calls `api.identifySighting`. We need to either:
- Replace it with a call to the new `label` endpoint, OR
- Keep `identifySighting` but have it call the new endpoint

The simpler path: update `api.identifySighting` to call `/api/sightings/{id}/label` instead of `/api/sightings/{id}/identify`, passing `visitor_id`.

---

## Key File Locations on the Pi

```
/home/pimediaadmin/projects/seewhozthere/
  config.ini                          — Live config (not in git)
  data/seewhozthere.db                — SQLite database
  data/snapshots/                     — Face snapshot JPEGs
  data/service.log                    — Detection service log
  data/web.log                        — Web server log
  app/static/dashboard/               — Built React frontend (served by FastAPI)
```

## Service Management

```bash
# Check status
sudo systemctl status seewhozthere seewhozthere-web

# Restart after code changes
git pull origin main
sudo systemctl restart seewhozthere seewhozthere-web

# View live logs
tail -f ~/projects/seewhozthere/data/service.log
tail -f ~/projects/seewhozthere/data/web.log
```

---

## Telegram Configuration

```ini
[TELEGRAM]
bot_token = <your_bot_token>
chat_id   = <your_chat_id>

[SCHEDULER]
enabled    = true
send_time  = 20:00
service    = telegram
```

Bot is already set up and working. Token and chat_id are in `config.ini` on the Pi.

---

## Pending / Future Work

- [ ] **Face labelling encoding extraction** (in progress — see above)
- [ ] **Docker containerization** — see `docs/future-enhancements.md`
- [ ] **Tailscale remote access** — access dashboard from outside home network
- [ ] **Multi-person recognition tuning** — test accuracy with multiple known people


## Appendix: Camera Capacity

**Recommendation for Pi 5 + Hailo HAT+:** 4 cameras is the sweet spot.

| Camera Count | Expected Performance |
|---|---|
| 1–2 cameras | Excellent — full detection rate, no frame drops |
| 3–4 cameras | Good — slight increase in inference queue wait time, still reliable |
| 5–6 cameras | Acceptable — recommend increasing `detection_interval` to 2–3s to reduce CPU load |
| 7+ cameras | Not recommended without tuning — RTSP decode threads compete for CPU, frame drops likely |
