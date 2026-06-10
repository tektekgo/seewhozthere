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
from PIL import Image
from contextlib import asynccontextmanager

# Import our configuration settings
from app.config import TIMEZONE, PORT, SECURITY_PASSPHRASE, SECURITY_SESSION_HOURS, SECURITY_LOGIN_ENABLED
from app.database import get_db
from app.face_recognition_engine import get_face_recognition_engine
from app.hailo_processor_v2 import get_processor
from app.analytics import get_analytics
from app.telegram_notifier import start_scheduler, stop_scheduler


# --- Application Setup ---

@asynccontextmanager
async def lifespan(app_instance):
    """Start background services on startup and clean up on shutdown."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="SeeWhozThere v2", lifespan=lifespan)

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

# Define dashboard directory paths
dashboard_dir = APP_DIR / "static" / "dashboard"
dashboard_assets_dir = dashboard_dir / "assets"

# Mount React dashboard assets FIRST — must come before the broad /static mount
# because /static/dashboard/ would otherwise intercept /dashboard/assets/* requests.
#
# index.js and index.css are served with Cache-Control: no-store so that
# Cloudflare, browsers, and any proxy always fetch the latest build after a git pull.
# Other assets (logo.png etc.) are served normally via StaticFiles.
if dashboard_assets_dir.exists():
    from starlette.responses import FileResponse as _AssetFileResponse
    from starlette.requests import Request as _AssetRequest

    _no_cache_assets = ["index.js", "index.css"]

    def _make_no_cache_asset_handler(asset_path):
        async def _handler(request: _AssetRequest):
            return _AssetFileResponse(
                str(asset_path),
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        return _handler

    for _asset_name in _no_cache_assets:
        _asset_path = dashboard_assets_dir / _asset_name
        if _asset_path.exists():
            app.add_api_route(
                f"/dashboard/assets/{_asset_name}",
                _make_no_cache_asset_handler(_asset_path),
                methods=["GET"],
                include_in_schema=False,
            )

    # All other assets (logo, fonts, etc.) served normally with default caching
    app.mount("/dashboard/assets", StaticFiles(directory=dashboard_assets_dir), name="dashboard_assets")

# Mount broad static directory (covers /static/mock_faces etc.)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.mount("/data", StaticFiles(directory=PROJECT_ROOT / "data"), name="data")

# Serve root-level dashboard files (favicon.ico, logo PNGs, robots.txt etc.)
# These are referenced as /dashboard/favicon.ico etc. in the built index.html
if dashboard_dir.exists():
    from starlette.responses import FileResponse as _FileResponse
    _dashboard_root_files = ["favicon.ico", "favicon.png", "logo.png", "logo-16.png", "logo-32.png", "logo-192.png", "robots.txt", "placeholder.svg"]
    for _fname in _dashboard_root_files:
        _fpath = dashboard_dir / _fname
        if _fpath.exists():
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
    """Get all known visitors with sighting counts."""
    db = get_db()
    visitors = db.get_all_visitors()

    # Fetch sighting counts per visitor in one query
    sighting_counts: dict = {}
    last_seen_map: dict = {}
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT visitor_id, COUNT(*) as cnt, MAX(timestamp) as last_seen
            FROM sightings
            WHERE visitor_id IS NOT NULL
            GROUP BY visitor_id
        """)
        for row in cursor.fetchall():
            sighting_counts[row['visitor_id']] = row['cnt']
            last_seen_map[row['visitor_id']] = row['last_seen']
        conn.close()
    except Exception:
        pass

    # Format for API response
    result = []
    for visitor in visitors:
        vid = visitor['id']
        result.append({
            "id": vid,
            "name": visitor['name'],
            "thumbnail_path": visitor.get('thumbnail_path'),
            "created_at": visitor['created_at'].isoformat() if visitor.get('created_at') else None,
            "has_encoding": visitor.get('face_encoding') is not None,
            "sighting_count": sighting_counts.get(vid, 0),
            "last_seen": last_seen_map.get(vid),
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
    
    # Check if visitor already exists — if so, treat as an update (upsert)
    existing = db.get_visitor_by_name(name)
    if existing:
        # Delegate to the update path so re-submitting with a photo fixes a partial record
        return await update_visitor(
            visitor_id=existing['id'],
            name=name,
            photo=photo,
        )
    
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
            
            # ── Image optimisation ──────────────────────────────────────────────
            # Resize large images to max 800×800 before encoding/saving
            MAX_DIM = 800
            h, w = img.shape[:2]
            if max(h, w) > MAX_DIM:
                scale = MAX_DIM / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            # Save thumbnail (200×200 square crop from centre)
            th, tw = img.shape[:2]
            side = min(th, tw)
            y0 = (th - side) // 2
            x0 = (tw - side) // 2
            thumbnail = cv2.resize(img[y0:y0+side, x0:x0+side], (200, 200))
            cv2.imwrite(str(thumbnail_path), thumbnail)

            # Convert to relative path for database
            thumbnail_path_str = f"data/thumbnails/{thumbnail_filename}"

            # Generate face encoding (may be None if ArcFace finds no face in the photo)
            encoding = face_recognition.encode_face(img)
            if encoding is not None:
                face_encoding_blob = encoding.tobytes()
            # If encoding is None, face_encoding_blob stays None — visitor is added without encoding

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
            "id": visitor_id,          # used by frontend NameDialog (addRes.id)
            "visitor_id": visitor_id,  # kept for backward compatibility
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
            
            # ── Image optimisation ──────────────────────────────────────────────
            MAX_DIM = 800
            h, w = img.shape[:2]
            if max(h, w) > MAX_DIM:
                scale = MAX_DIM / max(h, w)
                img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

            # Save thumbnail (200×200 square crop from centre)
            th, tw = img.shape[:2]
            side = min(th, tw)
            y0 = (th - side) // 2
            x0 = (tw - side) // 2
            thumbnail = cv2.resize(img[y0:y0+side, x0:x0+side], (200, 200))
            cv2.imwrite(str(thumbnail_path), thumbnail)

            update_data['thumbnail_path'] = f"data/thumbnails/{thumbnail_filename}"

            # Generate new face encoding (may be None if ArcFace finds no face in the photo)
            encoding = face_recognition.encode_face(img)
            if encoding is not None:
                update_data['face_encoding'] = encoding.tobytes()
            # If encoding is None, skip updating the encoding — keep the existing one
            
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



@app.post("/api/visitors/{visitor_id}/reset-encoding")
async def reset_visitor_encoding(visitor_id: int):
    """
    Clear ALL stored face encodings for a visitor so they can be re-enrolled cleanly.
    Clears both the legacy face_encoding column and the new face_encodings table.
    The visitor will appear as Unknown until clean encodings are captured.
    """
    db = get_db()
    visitor = db.get_visitor(visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    try:
        # clear_face_encodings handles both the new table and the legacy column
        deleted = db.clear_face_encodings(visitor_id)
        print(f"[reset-encoding] Cleared {deleted} encoding(s) for '{visitor['name']}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset encoding: {e}")
    # Reload known faces so the processor stops recognising this person until re-enrolled
    try:
        processor = get_processor()
        processor.reload_known_faces()
    except Exception:
        pass
    return {
        "success": True,
        "message": (
            f"All face encodings cleared for '{visitor['name']}'. "
            "They will appear as Unknown until re-enrolled from a clean detection."
        ),
    }

@app.post("/api/visitors/reset-all-encodings")
async def reset_all_encodings():
    """
    Clear ALL stored face encodings for EVERY visitor.

    Use this when the encoding database has been contaminated by false positives
    (e.g. birds, shadows, or objects that were incorrectly labelled as people).
    After calling this endpoint, all visitors will appear as Unknown until they
    are re-enrolled by walking past the camera and being identified via Telegram
    or the dashboard.

    This does NOT delete any visitors or sightings — only the face embeddings.
    """
    db = get_db()
    visitors = db.get_all_visitors()
    cleared_count = 0
    results = []
    for visitor in visitors:
        try:
            deleted = db.clear_face_encodings(visitor['id'])
            cleared_count += deleted
            results.append({"name": visitor['name'], "encodings_cleared": deleted})
            print(f"[reset-all-encodings] Cleared {deleted} encoding(s) for '{visitor['name']}'")
        except Exception as e:
            print(f"[reset-all-encodings] Failed for '{visitor['name']}': {e}")
    # Reload known faces so the processor immediately stops matching anyone
    try:
        processor = get_processor()
        processor.reload_known_faces()
    except Exception:
        pass
    return {
        "success": True,
        "message": (
            f"Cleared {cleared_count} total encoding(s) across {len(visitors)} visitor(s). "
            "Everyone will appear as Unknown until re-enrolled."
        ),
        "details": results,
    }


@app.post("/api/sightings/{sighting_id}/identify")
async def identify_sighting(sighting_id: int, visitor_id: int = Form(...)):
    """
    Associate a sighting with a known visitor and accumulate a new face encoding.

    Every confirmed identification adds a new encoding to the face_encodings table
    (capped at 20 per person). This means the more you correct the system, the
    better it gets at recognising each person across different lighting and angles.
    """
    db = get_db()

    # Verify visitor exists
    visitor = db.get_visitor(visitor_id)
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")

    # Get the sighting snapshot path
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT snapshot_path FROM sightings WHERE id = ?", (sighting_id,))
    row = cursor.fetchone()
    conn.close()
    snapshot_path = dict(row)["snapshot_path"] if row else None

    # Associate sighting with visitor
    success = db.identify_sighting(sighting_id, visitor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sighting not found")

    encoding_saved = False
    encoding_count = db.get_encoding_count(visitor_id)

    # Always try to extract and accumulate a new encoding from this snapshot.
    # This is the core of Part 2: every confirmed sighting teaches the system.
    if snapshot_path:
        try:
            import cv2 as _cv2
            from app.face_recognition_engine import get_face_recognition_engine as _get_fre

            img = _cv2.imread(snapshot_path)
            if img is not None:
                fre = _get_fre()
                encoding = fre.encode_face(img)

                # encode_face() returns None when ArcFace finds no face in the
                # snapshot (e.g. the snapshot is a bird or shadow that slipped
                # through detection).  Do NOT save a None encoding — that would
                # poison the database and cause future false-positive matches.
                if encoding is None:
                    print(f"[identify] ArcFace found no face in snapshot for sighting {sighting_id} — skipping encoding save")
                else:
                    encoding_bytes = encoding.astype(np.float32).tobytes()

                    # Add to multi-encoding table (auto-capped at 20)
                    db.add_face_encoding(visitor_id, encoding_bytes, source='sighting')
                    encoding_count = db.get_encoding_count(visitor_id)

                    # Also keep the legacy face_encoding column in sync (first encoding only)
                    if not visitor.get("face_encoding"):
                        thumb = visitor.get("thumbnail_path") or snapshot_path
                        db.update_visitor(visitor_id, face_encoding=encoding_bytes, thumbnail_path=thumb)

                    # Reload known faces in the running detection processor
                    try:
                        processor = get_processor()
                        processor.reload_known_faces()
                        print(f"[identify] Added encoding #{encoding_count} for {visitor['name']} — reloaded detector")
                    except Exception as reload_err:
                        print(f"[identify] Encoding saved but reload failed: {reload_err}")

                    encoding_saved = True
        except Exception as enc_err:
            print(f"[identify] Could not extract encoding from snapshot: {enc_err}")

    return {
        "success": True,
        "message": f"Identified as {visitor['name']}",
        "encoding_saved": encoding_saved,
        "encoding_count": encoding_count,
        "visitor_name": visitor['name']
    }


@app.post("/api/sightings/{sighting_id}/unidentify")
async def unidentify_sighting(sighting_id: int):
    """
    Remove the visitor association from a sighting, marking it as Unknown again.
    Useful for correcting a misidentification before re-assigning the correct person.
    """
    db = get_db()
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sightings SET visitor_id = NULL WHERE id = ?",
        (sighting_id,)
    )
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Sighting not found")
    conn.commit()
    conn.close()
    return {"success": True, "message": "Sighting marked as Unknown"}


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



@app.post("/api/sightings/bulk-unidentify")
async def bulk_unidentify_sightings(ids: list[int] = Body(..., embed=True)):
    """
    Remove visitor associations from multiple sightings at once.
    Sets visitor_id = NULL on each sighting so they appear as Unknown.
    Does NOT delete the sighting records or snapshot files.
    """
    if not ids:
        return {"success": True, "updated": 0}
    db = get_db()
    conn = db._get_connection()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    cursor.execute(
        f"UPDATE sightings SET visitor_id = NULL WHERE id IN ({placeholders})",
        ids,
    )
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return {"success": True, "updated": updated}

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
    
    # 5. Recognition engine info
    recognition_engine = "Unknown"
    try:
        from app.face_recognition_engine import get_face_recognition_engine
        engine = get_face_recognition_engine()
        recognition_engine = "ArcFace" if engine._using_arcface else "HOG/LBP"
    except Exception:
        recognition_engine = "Unknown"

    return {
        "running": detection_running,
        "hailo_available": hailo_available,
        "active_cameras": active_cameras,
        "camera_names": camera_names,
        "known_people": known_people,
        "face_detector": "Hailo AI" if hailo_available else "OpenCV",
        "recognition_engine": recognition_engine
    }



@app.get("/api/status/recognition")
async def get_recognition_status():
    """Detailed recognition engine status for the Settings page."""
    try:
        from app.face_recognition_engine import get_face_recognition_engine
        engine = get_face_recognition_engine()
        using_arcface = engine._using_arcface
        threshold = engine.recognition_threshold

        # Count total encodings across all visitors
        total_encodings = 0
        people_trained = 0
        try:
            db = get_db()
            visitors = db.get_all_visitors()
            for v in visitors:
                encs = db.get_face_encodings(v['id'])
                count = len(encs)
                total_encodings += count
                if count > 0:
                    people_trained += 1
        except Exception:
            pass

        return {
            "engine": "InsightFace ArcFace (buffalo_sc)" if using_arcface else "HOG/LBP (fallback)",
            "engine_short": "ArcFace" if using_arcface else "HOG/LBP",
            "using_arcface": using_arcface,
            "model": "buffalo_sc — 512-dim embeddings" if using_arcface else "HOG + LBP + Color Histogram",
            "recognition_threshold": threshold,
            "people_trained": people_trained,
            "total_encodings": total_encodings,
            "status": "optimal" if using_arcface else "degraded",
            "status_message": (
                "ArcFace deep learning model active — optimised for outdoor surveillance"
                if using_arcface else
                "HOG/LBP fallback active — install insightface for better accuracy"
            )
        }
    except Exception as e:
        return {
            "engine": "Unknown",
            "engine_short": "Unknown",
            "using_arcface": False,
            "model": "Unknown",
            "recognition_threshold": 0.40,
            "people_trained": 0,
            "total_encodings": 0,
            "status": "unknown",
            "status_message": f"Could not read engine status: {e}"
        }


# --- Storage Health API Endpoint ---

@app.get("/api/storage")
async def get_storage_health():
    """
    Return storage health metrics for the dashboard Storage Health panel.
    Reports snapshot counts, disk usage, and cleanup history.
    """
    import sqlite3
    import re

    snapshots_dir = PROJECT_ROOT / "data" / "snapshots"
    db_path = PROJECT_ROOT / "data" / "seewhozthere.db"
    cleanup_log = PROJECT_ROOT / "cleanup.log"

    # --- Snapshot counts ---
    total_snapshots = 0
    snapshots_this_week = 0
    oldest_snapshot: Optional[str] = None

    try:
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) as cnt FROM sightings WHERE snapshot_path IS NOT NULL AND snapshot_path != ''")
            row = cur.fetchone()
            total_snapshots = row["cnt"] if row else 0

            cur.execute(
                "SELECT COUNT(*) as cnt FROM sightings "
                "WHERE snapshot_path IS NOT NULL AND snapshot_path != '' "
                "AND timestamp >= datetime('now', '-7 days')"
            )
            row = cur.fetchone()
            snapshots_this_week = row["cnt"] if row else 0

            cur.execute(
                "SELECT timestamp FROM sightings "
                "WHERE snapshot_path IS NOT NULL AND snapshot_path != '' "
                "ORDER BY timestamp ASC LIMIT 1"
            )
            row = cur.fetchone()
            oldest_snapshot = row["timestamp"] if row else None

            conn.close()
    except Exception:
        pass

    # --- Disk space used by snapshot files ---
    disk_bytes_used = 0
    try:
        if snapshots_dir.exists():
            disk_bytes_used = sum(
                f.stat().st_size for f in snapshots_dir.iterdir() if f.is_file()
            )
    except Exception:
        disk_bytes_used = 0

    disk_mb_used = round(disk_bytes_used / (1024 * 1024), 2)

    # --- Cleanup log parsing ---
    last_cleanup_date: Optional[str] = None
    last_cleanup_freed_mb: float = 0.0
    last_cleanup_deleted: int = 0
    total_cleanups: int = 0

    try:
        if cleanup_log.exists():
            log_text = cleanup_log.read_text(errors="ignore")
            total_cleanups = log_text.count("Starting SeeWhozThere\u00ae cleanup")
            lines = log_text.splitlines()
            found_freed = False
            found_deleted = False
            for line in reversed(lines):
                if not found_freed and "freeing" in line and "MB" in line:
                    m = re.search(r"freeing ([\d.]+) MB", line)
                    if m:
                        last_cleanup_freed_mb = float(m.group(1))
                        found_freed = True
                if not found_deleted and "Deleted" in line and "snapshot images" in line:
                    m = re.search(r"Deleted (\d+) snapshot", line)
                    if m:
                        last_cleanup_deleted = int(m.group(1))
                        found_deleted = True
                if last_cleanup_date is None:
                    m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
                    if m:
                        last_cleanup_date = m.group(1)
                if last_cleanup_date and found_freed and found_deleted:
                    break
    except Exception:
        pass

    return {
        "total_snapshots": total_snapshots,
        "snapshots_this_week": snapshots_this_week,
        "disk_mb_used": disk_mb_used,
        "oldest_snapshot": oldest_snapshot,
        "last_cleanup_date": last_cleanup_date,
        "last_cleanup_freed_mb": last_cleanup_freed_mb,
        "last_cleanup_deleted": last_cleanup_deleted,
        "total_cleanups": total_cleanups,
    }


# --- Analytics API Endpoints ---

@app.get("/api/analytics/stats")
async def get_analytics_stats():
    """Get overall statistics for dashboard."""
    analytics = get_analytics()
    return analytics.get_stats()
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
