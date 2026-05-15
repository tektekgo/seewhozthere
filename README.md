# SeeWhozThere®

SeeWhozThere® is an advanced, privacy-first home security and face recognition system designed specifically for the Raspberry Pi 5 with the Hailo-8L AI Accelerator. It processes local RTSP camera streams in real-time, identifies known and unknown visitors, and provides a beautiful web dashboard and interactive Telegram notifications — all without sending a single frame to the cloud.

<p align="center">
  <img src="frontend/public/logo.png" width="120" alt="SeeWhozThere Logo">
</p>

---

## 🌟 Features

### AI & Detection
- **Real-time Face Detection** powered by the Hailo-8L NPU using the RetinaFace MobileNet model (25–30 FPS per camera stream).
- **Deep Learning Face Recognition** powered by InsightFace (ArcFace `buffalo_sc` model) for highly accurate outdoor identification across varying angles and lighting conditions.
- **Configurable Detection Tuning** — set minimum face size and confidence threshold per environment (indoor vs. outdoor) to eliminate false positives from foliage, shadows, or passing vehicles.
- **Snapshot Cooldown** — configurable minimum seconds between saved snapshots per camera to prevent photo floods.
- **Camera Watchdog** — automatically restarts any camera thread that dies due to a network drop, without requiring a service restart.
- **Face Encoding Learning** — when you identify an unknown face (from the dashboard or Telegram), SeeWhozThere® extracts and saves the face encoding from the snapshot so the system will recognise that person automatically in future sightings.

### Web Dashboard
- **Live Overview** — stat cards showing today's total sightings, known vs. unknown counts, and active cameras, all updated in real time.
- **Interactive Analytics** — clickable stat cards and charts that drill down into hourly activity, known/unknown breakdown, weekly trends, per-camera activity, and a heatmap of activity by hour and day.
- **History Page** — full sighting log with face thumbnails, timestamps, camera names, and confidence scores. Supports multi-select, bulk naming, and bulk delete.
- **Click-to-Enlarge Lightbox** — click any face thumbnail in the History page to view a full-size snapshot with identification options.
- **Re-identification & Correction** — every detection card has a **Correct ID** button to correct a misidentification, a **Wrong ID** button to unassign a visitor, and a **Change Name** option directly from the lightbox.
- **People Management Page** — view all known people, their thumbnails, sighting counts, and last-seen times. Add new people, edit names, and delete records.
- **Settings Page** — manage camera RTSP streams, detection parameters, Telegram credentials, and general settings directly from the browser. Start, stop, or restart system services directly from the UI without SSH.
- **Passphrase Login** — protect the dashboard with a passphrase. Configurable session duration. Can be disabled for fully local-only deployments.
- **Live Status Indicators** — real-time navbar badges showing whether the Hailo NPU is active, and which Recognition Engine (ArcFace vs HOG) is currently loaded.
- **Recognition Engine Details** — dedicated card in Settings showing the active AI model, threshold, number of people trained, and total encodings in the database.

### Telegram Notifications
- **Instant Unknown-Visitor Alerts** with a face snapshot photo sent the moment an unknown person is detected.
- **Inline Identification Buttons** — tap directly in Telegram to identify the person without opening the dashboard:
  - **"It's [Name]"** — up to 6 buttons for your most-recently-seen known people.
  - **"🚫 Keep Unknown"** — dismiss the buttons and leave the sighting as-is.
  - **"➕ Add as New Person"** — the bot prompts you to reply with a name, then creates the visitor record, saves the face encoding, and confirms.
- **Known-Visitor Alerts** — optional instant notification when a recognised person is seen.
- **Daily Summary** — a digest of the day's sightings sent at a configured time (e.g., 20:00).
- **Long-polling** — no webhook URL or port-forwarding required. The bot polls Telegram's servers from inside your network.

### Privacy & Security
- **100% Local Processing** — no video, images, or face data ever leave your home network.
- **No Cloud Subscription** — fully self-hosted on your Raspberry Pi.
- **Cloudflare Tunnel Support** — securely access your dashboard from anywhere without opening firewall ports.

---

## 📋 Hardware Requirements

