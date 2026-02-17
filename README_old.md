# SeeWhozThere

SeeWhozThere is a self-hosted application that uses a Raspberry Pi and Google Coral to perform real-time facial recognition on RTSP camera streams. It provides a web-based dashboard to summarize daily visitors, all while keeping your data 100% local.

## Core Principles

*   **Privacy First:** All processing happens on-premise. Your video data never leaves your local network.
*   **No Subscriptions:** Built with open-source software. Your only cost is the one-time hardware purchase.
*   **Camera Agnostic:** Works with any IP camera that supports the standard RTSP protocol.
*   **Scalable:** Designed from the ground up to support multiple cameras, from a single camera to a 16-camera system.

---

## Planned Features

### 1. Multi-Camera Real-Time Processing
*   Connect to multiple RTSP-enabled IP cameras simultaneously.
*   Each camera stream is processed in a separate thread for efficient performance.
*   Uses a central "recognition queue" to offload AI inference to the Google Coral, preventing bottlenecks.

### 2. AI-Powered Face Recognition
*   **Detection:** A lightweight model runs on each camera stream to detect the presence of a face.
*   **Recognition:** A powerful recognition model runs on the Google Coral to generate a unique "facial embedding" (a mathematical representation) for each detected face.
*   **Database Matching:** Compares new embeddings against a local vector database (LanceDB) to identify known individuals or log new, unknown visitors.

### 3. Real-Time Web Dashboard
*   A web-based interface, accessible from any device on your local network.
*   Displays a live summary of unique visitors seen throughout the day.
*   Allows you to "name" or "tag" unknown visitors for future automatic identification.
*   Provides a detailed view with thumbnail images and timestamps for each sighting.

### 4. Scheduled Summary Notifications
*   An optional, configurable scheduler to send a summary of the day's activity.
*   Runs at a user-defined time (e.g., daily at 8:00 PM).
*   Supported notification services:
    *   Email
    *   Telegram

---

## Technology Stack

*   **Hardware:** Raspberry Pi 5 + Google Coral USB Accelerator
*   **Deployment:** Docker & Docker Compose
*   **Backend:** Python, FastAPI, OpenCV
*   **Database:** LanceDB (Vector Database)
*   **AI Models:**
    *   **Detection:** YOLOv5-Face or similar
    *   **Recognition:** ArcFace or FaceNet (on Edge TPU)
*   **Scheduling:** APScheduler

---

## Getting Started

*(This section will be filled out with installation and configuration instructions)*

