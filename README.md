# SeeWhozThere

SeeWhozThere is a self-hosted application that uses a Raspberry Pi and Google Coral to perform real-time facial recognition on RTSP camera streams. It provides a web-based dashboard to summarize daily visitors, all while keeping your data 100% local.

## Core Principles

*   **Privacy First:** All processing happens on-premise. Your video data never leaves your local network.
*   **No Subscriptions:** Built with open-source software. Your only cost is the one-time hardware purchase.
*   **Camera Agnostic:** Works with any IP camera that supports the standard RTSP protocol.

## Technology Stack

*   **Hardware:** Raspberry Pi 5 + Google Coral USB Accelerator
*   **Backend:** Python, FastAPI, OpenCV
*   **AI Models:** YOLOv5-Face (Detection), ArcFace/FaceNet (Recognition)
*   **Database:** LanceDB (Vector Database)
*   **Deployment:** Docker & Docker Compose

## Getting Started

*(This section will be filled out with installation instructions)*
