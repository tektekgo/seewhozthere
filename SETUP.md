# SeeWhozThere: Complete Setup Guide

This guide provides step-by-step instructions to set up the SeeWhozThere smart security system on a Raspberry Pi 5 with a Hailo AI HAT+. It assumes you are starting with a fresh Raspberry Pi OS installation.

## 1. Hardware & OS Requirements

### Hardware

- **Raspberry Pi 5** (4GB or 8GB recommended)
- **Hailo AI HAT+**
- **microSD Card** (32GB or larger, high-speed recommended)
- **Raspberry Pi 5 Official Power Supply** (5V/5A)
- **RTSP-enabled IP Camera** (e.g., Tapo C310)

### Operating System

- **Raspberry Pi OS (64-bit) with Desktop** - Bookworm release. The 64-bit version is required for the Hailo drivers.

## 2. OS Configuration

### Step 2.1: Enable PCIe Interface

The Hailo AI HAT+ connects via the Raspberry Pi 5's PCIe interface. You must enable it.

1.  Open a terminal on your Raspberry Pi.
2.  Edit the EEPROM configuration:
    ```bash
    sudo rpi-eeprom-config --edit
    ```
3.  Add the following line to the file:
    ```
    PCIE_PROBE=1
    ```
4.  Save the file and reboot:
    ```bash
    sudo reboot
    ```

## 3. Hailo Driver & Runtime Installation

These steps are critical for the AI accelerator to function. The drivers are not available on PyPI and must be installed manually.

### Step 3.1: Add Hailo's APT Repository

```bash
sudo wget https://hailo-cs.s3.eu-west-2.amazonaws.com/public/Hailo-Public-GPG-Key.asc -O /usr/share/keyrings/hailo-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hailo-archive-keyring.gpg] https://hailo-cs.s3.eu-west-2.amazonaws.com/hailo-apt-stable/ bookworm main" | sudo tee /etc/apt/sources.list.d/hailo.list
sudo apt-get update
```

### Step 3.2: Install Hailo Packages

```bash
sudo apt-get install -y hailo-dkms hailort hailortcli
```

### Step 3.3: Verify Installation

After a reboot, check that the Hailo device is detected.

```bash
sudo reboot
```

After the reboot, run:

```bash
hailortcli scan
```

You should see output indicating that a Hailo-8L device was found.

## 4. Project Setup

### Step 4.1: Clone the Repository

```bash
cd ~/
mkdir projects
cd projects
git clone https://github.com/tektekgo/seewhozthere.git
cd seewhozthere
```

### Step 4.2: Python Environment & Dependencies

1.  **Install Python and venv**:
    ```bash
    sudo apt-get install -y python3-pip python3-venv
    ```
2.  **Create and activate a virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Install pinned dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Step 4.3: Download the AI Model

The face detection model is not included in the repository. Download it and place it in the `models` directory.

```bash
mkdir models
wget https://github.com/hailo-ai/hailo_model_zoo/raw/master/models_files/retinaface_mobilenet_v1_736x1280_hailo8l.hef -O models/retinaface_mobilenet_v1.hef
```

## 5. Configuration

### Step 5.1: Create `config.ini`

Copy the example configuration file:

```bash
cp config.ini.example config.ini
```

### Step 5.2: Edit `config.ini`

Open the file `config.ini` with a text editor (e.g., `nano config.ini`) and configure the following sections:

-   **`[CAMERAS]`**: Add your camera's RTSP URL. The name you give it (e.g., `front_door`) will be used in the dashboard.
    ```ini
    [CAMERAS]
    front_door = rtsp://user:password@192.168.1.100:554/stream1
    ```
-   **`[SECURITY]`**: Change the `passphrase` to something secure. This will be used to log in to the web dashboard.
    ```ini
    [SECURITY]
    passphrase = your_secret_passphrase_here
    ```

## 6. Systemd Service Installation

This will run the detection and web server processes automatically in the background.

```bash
sudo ./install_service.sh
```

