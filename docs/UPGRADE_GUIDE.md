# Upgrade Guide: Debian Bookworm to Trixie & HailoRT 4.23

This guide provides a comprehensive walkthrough for upgrading your Raspberry Pi from Debian 12 (Bookworm) to Debian 13 (Trixie) and upgrading HailoRT to version 4.23. This will enable full Python API support for your Hailo AI HAT+.

**Disclaimer:** This is a major OS upgrade. While the process is generally safe, there is always a risk of data loss or system instability. **Please back up your system before proceeding.**

## Phase 1: System Backup

Before starting the upgrade, it is crucial to back up your system. This will allow you to restore your system if anything goes wrong.

### 1.1. Full System Backup (Recommended)

The safest method is to create a full backup of your SD card. You can do this by shutting down your Raspberry Pi, removing the SD card, and using a tool like **Raspberry Pi Imager** or **Win32DiskImager** to create a full image of the SD card.

### 1.2. Manual Backup

If you prefer a manual backup, you should at least back up the following:

-   `/etc`
-   `/var/lib/dpkg`
-   `/var/lib/apt/extended_states`
-   The output of `dpkg --get-selections \*`
-   Your home directory (`/home/pimediaadmin`)

## Phase 2: Upgrade Debian from Bookworm to Trixie

This phase will upgrade your operating system from Debian 12 (Bookworm) to Debian 13 (Trixie).

### 2.1. Update Current System

First, ensure your current system is fully up to date:

```bash
sudo apt update
sudo apt full-upgrade
```

### 2.2. Update `sources.list`

Next, you need to update your APT sources to point to the Trixie repositories. Edit the `/etc/apt/sources.list` file and any files in `/etc/apt/sources.list.d/` and change all occurrences of `bookworm` to `trixie`.

You can do this with `sed`:

```bash
sudo sed -i 's/bookworm/trixie/g' /etc/apt/sources.list
sudo sed -i 's/bookworm/trixie/g' /etc/apt/sources.list.d/*.list
```

### 2.3. Refresh Package Index

After updating your sources, refresh your package index:

```bash
sudo apt update
```

### 2.4. Upgrade to Trixie

Now you can begin the upgrade to Trixie. This process will take some time and may require you to answer some questions about package configuration.

```bash
sudo apt full-upgrade
```

### 2.5. Reboot

Once the upgrade is complete, reboot your Raspberry Pi:

```bash
sudo reboot
```

## Phase 3: Upgrade HailoRT to 4.23

Now that your system is running Debian Trixie, you can upgrade HailoRT to version 4.23.

### 3.1. Install `dkms`

`dkms` is required to build the Hailo driver:

```bash
sudo apt install dkms
```

### 3.2. Install `hailo-all`

The `hailo-all` package will install the latest HailoRT and other tools:

```bash
sudo apt install hailo-all
```

### 3.3. Verify HailoRT Version

After installation, verify that you are running HailoRT 4.23:

```bash
hailortcli fw-control identify
```

The output should show `Firmware Version: 4.23.0`.

## Phase 4: Test Hailo Python API

Now that you have upgraded to HailoRT 4.23, the Python API should be fully functional. Let's test it.

### 4.1. Run Minimal Test

Run the minimal test script to verify that the Hailo Python API is working:

```bash
cd ~/projects/seewhozthere
python3 test_hailo_minimal.py
```

This should now pass without any errors.

### 4.2. Run Full Application

Finally, run the full SeeWhozThere application to confirm that everything is working as expected:

```bash
python3 test_hailo.py
```

You should now see the application running with full Hailo acceleration!

## References

1.  [Debian 13 “trixie” Release Notes](https://www.debian.org/releases/trixie/release-notes/)
2.  [Upgrading Debian 12 Bookworm to Debian 13 Trixie](https://community.openhab.org/t/upgrading-debian-12-bookworm-to-debian-13-trixie/165536)
3.  [How to upgrade from Debian 12 Bookworm to Debian 13 Trixie](https://fullmetalbrackets.com/blog/upgrade-debian-12-bookworm-debian-13-trixie/)
