# 🐳 Docker Deployment Guide

This guide explains how to deploy SeeWhozThere using Docker for easy installation and management.

## 📋 Prerequisites

### Required
- **Docker** 20.10+ installed
- **Docker Compose** 2.0+ installed
- **Raspberry Pi AI HAT+** (Hailo-8) connected
- **IP Camera** with RTSP support

### Optional
- **Portainer** for web-based Docker management

## 🚀 Quick Start

### 1. Install Docker (if not already installed)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install -y docker-compose

# Verify installation
docker --version
docker-compose --version
```

**Important:** Log out and log back in for group changes to take effect.

### 2. Clone the Repository

```bash
cd ~
git clone https://github.com/tektekgo/seewhozthere.git
cd seewhozthere
```

### 3. Configure Cameras

```bash
# Copy example config
cp config.ini.example config.ini

# Edit with your camera details
nano config.ini
```

Add your camera(s):
```ini
[cameras]
front_camera = rtsp://username:password@192.168.9.130:554/stream1

[system]
timezone = America/New_York
port = 7222
```

### 4. Build and Start

```bash
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

### 5. Access the Dashboard

Open your browser:
```
http://YOUR_PI_IP:7222/dashboard
```

Example: `http://192.168.9.140:7222/dashboard`

## 🔧 Docker Commands

### Container Management

```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# Restart containers
docker-compose restart

# View logs
docker-compose logs -f

# View logs for last 100 lines
docker-compose logs --tail=100

# Check container status
docker-compose ps
```

### Building

```bash
# Build without cache (force rebuild)
docker-compose build --no-cache

# Pull latest code and rebuild
git pull
docker-compose build
docker-compose up -d
```

### Data Management

```bash
# Backup data directory
tar -czf seewhozthere-backup-$(date +%Y%m%d).tar.gz data/

# Restore data directory
tar -xzf seewhozthere-backup-YYYYMMDD.tar.gz
```

## 📊 Monitoring

### View System Resources

```bash
# Container resource usage
docker stats seewhozthere

# Container details
docker inspect seewhozthere

# Health check status
docker inspect --format='{{.State.Health.Status}}' seewhozthere
```

### Logs

```bash
# Real-time logs
docker-compose logs -f

# Logs since specific time
docker-compose logs --since 30m

# Save logs to file
docker-compose logs > seewhozthere.log
```

## 🔄 Updates

### Update to Latest Version

```bash
# Pull latest code
cd ~/seewhozthere
git pull

# Rebuild and restart
docker-compose down
docker-compose build
docker-compose up -d
```

### Update Only Code (No Rebuild)

If you only changed Python code:

```bash
# Stop container
docker-compose down

# Pull changes
git pull

# Start container
docker-compose up -d
```

## 🐛 Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Check if port is in use
sudo netstat -tulpn | grep 7222

# Check Hailo device
ls -l /dev/hailo0

# Verify config file
cat config.ini
```

### Hailo Device Not Found

```bash
# Check if device is accessible
ls -l /dev/hailo0

# Verify device is mounted in container
docker exec seewhozthere ls -l /dev/hailo0

# Check device permissions
sudo chmod 666 /dev/hailo0
```

### Camera Connection Failed

```bash
# Test RTSP URL with VLC
vlc rtsp://username:password@camera_ip:554/stream1

# Check from inside container
docker exec seewhozthere python3 -c "import cv2; cap = cv2.VideoCapture('YOUR_RTSP_URL'); print(cap.isOpened())"
```

### High Memory Usage

```bash
# Check memory usage
docker stats seewhozthere

# Limit memory (edit docker-compose.yml)
# Add under 'seewhozthere' service:
#   mem_limit: 2g
#   mem_reservation: 1g
```

### Dashboard Not Loading

```bash
# Check if React build exists
docker exec seewhozthere ls -la /app/app/static/dashboard

# Rebuild frontend
docker-compose build --no-cache
docker-compose up -d
```

## 🔐 Security

### Best Practices

1. **Use Strong Passwords** - For cameras and any web interfaces
2. **Firewall Rules** - Limit access to port 7222
3. **Regular Updates** - Keep Docker and SeeWhozThere updated
4. **Backup Data** - Regular backups of the `data/` directory

### Firewall Configuration

```bash
# Allow only from local network
sudo ufw allow from 192.168.9.0/24 to any port 7222

# Or allow from specific IP
sudo ufw allow from 192.168.9.100 to any port 7222
```

## 📁 Volume Mounts

The Docker container mounts these directories:

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| `./data` | `/app/data` | Database, snapshots, encodings |
| `./config.ini` | `/app/config.ini` | Configuration (read-only) |

## 🌐 Environment Variables

You can customize the container with environment variables in `docker-compose.yml`:

```yaml
environment:
  - TZ=America/New_York          # Timezone
  - PYTHONUNBUFFERED=1           # Python output buffering
  - LOG_LEVEL=INFO               # Logging level
```

## 🔧 Advanced Configuration

### Custom Port

Edit `docker-compose.yml`:

```yaml
ports:
  - "8080:7222"  # Host port 8080 -> Container port 7222
```

### Multiple Instances

To run multiple instances (e.g., different locations):

```bash
# Copy the directory
cp -r seewhozthere seewhozthere-location2

# Edit docker-compose.yml in new directory
# Change container name and port

# Start both
cd ~/seewhozthere
docker-compose up -d

cd ~/seewhozthere-location2
docker-compose up -d
```

### Resource Limits

Edit `docker-compose.yml`:

```yaml
services:
  seewhozthere:
    # ... existing config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 📦 Portainer (Optional)

For easier Docker management with a web UI:

```bash
# Install Portainer
docker volume create portainer_data
docker run -d -p 9000:9000 --name=portainer --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce

# Access Portainer
# http://YOUR_PI_IP:9000
```

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `docker-compose logs -f`
2. Verify config: `cat config.ini`
3. Check GitHub Issues: https://github.com/tektekgo/seewhozthere/issues
4. Review this guide's troubleshooting section

## 📝 Notes

- **First Run**: Initial startup may take 1-2 minutes while models load
- **Updates**: Always backup `data/` before updating
- **Performance**: Docker adds minimal overhead (~5%) on Raspberry Pi
- **Hailo**: Requires `/dev/hailo0` device access

---

**Happy Monitoring! 👁️**