This script will:
1.  Copy the `.service` files to `/etc/systemd/system/`.
2.  Reload the systemd daemon.
3.  Enable and start both `seewhozthere.service` and `seewhozthere-web.service`.

## 7. First Run & Verification

1.  **Check Service Status**:
    ```bash
    sudo systemctl status seewhozthere
    sudo systemctl status seewhozthere-web
    ```
    Both should show `Active: active (running)`.

2.  **Access the Dashboard**:
    Open a web browser on the same network and go to `http://<your_pi_ip_address>:7222`.

3.  **Log In**:
    Use the passphrase you set in `config.ini`.

4.  **Test Detection**:
    Walk in front of your camera. Your face should appear on the dashboard's history page within a few seconds.

## 8. Automated Storage Cleanup (Cron Job)

SeeWhozThere® saves a snapshot every time a face is detected. Over time, this can fill up your Raspberry Pi's SD card. An automated cleanup script is included to safely delete old snapshots while preserving your AI's learned face encodings.

1. Open your terminal on the Raspberry Pi.
2. Edit your cron jobs:
   ```bash
   crontab -e
   ```
3. Add the following line at the bottom of the file. This will run the cleanup script every night at 2:00 AM and delete snapshots older than 7 days:
   ```bash
   0 2 * * * /usr/bin/python3 /home/ubuntu/projects/seewhozthere/cleanup_snapshots.py --days 7 >> /home/ubuntu/projects/seewhozthere/cleanup.log 2>&1
   ```
4. Save and exit the editor.

## 9. Troubleshooting

-   **Web server not starting**: Check the logs with `sudo journalctl -u seewhozthere-web -n 50 --no-pager`.
-   **Detection service not starting**: Check the logs with `sudo journalctl -u seewhozthere -n 50 --no-pager`.
-   **No faces detected**: Verify the camera RTSP URL is correct and accessible.

## 10. Frontend Development (Optional)

If you want to modify the web dashboard, you will need to set up the frontend development environment.

### Step 9.1: Install Node.js and npm

We recommend using Node.js version 22.x.

```bash
# Install nvm (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# Reload your shell to use nvm
source ~/.bashrc

# Install and use Node.js v22
nvm install 22
nvm use 22
```

### Step 9.2: Install Frontend Dependencies

```bash
cd ~/projects/seewhozthere/frontend
npm install
```

### Step 9.3: Run the Development Server

This will start a local development server for the frontend on port 8080, which will proxy API requests to the FastAPI backend running on port 7222.

```bash
npm run dev
```

Now you can access the development dashboard at `http://<your_pi_ip_address>:8080`.


## Appendix: Camera Capacity

The number of cameras you can reliably run depends on your Raspberry Pi model and the complexity of your RTSP streams. The Hailo AI HAT+ handles the heavy lifting of face detection, but the Pi's CPU is still responsible for decoding each camera's video stream.

### Recommendations for Raspberry Pi 5

| Camera Count | Expected Performance |
|---|---|
| 1–2 cameras | Excellent — full detection rate, no frame drops |
| 3–4 cameras | Good — slight increase in inference queue wait time, still reliable |
| 5–6 cameras | Acceptable — recommend increasing `detection_interval` to 2–3s to reduce CPU load |
| 7+ cameras | Not recommended without tuning — RTSP decode threads compete for CPU, frame drops likely |

**Practical recommendation: 4 cameras is the sweet spot for a Pi 5 with Hailo HAT+.**

### Tuning for Higher Camera Counts

If you need to run more than 4 cameras, you can improve performance by editing `config.ini`:

- **Increase `detection_interval`**: In the `[DETECTION]` section, set `detection_interval = 2` or `3`. This tells the processor to only analyze a frame every 2-3 seconds per camera, significantly reducing CPU load from frame preprocessing.
- **Lower camera resolution/framerate**: If your cameras support it, lower the RTSP stream to 720p or 10-15 FPS. This reduces the amount of data the CPU needs to decode.
