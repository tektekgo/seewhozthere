# Migration Guide: Fresh Raspberry Pi OS Trixie Installation

This guide will walk you through migrating from your current Raspberry Pi OS Bookworm installation to a fresh Raspberry Pi OS Trixie (Debian 13) installation, while preserving all your important data, configurations, and the SeeWhozThere project.

**Why fresh install?** The Raspberry Pi Foundation recommends fresh installation over upgrading due to potential package conflicts between Bookworm and Trixie, especially with Raspberry Pi-specific packages.

---

## Overview

The migration process consists of four main phases:

1. **Backup** - Save all important data from current system
2. **Flash** - Install fresh Trixie image to SD card
3. **Restore** - Transfer data and configurations back
4. **Setup** - Install HailoRT 4.23 and test SeeWhozThere

**Total time:** Approximately 2-3 hours

---

## Phase 1: Backup Your Current System

Before we begin, we need to back up everything important from your current Bookworm installation.

### 1.1. Create Backup Directory

On your current system, create a backup location:

```bash
mkdir -p ~/migration_backup
cd ~/migration_backup
```

### 1.2. Backup Your Project

```bash
# Backup SeeWhozThere project
cp -r ~/projects/seewhozthere ~/migration_backup/

# Backup database
cp ~/projects/seewhozthere/seewhozthere.db ~/migration_backup/ 2>/dev/null || echo "No database found"
```

### 1.3. Backup System Configurations

```bash
# Network configuration
sudo cp /etc/network/interfaces ~/migration_backup/ 2>/dev/null
sudo cp -r /etc/NetworkManager ~/migration_backup/ 2>/dev/null

# Hostname
sudo cp /etc/hostname ~/migration_backup/
sudo cp /etc/hosts ~/migration_backup/

# SSH keys
cp -r ~/.ssh ~/migration_backup/

# Git configuration
cp ~/.gitconfig ~/migration_backup/ 2>/dev/null
```

### 1.4. List Installed Packages

This will help you remember what software you had installed:

```bash
dpkg --get-selections > ~/migration_backup/installed_packages.txt
apt list --installed > ~/migration_backup/apt_packages.txt
```

### 1.5. Backup Important Services Configuration

```bash
# Docker (if you use it)
sudo cp -r /etc/docker ~/migration_backup/ 2>/dev/null

# Any custom systemd services
sudo cp -r /etc/systemd/system/*.service ~/migration_backup/ 2>/dev/null

# Cron jobs
crontab -l > ~/migration_backup/crontab.txt 2>/dev/null
```

### 1.6. Transfer Backup Off the Pi

**Option A: Copy to another computer via SCP**

From your computer (not the Pi):

```bash
scp -r pimediaadmin@plexpi:~/migration_backup ./raspberry_pi_backup
```

**Option B: Copy to USB drive**

On the Pi:

```bash
# Insert USB drive, then find it
lsblk

# Mount it (replace sdX1 with your USB device)
sudo mount /dev/sdX1 /mnt

# Copy backup
sudo cp -r ~/migration_backup /mnt/

# Unmount
sudo umount /mnt
```

**Option C: Push to GitHub**

```bash
cd ~/migration_backup
git init
git add .
git commit -m "Backup before Trixie migration"
# Push to a private repository
```

---

## Phase 2: Flash Raspberry Pi OS Trixie

Now we'll create a fresh Trixie installation on your SD card.

### 2.1. Download Raspberry Pi Imager

On your computer (Windows, Mac, or Linux):

- **Download from:** https://www.raspberrypi.com/software/
- Install and launch Raspberry Pi Imager

### 2.2. Prepare for Flashing

**⚠️ Important:** You'll need to shut down your Pi and remove the SD card. Make sure you've completed Phase 1 backup first!

```bash
# On the Pi, shut down
sudo shutdown -h now
```

Remove the SD card from your Pi and insert it into your computer.

### 2.3. Flash Trixie Image

In Raspberry Pi Imager:

1. **Choose Device:** Raspberry Pi 5
2. **Choose OS:** 
   - Scroll down to "Raspberry Pi OS (other)"
   - Select **"Raspberry Pi OS (64-bit)"** (this is Trixie)
   - **Release date:** 4 Dec 2025
   - **Debian version:** 13 (trixie)
3. **Choose Storage:** Select your SD card
4. **Click "Next"**

### 2.4. Configure OS Settings

When prompted "Would you like to apply OS customisation settings?", click **"Edit Settings"**:

**General Tab:**
- ✅ Set hostname: `plexpi` (or your preferred name)
- ✅ Set username and password: `pimediaadmin` / (your password)
- ✅ Configure wireless LAN: (your WiFi credentials)
- ✅ Set locale settings: (your timezone and keyboard)

**Services Tab:**
- ✅ Enable SSH
- Choose: "Use password authentication"

**Options Tab:**
- ✅ Eject media when finished

Click **"Save"**, then **"Yes"** to apply settings.

