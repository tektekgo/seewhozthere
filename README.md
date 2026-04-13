# SeeWhozThere®

SeeWhozThere® is an advanced, privacy-first home security and face recognition system designed specifically for the Raspberry Pi 5 with the Hailo-8L AI Accelerator. It processes local RTSP camera streams in real-time, identifies known and unknown visitors, and provides a beautiful web dashboard and Telegram notifications.

<p align="center">
  <img src="frontend/public/logo.png" width="120" alt="SeeWhozThere Logo">
</p>

## 🌟 Features

- **Real-time Face Detection**: Powered by the Hailo-8L NPU for high-performance edge inference (25-30 FPS).
- **Face Recognition**: Automatically identifies known visitors and flags unknown faces.
- **Interactive Dashboard**: View live detections, filter history, correct misidentifications, and manage known people.
- **Telegram Notifications**: Instant alerts with snapshots for unknown visitors, and daily summary reports.
- **Privacy First**: 100% local processing. No cloud subscription, no video feeds sent to third-party servers.
- **Cloudflare Tunnel Support**: Securely access your dashboard from anywhere without opening firewall ports.

---

## 📋 Hardware Requirements

To run SeeWhozThere®, you will need:

1. **Raspberry Pi 5** (4GB or 8GB RAM recommended)
2. **Raspberry Pi AI HAT+** (with Hailo-8L NPU)
3. **Active Cooling** (Active Cooler or similar recommended due to AI workload)
4. **RTSP-enabled IP Cameras** (e.g., Reolink, Amcrest, Tapo, UniFi)
5. **MicroSD Card or NVMe SSD** (32GB+ recommended)

---

## 🛠️ Step 1: Raspberry Pi OS & Hardware Setup

1. Install **Raspberry Pi OS (64-bit) Bookworm** or later.
2. Assemble the AI HAT+ according to the official Raspberry Pi documentation.
3. Enable PCIe Gen 3 (optional but recommended for maximum Hailo performance):
   ```bash
   sudo raspi-config
   # Go to Advanced Options -> PCIe Speed -> Enable Gen 3
   # Reboot
   ```

---

## 📥 Step 2: Hailo Software Setup

The Hailo SDK is required for the NPU to function.

1. Install the Hailo software suite:
   ```bash
   sudo apt update
   sudo apt full-upgrade
   sudo apt install hailo-all
   ```
2. Verify the Hailo device is recognized:
   ```bash
   hailortcli fw-control identify
   ```
3. Add your user to the `video` group to allow hardware access:
   ```bash
   sudo usermod -a -G video $USER
   # Log out and log back in, or reboot
   ```

---

## 📦 Step 3: Project Setup & Dependencies

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tektekgo/seewhozthere.git
   cd seewhozthere
   ```

2. **Download the Hailo Model:**
   Download the pre-compiled RetinaFace model for Hailo-8L into the `models` directory:
   ```bash
   mkdir -p models
   wget -O models/retinaface_mobilenet_v1.hef https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/FaceDetection/Detection/retinaface_mobilenet_v1/pretrained/2023-07-18/retinaface_mobilenet_v1.hef
   ```

3. **Run the setup script:**
   This creates a Python virtual environment and installs all pinned dependencies (crucial for Hailo compatibility).
   ```bash
   ./setup.sh
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
   * **`[CAMERAS]`**: Add your camera RTSP streams.
     * *Best Practice*: Reserve a static IP for your cameras in your router, and use a strong, complex username/password.
     * *Workflow*: If you change camera IPs later, update `config.ini` locally and commit/push your changes to your source control.
   * **`[SECURITY]`**: Set a strong `passphrase` for the web dashboard.
   * **`[TELEGRAM]`**: Add your Bot Token and Chat ID (see Step 5).

---

## 📱 Step 5: Telegram Bot Setup (Optional but Recommended)

To receive instant alerts with photos when an unknown person is detected:

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, choose a name and username, and copy the **HTTP API Token**.
3. Search for `@userinfobot` to get your personal **Chat ID**.
4. Paste both into the `[TELEGRAM]` section of your `config.ini`.

---

## 🚀 Step 6: Start the Services

SeeWhozThere® runs as two separate `systemd` services: the background detection processor and the web dashboard.

1. **Install and start the services:**
   ```bash
   ./install_service.sh
   ```
2. **Verify they are running:**
   ```bash
   sudo systemctl status seewhozthere
   sudo systemctl status seewhozthere-web
   ```

The web dashboard is now accessible on your local network at:
`http://<YOUR_PI_IP>:7222`

---

## 🌐 Step 7: Secure Remote Access via Cloudflare Tunnel

To access your dashboard securely from anywhere without opening ports on your router:

1. Create a free account on [Cloudflare Zero Trust](https://one.dash.cloudflare.com/).
2. Go to **Networks → Tunnels** and create a new tunnel.
3. Install `cloudflared` on your Raspberry Pi using the command provided in the dashboard.
4. Route a Public Hostname (e.g., `seewhozthere.yourdomain.com`) to `http://localhost:7222`.

**Important Cache Configuration:**
Cloudflare may aggressively cache the dashboard's JavaScript files. To ensure you always see the latest version after an update, create a **Cache Rule** in your Cloudflare dashboard:
- **Rule name**: `Bypass cache for dashboard assets`
- **When incoming requests match**: URI Path → contains → `/dashboard/assets/`
- **Cache eligibility**: Bypass cache

---

## 🔄 Updating SeeWhozThere®

When new features are pushed to the repository, updating your Pi is simple:

```bash
cd ~/projects/seewhozthere
git pull
sudo systemctl restart seewhozthere-web
```
*Note: Because the built frontend files are tracked in git, no Node.js build step is required on the Pi.*

---

## 📄 License

This project is proprietary and confidential. Designed & Created by Sujit G. All rights reserved.
