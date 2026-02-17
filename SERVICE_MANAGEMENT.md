# SeeWhozThere Service Management Guide

This guide explains how to install, manage, and troubleshoot the SeeWhozThere systemd services.

## 📦 Installation

### Quick Install (Recommended)

Run the installation script to set up automatic startup:

```bash
cd ~/seewhozthere
./install_service.sh
```

This will:
- Install two systemd services (face detection + web dashboard)
- Enable automatic startup on boot
- Start the services immediately
- Create necessary data directories

### Manual Installation

If you prefer to install manually:

```bash
# Update service files with your username and path
sudo cp seewhozthere.service /etc/systemd/system/
sudo cp seewhozthere-web.service /etc/systemd/system/

# Edit the files to set correct User, Group, and WorkingDirectory
sudo nano /etc/systemd/system/seewhozthere.service
sudo nano /etc/systemd/system/seewhozthere-web.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable seewhozthere.service
sudo systemctl enable seewhozthere-web.service
sudo systemctl start seewhozthere.service
sudo systemctl start seewhozthere-web.service
```

## 🔧 Service Management Commands

### Check Status

```bash
# Check if services are running
sudo systemctl status seewhozthere
sudo systemctl status seewhozthere-web

# Quick status check
sudo systemctl is-active seewhozthere
sudo systemctl is-active seewhozthere-web
```

### Start/Stop/Restart

```bash
# Start services
sudo systemctl start seewhozthere
sudo systemctl start seewhozthere-web

# Stop services
sudo systemctl stop seewhozthere
sudo systemctl stop seewhozthere-web

# Restart services (after configuration changes)
sudo systemctl restart seewhozthere
sudo systemctl restart seewhozthere-web
```

### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot
sudo systemctl enable seewhozthere
sudo systemctl enable seewhozthere-web

# Disable auto-start
sudo systemctl disable seewhozthere
sudo systemctl disable seewhozthere-web
```

## 📋 Viewing Logs

### Real-time Logs (systemd journal)

```bash
# Follow live logs for face detection
sudo journalctl -u seewhozthere -f

# Follow live logs for web dashboard
sudo journalctl -u seewhozthere-web -f

# View last 100 lines
sudo journalctl -u seewhozthere -n 100
```

### Application Logs

```bash
# Face detection logs
tail -f ~/seewhozthere/data/service.log

# Web dashboard logs
tail -f ~/seewhozthere/data/web.log

# SeeWhozThere application logs
tail -f ~/seewhozthere/data/seewhozthere.log
```

## 🔍 Troubleshooting

### Service Won't Start

1. **Check service status:**
   ```bash
   sudo systemctl status seewhozthere
   ```

2. **View error logs:**
   ```bash
   sudo journalctl -u seewhozthere -n 50
   ```

3. **Common issues:**
   - **Hailo device not found:** Make sure the AI HAT+ is properly connected
   - **Camera connection failed:** Check RTSP URL in `config.ini`
   - **Permission denied:** Ensure the service user has access to `/dev/hailo0`

### Service Keeps Restarting

1. **Check logs for errors:**
   ```bash
   sudo journalctl -u seewhozthere -f
   ```

2. **Test manually:**
   ```bash
   # Stop the service
   sudo systemctl stop seewhozthere
   
   # Run manually to see errors
   cd ~/seewhozthere
   python3 run_service.py
   ```

### Web Dashboard Not Accessible

1. **Check if service is running:**
   ```bash
   sudo systemctl status seewhozthere-web
   ```

2. **Check port binding:**
   ```bash
   sudo netstat -tulpn | grep 7222
   ```

3. **Test manually:**
   ```bash
   sudo systemctl stop seewhozthere-web
   cd ~/seewhozthere
   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7222
   ```

### High CPU Usage

The face detection service is CPU/AI-intensive. This is normal behavior. To reduce load:

1. **Increase detection interval** in `app/hailo_processor_v2.py`:
   ```python
   self.detection_interval = 2.0  # Process every 2 seconds instead of 1
   ```

2. **Restart service:**
   ```bash
   sudo systemctl restart seewhozthere
   ```

## 🗑️ Uninstallation

To remove the services (keeps your data):

```bash
cd ~/seewhozthere
./uninstall_service.sh
```

Or manually:

```bash
sudo systemctl stop seewhozthere seewhozthere-web
sudo systemctl disable seewhozthere seewhozthere-web
sudo rm /etc/systemd/system/seewhozthere.service
sudo rm /etc/systemd/system/seewhozthere-web.service
sudo systemctl daemon-reload
```

## 📊 Performance Monitoring

### Check Resource Usage

```bash
# CPU and memory usage
top -p $(pgrep -f "run_service.py")

# Detailed stats
systemd-cgtop
```

### Service Uptime

```bash
systemctl status seewhozthere | grep Active
```

## 🔄 After Updates

After updating the code from git:

```bash
cd ~/seewhozthere
git pull
sudo systemctl restart seewhozthere
sudo systemctl restart seewhozthere-web
```

## 🆘 Getting Help

If you encounter issues:

1. Check the logs (see "Viewing Logs" section)
2. Try running manually to see detailed errors
3. Check GitHub Issues: https://github.com/tektekgo/seewhozthere/issues
4. Review the main README.md for configuration help

## 📝 Service Configuration

The service files are located at:
- `/etc/systemd/system/seewhozthere.service`
- `/etc/systemd/system/seewhozthere-web.service`

After editing service files, always run:
```bash
sudo systemctl daemon-reload
sudo systemctl restart seewhozthere
```

## 🎯 Best Practices

1. **Always check logs** after starting services
2. **Test configuration changes** manually before restarting services
3. **Monitor resource usage** to ensure stable operation
4. **Keep backups** of your `config.ini` and database
5. **Update regularly** with `git pull` for bug fixes and improvements