| Component | Requirement |
|---|---|
| Single-board computer | Raspberry Pi 5 (4 GB or 8 GB RAM recommended) |
| AI accelerator | Raspberry Pi AI HAT+ (Hailo-8L, 13 TOPS) |
| Cooling | Active Cooler for Raspberry Pi 5 (recommended) |
| Storage | MicroSD Card or NVMe SSD, 32 GB+ |
| Cameras | One or more RTSP-enabled IP cameras (e.g., Reolink, Amcrest, Tapo, UniFi) |

---

## 🛠️ Step 1: Raspberry Pi OS & Hardware Setup

1. Install **Raspberry Pi OS (64-bit) Bookworm** or later using Raspberry Pi Imager.
2. Assemble the AI HAT+ according to the [official Raspberry Pi documentation](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html).
3. Enable PCIe Gen 3 for maximum Hailo performance (optional but recommended):
   ```bash
   sudo raspi-config
   # Advanced Options → PCIe Speed → Enable Gen 3 → Reboot
   ```

---

## 📥 Step 2: Hailo Software Setup

The Hailo SDK (`hailo-all`) is required for the NPU to function and is **not** installable via pip.

1. Install the Hailo software suite from the Raspberry Pi apt repository:
   ```bash
   sudo apt update
   sudo apt full-upgrade
   sudo apt install hailo-all
   ```
2. Verify the device is recognized:
   ```bash
   hailortcli fw-control identify
   ```
3. Add your user to the `video` group for hardware access:
   ```bash
   sudo usermod -a -G video $USER
   # Log out and back in, or reboot
   ```

> See [`docs/HAILO_SETUP.md`](docs/HAILO_SETUP.md) for detailed troubleshooting and [`docs/DEPENDENCY_NOTES.md`](docs/DEPENDENCY_NOTES.md) for critical notes on pinned package versions.

---

## 📦 Step 3: Project Setup & Dependencies

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tektekgo/seewhozthere.git ~/projects/seewhozthere
   cd ~/projects/seewhozthere
   ```

2. **Download the Hailo Model:**
   The pre-compiled RetinaFace MobileNet model must be placed in the `models/` directory:
   ```bash
   mkdir -p models
   wget -O models/retinaface_mobilenet_v1.hef \
     https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/FaceDetection/Detection/retinaface_mobilenet_v1/pretrained/2023-07-18/retinaface_mobilenet_v1.hef
   ```

3. **Run the setup script:**
   This creates a Python virtual environment and installs all pinned dependencies. The version pins are critical for Hailo SDK compatibility — do not upgrade packages without consulting [`docs/DEPENDENCY_NOTES.md`](docs/DEPENDENCY_NOTES.md).
   ```bash
   ./setup.sh
   ```

4. **Build the Web Dashboard:**
   This compiles the React frontend into static files that the FastAPI server can serve.
   ```bash
   ./build_frontend.sh
   ```

---

## ⚙️ Step 4: Configuration

1. **Copy the example configuration:**
   ```bash
   cp config.ini.example config.ini
   ```

2. **Edit `config.ini`:**
   ```bash
   nano config.ini
   ```

The full set of configuration sections is described below.

### `[GENERAL]`

| Key | Default | Description |
|---|---|---|
| `timezone` | `UTC` | Your local timezone (e.g., `America/New_York`, `Asia/Kolkata`). Do **not** use quotes. |
| `port` | `7222` | Port for the web dashboard. |
| `database_path` | `data/seewhozthere.db` | Path to the SQLite database file. |

### `[CAMERAS]`

Add one line per camera in the format `name = rtsp://user:pass@ip:port/stream`. Do **not** use quotes around RTSP URLs.

```ini
[CAMERAS]
front_door = rtsp://admin:MyStr0ngPass@192.168.1.100:554/stream1
driveway   = rtsp://admin:MyStr0ngPass@192.168.1.101:554/stream1
```

**Best practice:** Reserve a static IP for each camera in your router's DHCP settings and use a strong, unique password. If you change a camera's IP later, update `config.ini` and push the change to your source control repository.

### `[SECURITY]`

