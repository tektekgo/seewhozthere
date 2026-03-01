# Future Enhancements

This document captures planned improvements and architectural changes for future versions of SeeWhozThere.

---

## Docker Containerization

Containerizing SeeWhozThere would simplify deployment for new users, removing the need to manually install Python, Node.js, and system dependencies. A friend could get the system running with a single `docker compose up` command.

### Why It Is Deferred

The primary blocker is the **Hailo AI HAT+** hardware dependency. The Hailo PCIe driver (`hailo-dkms`) must be installed on the **host** operating system regardless of whether the application runs in a container. This means a new user still needs to perform the OS-level driver installation steps from the setup guide before Docker can help them. The value of containerization is therefore limited until a simpler driver installation path exists.

Additionally, the current two-service architecture (detection + web server as separate systemd units) maps cleanly onto a two-service Docker Compose setup, but migrating the existing Pi installation would require replacing the systemd services with Docker Compose — a non-trivial migration that risks disrupting a working setup.

### Planned Architecture

When containerization is implemented, the architecture will be as follows:

| Service | Image | Notes |
|---|---|---|
| `seewhozthere` | Custom Python image | Detection service, requires `/dev/hailo0` device passthrough |
| `seewhozthere-web` | Custom Python image | FastAPI web server |
| (optional) `nginx` | `nginx:alpine` | Reverse proxy for HTTPS / Tailscale access |

The `data/` directory (SQLite database and face snapshots) will be a named Docker volume, and `config.ini` will be bind-mounted from the host so users can edit it without rebuilding the image.

### Draft `docker-compose.yml`

```yaml
version: "3.9"

services:
  detection:
    build: .
    command: python3 run_service.py
    volumes:
      - ./config.ini:/app/config.ini:ro
      - swzt_data:/app/data
      - ./models:/app/models:ro
    devices:
      - /dev/hailo0:/dev/hailo0
    restart: unless-stopped

  web:
    build: .
    command: python3 -m uvicorn app.main:app --host 0.0.0.0 --port 7222
    volumes:
      - ./config.ini:/app/config.ini:ro
      - swzt_data:/app/data
    ports:
      - "7222:7222"
    depends_on:
      - detection
    restart: unless-stopped

volumes:
  swzt_data:
```

### Draft `Dockerfile`

```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy the pre-built frontend
COPY app/static/dashboard app/static/dashboard

EXPOSE 7222
```

### Prerequisites for a User Deploying via Docker

Even with Docker, a new user would still need to:

1.  Flash Raspberry Pi OS (64-bit, Bookworm).
2.  Enable the PCIe interface (`PCIE_PROBE=1`).
3.  Install the Hailo driver on the host: `sudo apt-get install hailo-dkms hailort`.
4.  Install Docker and Docker Compose.
5.  Clone the repository and create `config.ini`.
6.  Run `docker compose up -d`.

Steps 1–3 are identical to the non-Docker setup. Docker eliminates steps 4–9 of the current setup guide (Python, venv, pip, model download, service install).

### Migration Path for Existing Installations

For users who already have the system running via systemd (like the original developer), the migration path is:

1.  Stop and disable the systemd services:
    ```bash
    sudo systemctl stop seewhozthere seewhozthere-web
    sudo systemctl disable seewhozthere seewhozthere-web
    ```
2.  Install Docker and Docker Compose.
3.  Run `docker compose up -d` from the project directory.

The `data/` directory and `config.ini` remain in place — no data is lost.

---

## Other Planned Enhancements

- **Tailscale Integration**: Expose the dashboard securely over the internet without port forwarding, using Tailscale's free tier.
- **Multi-Camera Scaling**: Support for more than two simultaneous RTSP streams, with per-camera detection tuning.
- **Face Recognition Improvements**: Upgrade from `face_recognition` (dlib) to a Hailo-native face embedding model for fully on-device recognition.
- **Mobile Push Notifications**: Extend Telegram notifications to support Apple Push Notification Service (APNS) and Firebase Cloud Messaging (FCM) for native mobile alerts.
