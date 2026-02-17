# 👁️ SeeWhozThere

**Professional AI-Powered Face Detection and Recognition System for Raspberry Pi 5**

SeeWhozThere is a commercial-grade home security system that uses the Raspberry Pi AI HAT+ (Hailo-8) to detect and recognize faces in real-time from RTSP camera feeds. It runs 24/7, stores snapshots, and provides a beautiful web dashboard for monitoring your property.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)

## ✨ Features

### 🎯 Core Functionality
- **Real-time Face Detection** - 25+ FPS using Hailo AI accelerator
- **Face Recognition** - Identify known people automatically
- **24/7 Continuous Monitoring** - Auto-start on boot with systemd
- **Multi-Camera Support** - Monitor multiple RTSP cameras simultaneously
- **Snapshot Storage** - Automatic capture and storage of detections
- **Web Dashboard** - Beautiful, responsive interface with dark mode

### 🔧 Management
- **User Management** - Add, edit, and delete known people via web UI
- **Photo Upload** - Train face recognition with uploaded photos
- **Image Management** - Delete unwanted snapshots
- **System Status** - Real-time monitoring of service health
- **Auto-Recovery** - Automatic restart on failure

### 🛡️ Privacy & Security
- **100% Local** - All processing happens on your Raspberry Pi
- **No Cloud** - Your data never leaves your network
- **Private** - No external API calls or data sharing
- **Secure** - Systemd service with security hardening

## 📋 Requirements

### Hardware
- **Raspberry Pi 5** (4GB or 8GB RAM recommended)
- **Raspberry Pi AI HAT+** (Hailo-8L or Hailo-8)
- **IP Camera** with RTSP support (e.g., Tapo C310, C320WS)
- **MicroSD Card** (32GB+ recommended)
- **Power Supply** (Official Raspberry Pi 27W recommended)

### Software
- **Debian Trixie** (or Bookworm with HailoRT 4.23.0+)
- **Python 3.11+**
- **HailoRT 4.23.0+**

### Network
- Local network with camera access
- Static IP recommended for Raspberry Pi

## 🚀 Quick Start

### 1. Clone the Repository

```bash
cd ~
git clone https://github.com/tektekgo/seewhozthere.git
cd seewhozthere
```

### 2. Install Dependencies

```bash
# Install Python packages
sudo pip3 install -r requirements.txt

# Verify Hailo device
hailortcli scan
```

### 3. Configure Cameras

```bash
# Copy example configuration
cp config.ini.example config.ini

# Edit with your camera details
nano config.ini
```

Example `config.ini`:
```ini
[cameras]
front_door = rtsp://username:password@192.168.1.100:554/stream1
backyard = rtsp://username:password@192.168.1.101:554/stream1

[system]
timezone = America/New_York
port = 7222
```

### 4. Install as Service (Recommended)

```bash
# One-command installation
./install_service.sh
```

This will:
- Install systemd services
- Enable auto-start on boot
- Start the system immediately

### 5. Access the Dashboard

Open your browser and navigate to:
```
http://YOUR_PI_IP:7222
```

Example: `http://192.168.1.140:7222`

## 📚 Documentation

- **[Service Management Guide](SERVICE_MANAGEMENT.md)** - Managing systemd services
- **[Hailo Setup Guide](HAILO_SETUP.md)** - Setting up the AI HAT+
- **[Hardware Options](HARDWARE_OPTIONS.md)** - Choosing the right hardware
- **[Migration Guide](MIGRATION_GUIDE.md)** - Upgrading from older versions

## 🎨 Using the System

### Adding Known People

1. Click **"Add Person"** in the dashboard
2. Enter the person's name
3. Upload a clear photo of their face
4. Click **"Add Person"**

The system will automatically:
- Generate a face encoding
- Save the photo as a thumbnail
- Start recognizing this person in future detections

### Managing People

1. Click **"Manage People"** in the navigation
2. View all known people
3. Delete people you no longer want to track

### Viewing Detections

The dashboard shows:
- **Today's Activity** - All detections from today
- **Known Visitors** - People the system recognized
- **Unknown Visitors** - Unidentified faces
- **Sighting Count** - How many times each person was seen
- **First/Last Seen** - Timestamps for each visitor

### Filtering

Use the filter buttons to show:
- **All** - Everyone detected today
- **Known** - Only recognized people
- **Unknown** - Only unidentified faces

## 🔧 Configuration

### Camera Configuration

Edit `config.ini` to add or modify cameras:

```ini
[cameras]
camera_name = rtsp://username:password@ip:port/stream_path
```

**Tips:**
- Use lowercase, descriptive names (e.g., `front_door`, `backyard`)
- Test RTSP URLs with VLC before adding to config
- Use substream (lower resolution) for better performance

