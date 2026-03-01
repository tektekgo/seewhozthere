> [!NOTE]
> This file is maintained by Manus, your AI partner. Last updated: Mar 01, 2026.

# SeeWhozThere Project Memory

This file contains critical information about the SeeWhozThere project to ensure continuity between sessions. It reflects the final state of the application after significant UI/UX enhancements, code cleanup, and feature additions.

## 🔑 Key Details

- **Project Goal**: Build a world-class, privacy-first face recognition security dashboard for the home, using a Raspberry Pi 5, Hailo AI HAT+, and RTSP cameras. The final product is a polished, commercial-grade application.
- **Core Technologies**:
  - **Backend**: Python, FastAPI, SQLite, Hailo SDK
  - **Frontend**: React, TypeScript, Vite, Tailwind CSS, Shadcn/UI, Recharts
  - **Deployment**: Systemd services (`seewhozthere.service` for detection, `seewhozthere-web.service` for the UI).
- **GitHub Repo**: `https://github.com/tektekgo/seewhozthere`
- **Hardware**: Raspberry Pi 5, Hailo AI HAT+, RTSP cameras (e.g., Tapo).

## 📌 Final Status

- **React UI**: The UI is complete, featuring a professional dashboard, history page, and a comprehensive multi-tab settings page. The build process is stable.
- **Backend**: The FastAPI backend is robust, providing a full suite of analytics endpoints, camera configuration APIs, and systemd service control APIs.
- **Services**: The application is split into two systemd services for robustness:
  1.  `seewhozthere-web.service`: Runs the FastAPI web server and serves the React dashboard.
  2.  `seewhozthere.service`: Runs the core `run_service.py` face detection processor, utilizing the Hailo AI accelerator.
- **Codebase**: All legacy UI files and unused Python modules have been removed. The code is clean and organized.
- **Critical Dependency**: The Hailo/numpy/OpenCV dependency issue is resolved and documented. The required versions (`numpy<2`, `opencv-python-headless==4.8.1.78`) are pinned in `requirements.txt`.

## ✨ Key Features Implemented

- **Advanced Settings UI**: A new multi-tab settings page allows users to:
    - **Manage Cameras**: Add, edit, and delete camera RTSP streams directly from the UI.
    - **Control Detection Service**: Start, stop, and restart the `seewhozthere.service` via API calls from the dashboard, providing an excellent user experience.
    - **View System Info**: An "About" tab displays project details, stack, and critical dependency information.
- **Live Status Indicators**: The UI shows the live status of the detection service (Online/Offline) and the AI Engine in use (Hailo/OpenCV).
- **Branding**: The footer now includes "Created by Sujit G · © Techsilon" and a build version placeholder.

## 🚀 Next Steps (Task Complete)

1.  **Documentation**: Update all project documentation to reflect the new features and architecture. (Completed)
2.  **Final Push**: Commit all changes to the GitHub repository. (Next Action)
3.  **Deliver to User**: Provide a final summary and instructions. (Final Action)