### 2.5. Write Image

Click **"Yes"** to confirm you want to erase the SD card. The process will take 5-15 minutes.

When complete, eject the SD card from your computer and insert it back into your Raspberry Pi.

---

## Phase 3: First Boot and Initial Setup

### 3.1. Boot the Pi

Power on your Raspberry Pi. It will take 1-2 minutes to boot for the first time.

### 3.2. Connect via SSH

From your computer:

```bash
ssh pimediaadmin@plexpi.local
# Or use the IP address if .local doesn't work
```

### 3.3. Verify Trixie Installation

```bash
lsb_release -a
```

You should see:
```
Description:    Debian GNU/Linux 13 (trixie)
Release:        13
Codename:       trixie
```

### 3.4. Update System

```bash
sudo apt update
sudo apt full-upgrade -y
```

---

## Phase 4: Restore Data and Install Software

### 4.1. Transfer Backup to New System

**Option A: From another computer**

From your computer:

```bash
scp -r ./raspberry_pi_backup pimediaadmin@plexpi:~/migration_backup
```

**Option B: From USB drive**

On the Pi:

```bash
sudo mount /dev/sdX1 /mnt
cp -r /mnt/migration_backup ~/
sudo umount /mnt
```

### 4.2. Restore Project

```bash
mkdir -p ~/projects
cp -r ~/migration_backup/seewhozthere ~/projects/
cd ~/projects/seewhozthere
```

### 4.3. Install Essential Software

```bash
# Git
sudo apt install -y git

# Python and dependencies
sudo apt install -y python3 python3-pip python3-venv

# OpenCV dependencies
sudo apt install -y python3-opencv

# Database tools
sudo apt install -y sqlite3

# Network tools
sudo apt install -y curl wget net-tools
```

### 4.4. Restore SSH Keys

```bash
cp -r ~/migration_backup/.ssh ~/
chmod 700 ~/.ssh
chmod 600 ~/.ssh/*
```

### 4.5. Restore Git Configuration

```bash
cp ~/migration_backup/.gitconfig ~/ 2>/dev/null || echo "No git config to restore"
```

---

## Phase 5: Install HailoRT 4.23

Now we can install the latest HailoRT with full Python API support!

### 5.1. Install DKMS

```bash
sudo apt install -y dkms
```

### 5.2. Install Hailo Software

```bash
sudo apt install -y hailo-all
```

### 5.3. Verify Installation

```bash
hailortcli fw-control identify
```

You should see:
```
Firmware Version: 4.23.0
Device Architecture: HAILO8L
```

### 5.4. Test Python API

```bash
python3 -c "from hailo_platform import HEF, VDevice; print('✅ Hailo Python API works!')"
```

---

## Phase 6: Setup and Test SeeWhozThere

### 6.1. Install Project Dependencies

```bash
cd ~/projects/seewhozthere
pip3 install -r requirements.txt --break-system-packages
```

### 6.2. Verify Model Files

```bash
ls -lh models/
```

You should see `retinaface_mobilenet_v1.hef` (13 MB).

### 6.3. Test Hailo Detection

```bash
python3 test_hailo_minimal.py
```

This should now **pass without errors**!

### 6.4. Run Full Application

```bash
python3 test_hailo.py
```

You should see:
- ✅ Hailo device detected
- ✅ Model loaded
- ✅ Face detection running at **60-100 FPS**!

---

## Phase 7: Final Configuration

### 7.1. Restore Hostname (if needed)

```bash
sudo cp ~/migration_backup/hostname /etc/hostname
sudo cp ~/migration_backup/hosts /etc/hosts
sudo reboot
```

### 7.2. Restore Cron Jobs (if any)

```bash
crontab ~/migration_backup/crontab.txt
```

### 7.3. Install Additional Software

Review your backup package list:

```bash
cat ~/migration_backup/installed_packages.txt
```

Install any additional software you need.

---

## Troubleshooting

### Issue: Can't SSH to Pi

**Solution:** Find the Pi's IP address by checking your router, or connect a monitor/keyboard.

### Issue: Hailo device not found

**Solution:** 
```bash
# Check if Hailo is detected
ls -la /dev/hailo*

# Reinstall driver
sudo apt reinstall hailo-all
sudo reboot
```

### Issue: Python packages won't install

**Solution:** Use `--break-system-packages` flag:
```bash
pip3 install <package> --break-system-packages
```

---

## Summary

After completing this migration, you will have:

✅ Fresh Raspberry Pi OS Trixie (Debian 13) installation  
✅ HailoRT 4.23 with full Python API support  
✅ SeeWhozThere project restored and working  
✅ Hailo AI HAT+ running at full speed (60-100 FPS)  
✅ All your data and configurations restored  

---

## Next Steps

1. Test your camera stream
2. Verify face detection is working
3. Set up the web dashboard
4. Configure systemd service for auto-start

Congratulations! You're now running the latest Raspberry Pi OS with full Hailo acceleration! 🎉