### System Configuration

```ini
[system]
timezone = America/New_York  # Your timezone
port = 7222                   # Web dashboard port
```

### Detection Parameters

Edit `app/hailo_processor_v2.py` to adjust:

```python
self.detection_interval = 1.0  # Seconds between detections
self.confidence_threshold = 0.6  # Face detection confidence (0.0-1.0)
self.min_face_size = (50, 50)  # Minimum face size in pixels
```

### Recognition Threshold

Edit `app/face_recognition_engine.py`:

```python
self.recognition_threshold = 0.6  # Face matching threshold (0.0-1.0)
```

Lower = more strict matching (fewer false positives)
Higher = more lenient matching (more false positives)

## 🛠️ Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status seewhozthere

# View logs
sudo journalctl -u seewhozthere -n 50

# Test manually
cd ~/seewhozthere
python3 run_service.py
```

### Camera Connection Failed

1. Test RTSP URL in VLC Media Player
2. Check camera IP address and credentials
3. Verify network connectivity
4. Check firewall settings

### Hailo Device Not Found

```bash
# Check device
ls -l /dev/hailo0

# Verify HailoRT version
hailortcli fw-control identify

# Check permissions
sudo usermod -a -G video $USER
```

### High CPU Usage

This is normal - face detection is CPU-intensive. To reduce:

1. Increase `detection_interval` in `hailo_processor_v2.py`
2. Use camera substreams (lower resolution)
3. Reduce number of cameras

### Web Dashboard Not Accessible

```bash
# Check if service is running
sudo systemctl status seewhozthere-web

# Check port binding
sudo netstat -tulpn | grep 7222

# Test manually
cd ~/seewhozthere
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7222
```

## 📊 Performance

### Typical Performance (Raspberry Pi 5 + Hailo-8L)

- **Face Detection**: 25-30 FPS (limited by camera, not Hailo)
- **Processing Latency**: 30-50ms per frame
- **Face Recognition**: Real-time (< 100ms per face)
- **CPU Usage**: 40-60% (with 2 cameras)
- **Memory Usage**: 500-800 MB

### Optimization Tips

1. **Use Substreams** - Lower resolution = faster processing
2. **Adjust Detection Interval** - Process every 2-3 seconds instead of 1
3. **Limit Cameras** - Start with 1-2 cameras, add more as needed
4. **Use Wired Network** - More stable than WiFi
5. **Overclock Pi** - Increase performance (advanced users)

## 🔐 Security Best Practices

1. **Change Default Passwords** - Use strong camera passwords
2. **Use Static IPs** - Easier to manage and more secure
3. **Firewall Rules** - Limit access to dashboard port
4. **Regular Updates** - Keep system and packages updated
5. **Backup Database** - Regularly backup `data/seewhozthere.db`

## 📁 Project Structure

```
seewhozthere/
├── app/
│   ├── main.py                      # Web server and API
│   ├── hailo_processor_v2.py        # Face detection & recognition
│   ├── face_recognition_engine.py   # Face encoding & matching
│   ├── database.py                  # SQLite database interface
│   ├── config.py                    # Configuration loader
│   ├── templates/
│   │   └── index.html               # Web dashboard
│   └── static/                      # CSS, JS, images
├── data/
│   ├── snapshots/                   # Face detection snapshots
│   ├── thumbnails/                  # Person thumbnails
│   ├── encodings/                   # Face encodings
│   ├── seewhozthere.db             # SQLite database
│   └── *.log                        # Log files
├── models/
│   └── retinaface_mobilenet_v1.hef  # Hailo face detection model
├── run_service.py                   # Service runner (24/7 operation)
├── install_service.sh               # Service installation script
├── uninstall_service.sh             # Service removal script
├── config.ini                       # Configuration (not in git)
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Hailo** - For the amazing AI HAT+ accelerator
- **Raspberry Pi Foundation** - For the Raspberry Pi 5
- **OpenCV** - For computer vision tools
- **FastAPI** - For the web framework
- **Tailwind CSS** - For the beautiful UI

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/tektekgo/seewhozthere/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tektekgo/seewhozthere/discussions)
- **Documentation**: See `docs/` folder

## 🗺️ Roadmap

- [ ] Mobile app (iOS/Android)
- [ ] Telegram/Email notifications
- [ ] Motion detection integration
- [ ] Cloud backup (optional)
- [ ] Multi-user authentication
- [ ] Advanced analytics dashboard
- [ ] Integration with Home Assistant
- [ ] Docker support

## ⭐ Star History

If you find this project useful, please consider giving it a star on GitHub!

---

**Made with ❤️ for the Raspberry Pi and home automation community**
