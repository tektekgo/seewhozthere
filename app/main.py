"""
SeeWhozThere Web Server v2

Enhanced version with user management, face recognition training, and API endpoints.
"""

import uvicorn
import os
import io
import hmac
import hashlib
import secrets
import time
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException, Body, Response
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import cv2

# Import our configuration settings
from app.config import TIMEZONE, PORT, SECURITY_PASSPHRASE, SECURITY_SESSION_HOURS, SECURITY_LOGIN_ENABLED
from app.database import get_db
from app.face_recognition_engine import get_face_recognition_engine
from app.hailo_processor_v2 import get_processor
from app.analytics import get_analytics


# --- Application Setup ---

app = FastAPI(title="SeeWhozThere v2")

# --- Auth / Session Helpers ---

# A random secret key generated at startup (changes on restart — sessions expire on restart)
_SESSION_SECRET = secrets.token_hex(32)
SESSION_COOKIE = "swzt_session"


def _make_token() -> str:
    """Create a signed session token: timestamp|hmac_signature"""
    ts = str(int(time.time()))
    sig = hmac.new(_SESSION_SECRET.encode(), ts.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def _verify_token(token: str) -> bool:
    """Verify a session token is valid and not expired."""
    if not SECURITY_LOGIN_ENABLED:
        return True  # login disabled — always authenticated
    try:
        ts_str, sig = token.rsplit(".", 1)
        # Check signature
        expected = hmac.new(_SESSION_SECRET.encode(), ts_str.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        # Check expiry
        age_hours = (time.time() - int(ts_str)) / 3600
        return age_hours < SECURITY_SESSION_HOURS
    except Exception:
        return False


def _is_authenticated(request: Request) -> bool:
    """Return True if the request carries a valid session cookie."""
    if not SECURITY_LOGIN_ENABLED:
        return True
    token = request.cookies.get(SESSION_COOKIE, "")
    return _verify_token(token)


class AuthMiddleware(BaseHTTPMiddleware):
    """Redirect unauthenticated requests for dashboard pages to /login.
    API calls return 401 JSON instead of a redirect."""

    # Paths that are always public (no auth required)
    PUBLIC_PATHS = {"/login", "/login/", "/dashboard/login", "/dashboard/login/",
                    "/api/login", "/api/logout", "/api/auth-status"}
    # Prefixes that are always public (static assets needed by the login page)
    PUBLIC_PREFIXES = ("/dashboard/assets/", "/dashboard/favicon", "/dashboard/logo",
                       "/static/", "/data/")

    async def dispatch(self, request: Request, call_next):
        if not SECURITY_LOGIN_ENABLED:
            return await call_next(request)

        path = request.url.path

        # Always allow public paths
        if path in self.PUBLIC_PATHS or any(path.startswith(p) for p in self.PUBLIC_PREFIXES):
            return await call_next(request)

        # Check auth
        if _is_authenticated(request):
            return await call_next(request)

        # Unauthenticated — API gets 401, pages get redirect to /dashboard/login
        if path.startswith("/api/"):
            return JSONResponse({"error": "Not authenticated"}, status_code=401)
        return RedirectResponse(url="/dashboard/login", status_code=302)


app.add_middleware(AuthMiddleware)

# Define the absolute path to the 'app' directory
APP_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = APP_DIR.parent

# Mount static directories
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.mount("/data", StaticFiles(directory=PROJECT_ROOT / "data"), name="data")

# Mount React dashboard (if built)
dashboard_dir = APP_DIR / "static" / "dashboard"
if dashboard_dir.exists():
    app.mount("/dashboard/assets", StaticFiles(directory=dashboard_dir / "assets"), name="dashboard_assets")
    # Serve root-level dashboard files (favicon.ico, logo PNGs, robots.txt etc.)
    # These are referenced as /dashboard/favicon.ico etc. in the built index.html
    from starlette.responses import FileResponse as _FileResponse
    from pathlib import Path as _Path
    _dashboard_root_files = ["favicon.ico", "favicon.png", "logo.png", "logo-16.png", "logo-32.png", "logo-192.png", "robots.txt", "placeholder.svg"]
    for _fname in _dashboard_root_files:
        _fpath = dashboard_dir / _fname
        if _fpath.exists():
            # Create a closure to capture the correct path
            def _make_handler(p):
                async def _handler():
                    return _FileResponse(str(p))
                return _handler
            app.add_api_route(f"/dashboard/{_fname}", _make_handler(_fpath), methods=["GET"], include_in_schema=False)



# --- Data Functions ---

def get_daily_summary():
    """Gets today's visitor summary from the database."""
    db = get_db()
    summary = db.get_today_summary()
    stats = db.get_statistics()
    
    # Get processor status
    try:
        processor = get_processor()
        processor_status = processor.get_status()
    except:
        processor_status = {'running': False, 'active_cameras': 0}
    
    # Transform database format to template format
    visitors = []
    unknown_count = 0
    
    for visitor in summary:
        # Format timestamps
        first_seen_time = visitor['first_seen'].strftime('%H:%M:%S') if visitor['first_seen'] else 'N/A'
        last_seen_time = visitor['last_seen'].strftime('%H:%M:%S') if visitor['last_seen'] else 'N/A'
        
        # Determine thumbnail URL - fix the path
        thumbnail_url = None
        if visitor.get('thumbnail_path'):
            thumbnail_url = visitor['thumbnail_path']
        elif visitor.get('latest_snapshot'):
            # Convert absolute path to URL path
            snapshot_path = visitor['latest_snapshot']
            if snapshot_path.startswith('data/'):
                thumbnail_url = '/' + snapshot_path
            else:
                thumbnail_url = '/data/snapshots/' + os.path.basename(snapshot_path)
        else:
            thumbnail_url = '/static/mock_faces/unknown_1.jpg'
        
        is_known = visitor['visitor_id'] != 0
        if not is_known:
            unknown_count += 1
        
        visitors.append({
            "id": visitor['visitor_id'] if is_known else 0,
            "name": visitor['name'],
            "is_known": is_known,
            "first_seen": first_seen_time,
            "last_seen": last_seen_time,
            "sighting_count": visitor['sighting_count'],
            "thumbnail_url": thumbnail_url
        })
    
    return {
        "summary_date": datetime.today().isoformat(),
        "timezone": TIMEZONE,
        "visitors": visitors,
        "total_visitors": stats['total_visitors'],
        "unknown_count": unknown_count,
        "active_cameras": processor_status.get('active_cameras', 0),
        "system_running": processor_status.get('running', False)
    }


# --- Dashboard Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    """Redirect root to the React dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard/")


# --- API Endpoints for User Management ---


@app.get("/dashboard")
@app.get("/dashboard/")
@app.get("/dashboard/{path:path}")
async def serve_dashboard(path: str = ""):
    """Serve the React dashboard SPA."""
    dashboard_index = APP_DIR / "static" / "dashboard" / "index.html"
    if dashboard_index.exists():
        return FileResponse(str(dashboard_index))
    return HTMLResponse("<h1>Dashboard not built yet. Run ./build_frontend.sh</h1>")

@app.get("/api/visitors")
async def get_all_visitors():
    """Get all known visitors."""
    db = get_db()
    visitors = db.get_all_visitors()
    
    # Format for API response
    result = []
    for visitor in visitors:
        result.append({
            "id": visitor['id'],
            "name": visitor['name'],
            "thumbnail_path": visitor.get('thumbnail_path'),
            "created_at": visitor['created_at'].isoformat() if visitor.get('created_at') else None,
            "has_encoding": visitor.get('face_encoding') is not None
        })
    
    return {"visitors": result}


@app.get("/api/visitors/{visitor_id}")
async def get_visitor(visitor_id: int):
    """Get a specific visitor by ID."""
    db = get_db()
    visitor = db.get_visitor(visitor_id)
    
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    return {
        "id": visitor['id'],
        "name": visitor['name'],
        "thumbnail_path": visitor.get('thumbnail_path'),
        "created_at": visitor['created_at'].isoformat() if visitor.get('created_at') else None,
        "has_encoding": visitor.get('face_encoding') is not None
    }


@app.post("/api/visitors")
async def add_visitor(
    name: str = Form(...),
    photo: Optional[UploadFile] = File(None)
):
    """
    Add a new visitor with optional photo for face recognition training.
    """
    db = get_db()
    face_recognition = get_face_recognition_engine()
    
    # Validate name
    if not name or len(name.strip()) == 0:
        raise HTTPException(status_code=400, detail="Name is required")
    
    name = name.strip()
    
    # Check if visitor already exists
    existing = db.get_visitor_by_name(name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Visitor '{name}' already exists")
    
    thumbnail_path = None
    face_encoding_blob = None
    
    # Process photo if provided
    if photo and photo.filename:
        try:
            # Read image file
            contents = await photo.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise HTTPException(status_code=400, detail="Invalid image file")
            
            # Save thumbnail
            thumbnails_dir = PROJECT_ROOT / "data" / "thumbnails"
            thumbnails_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            thumbnail_filename = f"{safe_name}_{timestamp}.jpg"
            thumbnail_path = thumbnails_dir / thumbnail_filename
            
            # Resize and save thumbnail
            thumbnail = cv2.resize(img, (200, 200))
            cv2.imwrite(str(thumbnail_path), thumbnail)
            
            # Convert to relative path for database
            thumbnail_path_str = f"data/thumbnails/{thumbnail_filename}"
            
            # Generate face encoding
            encoding = face_recognition.encode_face(img)
            face_encoding_blob = encoding.tobytes()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing photo: {str(e)}")
    
    # Add visitor to database
    try:
        visitor_id = db.add_visitor(
            name=name,
            face_encoding=face_encoding_blob,
            thumbnail_path=thumbnail_path_str if thumbnail_path else None
        )
        
        # Reload known faces in the processor
        try:
            processor = get_processor()
            processor.reload_known_faces()
        except:
            pass  # Processor might not be running
        
        return {
            "success": True,
            "visitor_id": visitor_id,
            "name": name,
            "has_encoding": face_encoding_blob is not None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding visitor: {str(e)}")


@app.put("/api/visitors/{visitor_id}")
async def update_visitor(
    visitor_id: int,
    name: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None)
):
    """Update a visitor's information and/or photo."""
    db = get_db()
    face_recognition = get_face_recognition_engine()
    
    # Check if visitor exists
    visitor = db.get_visitor(visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    update_data = {}
    
    # Update name if provided
    if name and len(name.strip()) > 0:
        update_data['name'] = name.strip()
    
    # Process new photo if provided
    if photo and photo.filename:
        try:
            # Read image file
            contents = await photo.read()
            nparr = np.frombuffer(contents, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise HTTPException(status_code=400, detail="Invalid image file")
            
            # Save new thumbnail
            thumbnails_dir = PROJECT_ROOT / "data" / "thumbnails"
            thumbnails_dir.mkdir(parents=True, exist_ok=True)
            
            visitor_name = update_data.get('name', visitor['name'])
            safe_name = "".join(c for c in visitor_name if c.isalnum() or c in (' ', '-', '_')).strip()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            thumbnail_filename = f"{safe_name}_{timestamp}.jpg"
            thumbnail_path = thumbnails_dir / thumbnail_filename
            
            # Resize and save thumbnail
            thumbnail = cv2.resize(img, (200, 200))
            cv2.imwrite(str(thumbnail_path), thumbnail)
            
            update_data['thumbnail_path'] = f"data/thumbnails/{thumbnail_filename}"
            
            # Generate new face encoding
            encoding = face_recognition.encode_face(img)
            update_data['face_encoding'] = encoding.tobytes()
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing photo: {str(e)}")
    
    # Update in database
    if update_data:
        success = db.update_visitor(visitor_id, **update_data)
        
        if success:
            # Reload known faces in the processor
            try:
                processor = get_processor()
                processor.reload_known_faces()
            except:
                pass
            
            return {"success": True, "visitor_id": visitor_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to update visitor")
    else:
        return {"success": True, "visitor_id": visitor_id, "message": "No changes made"}


@app.delete("/api/visitors/{visitor_id}")
async def delete_visitor(visitor_id: int):
    """Delete a visitor and all their sightings."""
    db = get_db()
    
    # Check if visitor exists
    visitor = db.get_visitor(visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    # Delete from database
    success = db.delete_visitor(visitor_id)
    
    if success:
        # Reload known faces in the processor
        try:
            processor = get_processor()
            processor.reload_known_faces()
        except:
            pass
        
        return {"success": True, "message": f"Deleted visitor '{visitor['name']}'"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete visitor")


@app.post("/api/sightings/{sighting_id}/identify")
async def identify_sighting(sighting_id: int, visitor_id: int = Form(...)):
    """Associate an unknown sighting with a known visitor."""
    db = get_db()
    
    # Verify visitor exists
    visitor = db.get_visitor(visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    
    # Update sighting
    success = db.identify_sighting(sighting_id, visitor_id)
    
    if success:
        return {"success": True, "message": f"Identified as {visitor['name']}"}
    else:
        raise HTTPException(status_code=404, detail="Sighting not found")


@app.get("/api/unknown-sightings")
async def get_unknown_sightings(limit: int = 50):
    """Get recent unknown sightings."""
    db = get_db()
    sightings = db.get_unknown_sightings(limit=limit)
    
    result = []
    for sighting in sightings:
        # Fix snapshot path
        snapshot_path = sighting.get('snapshot_path', '')
        if snapshot_path and snapshot_path.startswith('data/'):
            snapshot_url = '/' + snapshot_path
        else:
            snapshot_url = '/data/snapshots/' + os.path.basename(snapshot_path) if snapshot_path else None
        
        result.append({
            "id": sighting['id'],
            "camera_name": sighting['camera_name'],
            "timestamp": sighting['timestamp'].isoformat() if sighting.get('timestamp') else None,
            "snapshot_url": snapshot_url
        })
    
    return {"sightings": result}


@app.get("/api/sightings")
async def get_all_sightings(limit: int = 100):
    """Get all sightings (known and unknown) with visitor names."""
    db = get_db()
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.camera_name, s.timestamp, s.snapshot_path,
               s.visitor_id, v.name as visitor_name
        FROM sightings s
        LEFT JOIN visitors v ON s.visitor_id = v.id
        ORDER BY s.timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        snapshot_path = row['snapshot_path'] or ''
        if snapshot_path and snapshot_path.startswith('data/'):
            snapshot_url = '/' + snapshot_path
        elif snapshot_path:
            snapshot_url = '/data/snapshots/' + os.path.basename(snapshot_path)
        else:
            snapshot_url = None

        ts = row['timestamp']
        if ts and hasattr(ts, 'isoformat'):
            ts_str = ts.isoformat()
        elif ts:
            ts_str = str(ts)
        else:
            ts_str = None

        result.append({
            "id": row['id'],
            "camera_name": row['camera_name'],
            "timestamp": ts_str,
            "snapshot_url": snapshot_url,
            "visitor_id": row['visitor_id'],
            "visitor_name": row['visitor_name'],
        })

    return {"sightings": result}


@app.delete("/api/sightings/{sighting_id}")
async def delete_sighting(sighting_id: int):
    """Delete a sighting and its snapshot."""
    db = get_db()
    
    # Get sighting to find snapshot path
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT snapshot_path FROM sightings WHERE id = ?", (sighting_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Sighting not found")
    
    snapshot_path = row['snapshot_path']
    
    # Delete from database
    cursor.execute("DELETE FROM sightings WHERE id = ?", (sighting_id,))
    conn.commit()
    conn.close()
    
    # Delete snapshot file if it exists
    if snapshot_path:
        full_path = PROJECT_ROOT / snapshot_path
        if full_path.exists():
            try:
                full_path.unlink()
            except Exception as e:
                print(f"Error deleting snapshot: {e}")
    
    return {"success": True, "message": "Sighting deleted"}


@app.delete("/api/sightings")
async def bulk_delete_sightings(ids: list[int] = Body(..., embed=True)):
    """Delete multiple sightings and their snapshot files."""
    if not ids:
        return {"success": True, "deleted": 0}

    db = get_db()
    conn = db._get_connection()
    cursor = conn.cursor()

    # Fetch snapshot paths for all requested IDs
    placeholders = ",".join("?" for _ in ids)
    cursor.execute(f"SELECT id, snapshot_path FROM sightings WHERE id IN ({placeholders})", ids)
    rows = cursor.fetchall()

    found_ids = [row['id'] for row in rows]
    snapshot_paths = [row['snapshot_path'] for row in rows if row['snapshot_path']]

    # Delete from database
    cursor.execute(f"DELETE FROM sightings WHERE id IN ({placeholders})", found_ids)
    conn.commit()
    conn.close()

    # Delete snapshot files
    for snapshot_path in snapshot_paths:
        if snapshot_path.startswith('data/'):
            full_path = PROJECT_ROOT / snapshot_path
        else:
            full_path = PROJECT_ROOT / 'data' / 'snapshots' / os.path.basename(snapshot_path)
        if full_path.exists():
            try:
                full_path.unlink()
            except Exception as e:
                print(f"Error deleting snapshot {snapshot_path}: {e}")

    return {"success": True, "deleted": len(found_ids)}


@app.get("/api/status")
async def get_system_status():
    """Get current system status.
    
    The web server and the detection service are separate OS processes.
    We determine status by:
    - detection_running: systemd service 'seewhozthere' is active (cross-process check)
    - hailo_available: check for Hailo device file (cross-process, hardware-level)
    - active_cameras: count cameras configured in config.ini (not in-memory state)
    - known_people: from the shared SQLite database
    """
    import subprocess
    from app.config import get_cameras
    
    # 1. Check if detection service (seewhozthere systemd unit) is running
    detection_running = False
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "seewhozthere"],
            capture_output=True, text=True, timeout=5
        )
        detection_running = result.stdout.strip() == "active"
    except Exception:
        detection_running = False
    
    # 2. Check Hailo hardware availability (device file exists)
    hailo_available = False
    try:
        import os
        hailo_available = (
            os.path.exists("/dev/hailo0") or
            os.path.exists("/dev/hailo") or
            len([f for f in os.listdir("/dev") if f.startswith("hailo")]) > 0
        )
    except Exception:
        hailo_available = False
    
    # 3. Count configured cameras from config.ini (shared file, accessible to both processes)
    cameras = get_cameras()
    active_cameras = len(cameras)
    camera_names = list(cameras.keys())
    
    # 4. Known people count from shared database
    known_people = 0
    try:
        db = get_db()
        stats = db.get_statistics()
        known_people = stats.get('total_visitors', 0)
    except Exception:
        known_people = 0
    
    return {
        "running": detection_running,
        "hailo_available": hailo_available,
        "active_cameras": active_cameras,
        "camera_names": camera_names,
        "known_people": known_people,
        "face_detector": "Hailo AI" if hailo_available else "OpenCV"
    }


# --- Analytics API Endpoints ---

@app.get("/api/analytics/stats")
async def get_analytics_stats():
    """Get overall statistics for dashboard."""
    analytics = get_analytics()
    return analytics.get_stats()


@app.get("/api/analytics/hourly")
async def get_hourly_activity():
    """Get hourly activity breakdown."""
    analytics = get_analytics()
    return {"hourly": analytics.get_hourly_activity()}


@app.get("/api/analytics/known-unknown")
async def get_known_unknown():
    """Get known vs unknown visitor count."""
    analytics = get_analytics()
    return analytics.get_known_vs_unknown()


@app.get("/api/analytics/weekly")
async def get_weekly_trend():
    """Get weekly visitor trend."""
    analytics = get_analytics()
    return {"weekly": analytics.get_weekly_trend()}


@app.get("/api/analytics/cameras")
async def get_camera_activity():
    """Get activity breakdown by camera."""
    analytics = get_analytics()
    return {"cameras": analytics.get_camera_activity()}


@app.get("/api/analytics/top-visitors")
async def get_top_visitors():
    """Get top visitors by sighting count."""
    analytics = get_analytics()
    return {"visitors": analytics.get_top_visitors()}


@app.get("/api/analytics/heatmap")
async def get_heatmap():
    """Get heatmap data for peak hours visualization."""
    analytics = get_analytics()
    return {"heatmap": analytics.get_heatmap_data()}



# --- Short-form API Endpoints (for React dashboard compatibility) ---
@app.get("/api/stats")
async def get_stats_short():
    """Short-form stats endpoint for React dashboard."""
    analytics = get_analytics()
    return analytics.get_stats()

@app.get("/api/hourly")
async def get_hourly_short():
    """Short-form hourly endpoint for React dashboard."""
    analytics = get_analytics()
    return analytics.get_hourly_activity()

@app.get("/api/known-unknown")
async def get_known_unknown_short():
    """Short-form known-unknown endpoint for React dashboard."""
    analytics = get_analytics()
    return analytics.get_known_vs_unknown()

@app.get("/api/weekly")
async def get_weekly_short():
    """Short-form weekly endpoint for React dashboard."""
    analytics = get_analytics()
    return analytics.get_weekly_trend()

@app.get("/api/cameras")
async def get_cameras_short():
    """Short-form cameras endpoint for React dashboard."""
    analytics = get_analytics()
    return analytics.get_camera_activity()

@app.get("/api/top-visitors")
async def get_top_visitors_short():
    """Short-form top-visitors endpoint for React dashboard."""
    analytics = get_analytics()
    return analytics.get_top_visitors()

@app.get("/api/today-visitors")
async def get_today_visitors():
    """Get today's sightings (known + unknown) for React dashboard."""
    analytics = get_analytics()
    sightings = analytics.get_today_sightings(limit=20)
    return {"sightings": sightings}

@app.get("/api/heatmap")
async def get_heatmap_short():
    """Short-form heatmap endpoint for React dashboard."""
    analytics = get_analytics()
    return analytics.get_heatmap_data()

# --- Camera Configuration API ---

@app.get("/api/config/cameras")
async def get_cameras_config():
    """Get current camera configuration from config.ini."""
    import configparser
    config = configparser.ConfigParser()
    config_path = PROJECT_ROOT / "config.ini"
    if config_path.exists():
        config.read(str(config_path))
    cameras = {}
    if config.has_section("CAMERAS"):
        for name, url in config.items("CAMERAS"):
            cameras[name] = url
    return {"cameras": cameras}


@app.post("/api/config/cameras")
async def save_cameras_config(request: Request):
    """Save camera configuration to config.ini."""
    import configparser
    data = await request.json()
    cameras = data.get("cameras", {})
    
    config = configparser.ConfigParser()
    config_path = PROJECT_ROOT / "config.ini"
    
    # Read existing config to preserve other settings
    if config_path.exists():
        config.read(str(config_path))
    
    # Ensure required sections exist
    for section in ["GENERAL", "SCHEDULER", "TELEGRAM", "EMAIL", "CAMERAS"]:
        if not config.has_section(section):
            config.add_section(section)
    
    # Set defaults if not present
    if not config.has_option("GENERAL", "timezone"):
        config.set("GENERAL", "timezone", "UTC")
    if not config.has_option("GENERAL", "port"):
        config.set("GENERAL", "port", "7222")
    if not config.has_option("GENERAL", "database_path"):
        config.set("GENERAL", "database_path", "data/seewhozthere.db")
    
    # Remove all existing camera entries
    for key in list(config.options("CAMERAS")):
        config.remove_option("CAMERAS", key)
    
    # Add new camera entries
    for name, url in cameras.items():
        safe_name = name.strip().lower().replace(" ", "_")
        if safe_name and url.strip():
            config.set("CAMERAS", safe_name, url.strip())
    
    # Write back to file
    with open(str(config_path), "w") as f:
        config.write(f)
    
    return {"success": True, "message": f"Saved {len(cameras)} camera(s). Restart the detection service to apply changes."}


@app.get("/api/config/general")
async def get_general_config():
    """Get general configuration settings."""
    import configparser
    config = configparser.ConfigParser()
    config_path = PROJECT_ROOT / "config.ini"
    if config_path.exists():
        config.read(str(config_path))
    return {
        "timezone": config.get("GENERAL", "timezone", fallback="UTC"),
        "port": config.getint("GENERAL", "port", fallback=7222),
        "scheduler_enabled": config.getboolean("SCHEDULER", "enabled", fallback=False),
        "telegram_configured": bool(config.get("TELEGRAM", "bot_token", fallback="").strip()),
    }


@app.post("/api/config/general")
async def save_general_config(request: Request):
    """Save general configuration settings."""
    import configparser
    data = await request.json()
    
    config = configparser.ConfigParser()
    config_path = PROJECT_ROOT / "config.ini"
    if config_path.exists():
        config.read(str(config_path))
    
    for section in ["GENERAL", "SCHEDULER", "TELEGRAM", "EMAIL", "CAMERAS"]:
        if not config.has_section(section):
            config.add_section(section)
    
    if "timezone" in data:
        config.set("GENERAL", "timezone", str(data["timezone"]))
    
    with open(str(config_path), "w") as f:
        config.write(f)
    
    return {"success": True, "message": "Settings saved. Restart services to apply changes."}


# --- Service Control API ---

@app.post("/api/service/action")
async def service_action(request: Request):
    """Control the detection service via systemctl or process management."""
    import subprocess
    data = await request.json()
    action = data.get("action", "")  # start | stop | restart | status
    
    if action not in ("start", "stop", "restart", "status"):
        raise HTTPException(status_code=400, detail="Invalid action. Use: start, stop, restart, status")
    
    service_name = "seewhozthere"
    
    try:
        if action == "status":
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True, text=True, timeout=5
            )
            active = result.stdout.strip() == "active"
            # Also check if systemd service exists
            exists_result = subprocess.run(
                ["systemctl", "status", service_name],
                capture_output=True, text=True, timeout=5
            )
            installed = exists_result.returncode != 4  # 4 = unit not found
            return {
                "active": active,
                "installed": installed,
                "status": result.stdout.strip(),
                "details": exists_result.stdout[:500] if installed else "Service not installed"
            }
        else:
            result = subprocess.run(
                ["sudo", "systemctl", action, service_name],
                capture_output=True, text=True, timeout=15
            )
            success = result.returncode == 0
            return {
                "success": success,
                "action": action,
                "message": f"Service {action} {'succeeded' if success else 'failed'}",
                "output": result.stdout + result.stderr
            }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Service command timed out")
    except FileNotFoundError:
        # systemctl not available (non-systemd system)
        return {
            "success": False,
            "action": action,
            "message": "systemctl not available on this system",
            "installed": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/service/status")
async def get_service_status():
    """Get the systemd service status."""
    import subprocess
    service_name = "seewhozthere"
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True, text=True, timeout=5
        )
        active = result.stdout.strip() == "active"
        exists_result = subprocess.run(
            ["systemctl", "status", service_name],
            capture_output=True, text=True, timeout=5
        )
        installed = exists_result.returncode != 4
        return {
            "active": active,
            "installed": installed,
            "status": result.stdout.strip()
        }
    except Exception:
        return {"active": False, "installed": False, "status": "unknown"}


## --- Login / Auth Endpoints ---

@app.get("/login")
@app.get("/login/")
async def serve_login_redirect():
    """Redirect old /login URL to the React-handled /dashboard/login."""
    return RedirectResponse(url="/dashboard/login", status_code=302)


@app.post("/api/login")
async def api_login(request: Request, response: Response):
    """Validate passphrase and set session cookie."""
    body = await request.json()
    passphrase = body.get("passphrase", "")

    if not SECURITY_LOGIN_ENABLED:
        return {"success": True, "message": "Login not required"}

    if passphrase == SECURITY_PASSPHRASE:
        token = _make_token()
        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            httponly=True,
            samesite="lax",
            max_age=int(SECURITY_SESSION_HOURS * 3600),
            path="/"
        )
        return {"success": True}
    else:
        return JSONResponse({"success": False, "error": "Incorrect passphrase"}, status_code=401)


@app.post("/api/logout")
async def api_logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"success": True}


@app.get("/api/auth-status")
async def api_auth_status(request: Request):
    """Return whether the user is authenticated and whether login is enabled."""
    return {
        "login_enabled": SECURITY_LOGIN_ENABLED,
        "authenticated": _is_authenticated(request),
        "default_passphrase": SECURITY_PASSPHRASE == "changeme" and SECURITY_LOGIN_ENABLED
    }


# --- Main Execution ---
def start():
    """Entry point for running the Uvicorn server."""
    is_development = os.environ.get("APP_ENV") == "development"
    
    print(f"--- SeeWhozThere v2 Web Server Starting in {'DEVELOPMENT' if is_development else 'PRODUCTION'} mode ---")
    
    reload_dirs = [str(APP_DIR)] if is_development else None
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=is_development,
        reload_dirs=reload_dirs
    )


if __name__ == "__main__":
    os.environ["APP_ENV"] = "development"
    start()