| Key | Default | Description |
|---|---|---|
| `passphrase` | `changeme` | Passphrase to access the web dashboard. Change this before exposing the dashboard externally. Leave blank to disable login (not recommended). |
| `session_hours` | `24` | How long a login session lasts before requiring re-authentication. |

### `[TELEGRAM]`

| Key | Description |
|---|---|
| `bot_token` | Your Telegram bot's HTTP API token from `@BotFather`. |
| `chat_id` | Your personal Telegram Chat ID from `@userinfobot`. |

### `[SCHEDULER]`

| Key | Default | Description |
|---|---|---|
| `enabled` | `false` | Set to `true` to enable the daily summary notification. |
| `send_time` | `20:00` | Time to send the daily summary in 24-hour `HH:MM` format. |
| `service` | `telegram` | Notification service to use (`telegram`). |

### `[DETECTION]`

| Key | Default | Description |
|---|---|---|
| `snapshot_cooldown_seconds` | `15` | Minimum seconds between saved snapshots per camera. Lower = more photos per visit; higher = fewer. Recommended: 15–30 s. |
| `confidence_threshold` | `0.15` | Minimum Hailo detection confidence (0.0–1.0). Recommended: `0.15` for outdoor cameras using the Hailo RetinaFace model. |
| `recognition_threshold` | `0.45` | Minimum ArcFace similarity score (0.0–1.0) to identify a known person. Recommended: `0.40`–`0.45`. |
| `min_face_width` | `35` | Minimum face width in pixels. Rejects small distant detections. Recommended: `35` outdoors to catch faces at distance. |
| `min_face_height` | `35` | Minimum face height in pixels. Same guidance as width. |

---

## 📱 Step 5: Telegram Bot Setup (Optional but Recommended)

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, choose a name and username, and copy the **HTTP API Token**.
3. Search for `@userinfobot` to get your personal **Chat ID**.
4. Paste both values into the `[TELEGRAM]` section of `config.ini`.

Once configured, every unknown-visitor alert will include inline buttons:

```
🚨 Unknown visitor detected
Camera: Front Door  |  Time: 14:32:07
— SeeWhozThere®

[ It's Sujit    ]
[ It's Sandhya  ]
[ 🚫 Keep Unknown  |  ➕ Add as New Person ]
```

Tapping **"It's [Name]"** updates the database, extracts a face encoding from the snapshot so the system recognises that person automatically next time, and edits the message to show `✅ Identified: [Name]`.

Tapping **"Add as New Person"** removes the buttons and prompts you to reply with a name. The bot creates the visitor record, saves the face encoding, and confirms with a `✅` message.

> **Group chat note:** If your bot is in a Telegram group rather than a DM, go to `@BotFather → Bot Settings → Group Privacy → Turn Off` so the bot can read your name-reply message.

---

## 🚀 Step 6: Start the Services

SeeWhozThere® runs as two separate `systemd` services.

| Service | Description |
|---|---|
| `seewhozthere` | Background face detection and recognition processor |
| `seewhozthere-web` | FastAPI web dashboard (port 7222) + Telegram callback polling loop |

1. **Install and start both services:**
   ```bash
   ./install_service.sh
   ```

2. **Verify they are running:**
   ```bash
   sudo systemctl status seewhozthere
   sudo systemctl status seewhozthere-web
   ```

The web dashboard is accessible on your local network at:
`http://<YOUR_PI_IP>:7222/dashboard`

---

## 🌐 Step 7: Secure Remote Access via Cloudflare Tunnel

To access your dashboard securely from anywhere without opening firewall ports:

1. Create a free account on [Cloudflare Zero Trust](https://one.dash.cloudflare.com/).
2. Go to **Networks → Tunnels** and create a new tunnel.
3. Install `cloudflared` on your Raspberry Pi using the command provided in the Cloudflare dashboard.
4. Route a Public Hostname (e.g., `seewhozthere.yourdomain.com`) to `http://localhost:7222`.

**Important Cache Configuration:**
Cloudflare may aggressively cache the dashboard's JavaScript files. To ensure you always see the latest version after an update, create a **Cache Rule** in your Cloudflare dashboard:

- **Rule name:** `Bypass cache for dashboard assets`
- **When incoming requests match:** URI Path → contains → `/dashboard/assets/`
- **Cache eligibility:** Bypass cache

---

## 🧹 Automated Storage Cleanup

SeeWhozThere® can generate hundreds of snapshots per day. To prevent your Raspberry Pi's storage from filling up, an automated cleanup script is included.

The script (`cleanup_snapshots.py`) safely removes snapshot images older than a specified number of days and clears their corresponding database records, without affecting known visitor profiles or face encodings.

**Setup an automated daily cleanup (Cron Job):**
1. Open your terminal on the Raspberry Pi and edit your cron jobs:
   ```bash
   crontab -e
   ```
2. Add the following line at the bottom to run the cleanup script every night at 2:00 AM, keeping the last 7 days of history:
   ```bash
   0 2 * * * /usr/bin/python3 ~/projects/seewhozthere/cleanup_snapshots.py --days 7 >> ~/projects/seewhozthere/data/cleanup.log 2>&1
   ```
3. Save and exit.

---

## 🔄 Updating SeeWhozThere®

When new features are pushed to the repository, updating your Pi requires pulling the code and restarting **both** services.

### Quick Reference — What Requires Which Restart

The table below covers every type of change and exactly what needs to be restarted. **No database action is ever needed for config or code changes** — the database is only touched when a sighting is saved or a face encoding is updated.

| What changed | Restart needed | Notes |
|---|---|---|
| `config.ini` — any detection setting (`confidence_threshold`, `recognition_threshold`, `min_face_width`, etc.) | `sudo systemctl restart seewhozthere` | Read by the detection service at startup only |
| `hailo_processor_v2.py`, `retinaface_postprocessor.py`, `face_recognition_engine.py` | `sudo systemctl restart seewhozthere` | Detection pipeline files |
| `database.py`, `config.py`, `analytics.py` | `sudo systemctl restart seewhozthere` | Shared modules loaded at startup |
| `main.py` (any `/api/` endpoint) | `sudo systemctl restart seewhozthere-web.service` | FastAPI web server |
| `telegram_notifier.py` | `sudo systemctl restart seewhozthere-web.service` | Telegram polling loop runs inside the web service |
| Frontend JS/CSS (after `pnpm build`) | `sudo systemctl restart seewhozthere-web.service` + browser hard-refresh | Static files served by FastAPI |
| **Any `git pull`** | **`swt-restart` (both services)** | Safest default — restarts everything |
| Database schema change (new table or column in `database.py`) | `sudo systemctl restart seewhozthere` | Schema migrations run automatically on startup; no manual SQL needed |

### One-Command Restart Alias (Recommended)

To make updates foolproof, add this alias to your Pi once:

```bash
echo "alias swt-restart='sudo systemctl restart seewhozthere seewhozthere-web.service && echo \"Both SeeWhozThere® services restarted\"'" >> ~/.bashrc && source ~/.bashrc
```

Then, whenever you pull new code, simply run:

```bash
cd ~/projects/seewhozthere
git pull
swt-restart
```

---

## 🗂️ Project Structure

```
seewhozthere/
├── app/
│   ├── main.py                  # FastAPI application, all REST API endpoints
│   ├── hailo_processor_v2.py    # Real-time detection & recognition processor
│   ├── hailo_face_detector_v4.py# Hailo NPU pipeline wrapper
│   ├── face_recognition_engine.py # Face encoding and matching
│   ├── telegram_notifier.py     # Telegram alerts, inline buttons, polling loop
│   ├── database.py              # SQLite database layer
│   ├── analytics.py             # Analytics query helpers
│   └── config.py                # config.ini reader
├── frontend/                    # Pre-built React + TypeScript dashboard
├── models/                      # Hailo .hef model files (downloaded separately)
├── data/                        # Runtime data: database, snapshots, thumbnails
├── docs/                        # Supplementary documentation
├── config.ini.example           # Configuration template
├── setup.sh                     # Virtual environment & dependency installer
└── install_service.sh           # systemd service installer
```

---

## 📄 License

This project is proprietary and confidential. Designed & Created by Sujit G. All rights reserved.
