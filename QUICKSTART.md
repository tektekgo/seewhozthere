# 🚀 SeeWhozThere Quick Start Guide

Get up and running with SeeWhozThere in under 10 minutes!

## 📋 What You Need

- **Raspberry Pi 5** with AI HAT+ (Hailo-8)
- **IP Camera** with RTSP support
- **Internet connection** for installation

## 🎯 Choose Your Installation Method

### **Option 1: Docker (Recommended)** ⭐

**Best for:** Easy deployment, automatic updates, isolated environment

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 2. Clone repository
git clone https://github.com/tektekgo/seewhozthere.git
cd seewhozthere

# 3. Configure cameras
cp config.ini.example config.ini
nano config.ini  # Add your camera RTSP URLs

# 4. Start the system
docker-compose up -d

# 5. Access dashboard
# Open: http://YOUR_PI_IP:7222/dashboard
```

**Full guide:** [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

---

### **Option 2: Direct Installation**

**Best for:** Maximum performance, systemd integration

```bash
# 1. Clone repository
git clone https://github.com/tektekgo/seewhozthere.git
cd seewhozthere

# 2. Install dependencies
sudo pip3 install -r requirements.txt

# 3. Configure cameras
cp config.ini.example config.ini
nano config.ini  # Add your camera RTSP URLs

# 4. Build React dashboard
./build_frontend.sh

# 5. Install as service
./install_service.sh

# 6. Access dashboard
# Open: http://YOUR_PI_IP:7222/dashboard
```

**Full guide:** [README.md](README.md) and [SERVICE_MANAGEMENT.md](SERVICE_MANAGEMENT.md)

---

## 📸 Camera Configuration

Edit `config.ini`:

```ini
[cameras]
# Format: camera_name = rtsp://username:password@ip:port/stream_path
front_door = rtsp://admin:password123@192.168.1.100:554/stream1
backyard = rtsp://admin:password123@192.168.1.101:554/stream1

[system]
timezone = America/New_York
port = 7222
```

**Tips:**
- Test RTSP URLs in VLC Media Player first
- Use lowercase names (e.g., `front_door`, not `Front Door`)
- Use substream for better performance

---

## 🎨 Using the Dashboard

### **1. View the Dashboard**

Open `http://YOUR_PI_IP:7222/dashboard` in your browser.

You'll see:
- **Stats Cards** - Total visitors, today's activity, active cameras, unknown visitors
- **Charts** - Hourly activity, known vs unknown, weekly trends, camera activity
- **Heatmap** - Peak hours visualization
- **Visitor Grid** - All visitors seen today

### **2. Add Known People**

1. Click **"Add Person"** button
2. Enter the person's name
3. Upload a clear photo of their face
4. Click **"Add Person"**

The system will now recognize this person automatically!

### **3. Manage People**

1. Click **"Manage People"** in the navigation
2. View all known people
3. Delete people you no longer want to track

---

## ✅ Testing Your Installation

Follow the [TESTING_GUIDE.md](TESTING_GUIDE.md) to verify everything works.

**Quick test:**
1. Walk in front of the camera
2. Check the dashboard - you should see an "Unknown" visitor card within 20 seconds
3. Add yourself as a known person
4. Walk in front of the camera again
5. You should now appear as a known visitor!

---

## 🔧 Common Issues

### **Dashboard won't load**
```bash
# Check if service is running
docker-compose ps  # For Docker
sudo systemctl status seewhozthere-web  # For direct install

# Check logs
docker-compose logs -f  # For Docker
sudo journalctl -u seewhozthere-web -f  # For direct install
```

### **No detections**
```bash
# Test camera URL in VLC
vlc rtsp://username:password@camera_ip:554/stream1

# Check Hailo device
ls -l /dev/hailo0

# View logs
docker-compose logs -f  # For Docker
tail -f data/service.log  # For direct install
```

### **High CPU usage**
This is normal! Face detection is CPU-intensive. To reduce:
- Use camera substreams (lower resolution)
- Increase `detection_interval` in `app/hailo_processor_v2.py`

---

## 📚 Full Documentation

- **[README.md](README.md)** - Complete feature list and configuration
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Docker deployment guide
- **[SERVICE_MANAGEMENT.md](SERVICE_MANAGEMENT.md)** - Systemd service management
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing checklist

---

## 🆘 Getting Help

- **GitHub Issues:** https://github.com/tektekgo/seewhozthere/issues
- **Discussions:** https://github.com/tektekgo/seewhozthere/discussions

---

**Happy Monitoring! 👁️**
