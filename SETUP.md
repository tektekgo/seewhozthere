# SeeWhozThere® — Getting Started Guide

Welcome to SeeWhozThere®! This guide is designed to take you from a brand-new Raspberry Pi straight through to a fully functioning, private, AI-powered home security system. 

We have written this guide step-by-step so that anyone can follow it. You don't need to be a Linux expert, but you will need to run a few commands in the terminal.

---

## 1. What You Need Before You Start

### Hardware Checklist
- **Raspberry Pi 5** (4 GB or 8 GB RAM)
- **Raspberry Pi AI HAT+** (Hailo-8L, 13 TOPS model)
- **Active Cooler** for Raspberry Pi 5 (highly recommended to prevent overheating)
- **MicroSD Card** (32 GB or larger, high-speed A2 class recommended)
- **Official Raspberry Pi 5 Power Supply** (5V/5A)

### Camera Requirements
You need at least one IP camera that supports **RTSP** (Real-Time Streaming Protocol). Most security cameras support this, including:
- Tapo (e.g., C310, C320WS)
- Reolink
- Amcrest
- UniFi Protect

**Before proceeding**, find your camera's RTSP URL. It usually looks like this:
`rtsp://username:password@192.168.1.100:554/stream1`
*(You can usually find this in your camera's mobile app settings or by searching "[Camera Brand] RTSP URL" online).*

---

## 2. Prepare Your Raspberry Pi

1. **Install the Operating System:**
   Use the official [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer.
   - Choose **Raspberry Pi OS (64-bit)** (Bookworm release).
   - *Important:* The 64-bit version is strictly required for the Hailo AI drivers.

2. **Assemble the Hardware:**
   Attach the Active Cooler to the Pi, then mount the AI HAT+ on top according to the [official instructions](https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html).

3. **Boot Up:**
   Insert the SD card, plug in the power, and connect to your network (Wi-Fi or Ethernet).

4. **Enable the PCIe Interface (Crucial for the AI chip):**
   Open a terminal on your Pi and run:
   ```bash
   sudo raspi-config
   ```
   - Go to **Advanced Options** → **PCIe Speed**
   - Choose **Yes** to enable PCIe Gen 3.
   - Finish and reboot when prompted.

---

## 3. Install the Hailo AI Drivers

The Hailo-8L chip is the brain of this system. It processes the video feeds locally without sending anything to the cloud. We need to install its software.

Open a terminal and run these commands one by one:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install hailo-all -y
```

Next, give your user account permission to access the video hardware:
```bash
sudo usermod -a -G video $USER
```

**Reboot your Pi** to apply the permissions:
```bash
sudo reboot
```

After the Pi turns back on, verify the AI chip is working:
```bash
hailortcli fw-control identify
```
*(You should see output confirming a Hailo-8L device is present).*

---

## 4. Download and Setup SeeWhozThere®

Now we will download the software and set up its isolated Python environment.

1. **Download the code:**
   ```bash
   mkdir -p ~/projects
   cd ~/projects
   git clone https://github.com/tektekgo/seewhozthere.git
   cd seewhozthere
   ```

2. **Download the AI Face Detection Model:**
   ```bash
   mkdir -p models
   wget -O models/retinaface_mobilenet_v1.hef https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/FaceDetection/Detection/retinaface_mobilenet_v1/pretrained/2023-07-18/retinaface_mobilenet_v1.hef
   ```

3. **Run the Setup Script:**
   This script creates a safe "virtual environment" so our software doesn't conflict with your Pi's system files.
   ```bash
   ./setup.sh
   ```

4. **Build the Web Dashboard:**
   This compiles the beautiful user interface you will use to manage the system.
   ```bash
   ./build_frontend.sh
   ```

---

## 5. Configure Your System

The system needs to know where your cameras are and how you want it to behave.

1. **Create your configuration file:**
   ```bash
   cp config.ini.example config.ini
   nano config.ini
   ```

2. **Edit the file:**
   Use the arrow keys to move around. Change these specific lines:

   - **`[GENERAL]`**
     Change `timezone` to your local timezone (e.g., `America/New_York` or `Europe/London`).

   - **`[SECURITY]`**
     Change `passphrase = changeme` to a secure password. You will use this to log into the dashboard.

   - **`[CAMERAS]`**
     Add your camera(s) here. Do not use quotes.
     ```ini
     [CAMERAS]
     front_door = rtsp://admin:password@192.168.1.100:554/stream1
     ```

   - **`[DETECTION]`**
     If your camera is outdoors, change `confidence_threshold` to `0.15` and `min_face_width` to `35`.

3. **Save and Exit:**
   Press `Ctrl+O`, then `Enter` to save. Press `Ctrl+X` to exit.

---

## 6. Start the Services

We are ready to turn the system on! We will install it as a background service so it automatically starts whenever your Pi is plugged in.

```bash
./install_service.sh
```

The script will confirm that two services are running:
1. `seewhozthere` (The AI brain looking at the cameras)
2. `seewhozthere-web` (The dashboard you view in your browser)

---

## 7. Your First Login

1. Open a web browser on your computer or phone (must be on the same Wi-Fi as the Pi).
2. Go to: `http://<YOUR_PI_IP_ADDRESS>:7222/dashboard`
   *(If you don't know your Pi's IP address, type `hostname -I` in the Pi's terminal).*
3. Enter the passphrase you set in `config.ini`.

**You should now see the SeeWhozThere® dashboard!** 

---

## 8. Teaching the System Your Face

Right now, the system doesn't know who anyone is. Every face it sees will be marked as "Unknown". Here is how to teach it:

1. Walk outside in front of your camera. Look at it for a few seconds.
2. Go to your Dashboard and click on the **History** tab.
3. You will see a snapshot of your face. Click the **Change Name** or **Correct ID** button.
4. Type your name (e.g., "John") and save.

**What just happened?** 
The system just extracted a mathematical map of your face (an "encoding") and saved it to the database. The next time you walk outside, it will recognize you automatically!

*Tip: For the best accuracy, correct your face 4 or 5 times in different lighting conditions. The system learns and gets smarter every time you correct it.*

---

## 9. Set Up Telegram Alerts (Highly Recommended)

SeeWhozThere® can send a photo to your phone the second an unknown person is detected.

1. Open the Telegram app on your phone and search for `@BotFather`.
2. Send the message `/newbot` and follow the prompts to name your bot.
3. BotFather will give you an **HTTP API Token**. Copy it.
4. Search Telegram for `@userinfobot` and press Start. It will give you your **Id** (a string of numbers). Copy it.
5. Go to the **Settings** page in your SeeWhozThere® dashboard.
6. Paste the Token and Chat ID into the Telegram section and click Save.

Now, when someone walks up to your door, you will get a Telegram message with their photo and buttons to instantly identify them right from the chat!

---

## 10. Automated Storage Cleanup

The system saves a snapshot every time it sees a face. To prevent your SD card from filling up, set up this automated cleanup job to delete photos older than 7 days (it will NOT delete your learned faces).

1. Open a terminal on the Pi and run:
   ```bash
   crontab -e
   ```
2. Add this exact line to the very bottom:
   ```bash
   0 2 * * * /usr/bin/python3 ~/projects/seewhozthere/cleanup_snapshots.py --days 7 >> ~/projects/seewhozthere/data/cleanup.log 2>&1
   ```
3. Save and exit.

---

## Keeping the System Updated

When new features are released, you can update your system easily. We recommend adding this shortcut to your Pi once:

```bash
echo "alias swt-restart='sudo systemctl restart seewhozthere seewhozthere-web.service && echo \"Both SeeWhozThere® services restarted\"'" >> ~/.bashrc && source ~/.bashrc
```

Now, whenever you want to update, just run:
```bash
cd ~/projects/seewhozthere
git pull
swt-restart
```

Enjoy your private, AI-powered security system!
