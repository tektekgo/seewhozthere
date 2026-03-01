# SeeWhozThere Project Memory

This file contains critical information about the SeeWhozThere project to ensure continuity between sessions.

## 🔑 Key Details

- **Project Goal**: Build a world-class, privacy-first face recognition security dashboard for the home, using a Raspberry Pi and RTSP cameras.
- **Core Technologies**:
  - **Backend**: Python, FastAPI, OpenCV, SQLite
  - **Frontend**: React, TypeScript, Vite, Tailwind CSS, Recharts
  - **Deployment**: Systemd services, Docker (planned)
- **Key Repositories**:
  - **Main Repo**: `https://github.com/tektekgo/seewhozthere`
  - **UI Reference**: `https://github.com/tektekgo/pi-security-refresh`
- **Hardware**: Raspberry Pi 4/5, RTSP cameras, optional Hailo AI HAT+

## 📌 Current Status

- **React UI**: The full UI from pi-security-refresh has been integrated, but needs configuration fixes.
- **Backend**: API endpoints exist but need to be aligned with the frontend.
- **Services**: Systemd services are created but need to be made robust.
- **Documentation**: Needs to be created and organized.

## 🚀 Next Steps

1. **Fix React UI**: Correct `vite.config.ts` and `api.ts` to match the backend.
2. **Fix Backend**: Align API endpoints with frontend expectations.
3. **Fix Services**: Make systemd services robust and auto-starting.
4. **Create Documentation**: Write comprehensive docs for users and developers.
5. **Push to GitHub**: Commit all changes and deliver the final product.
