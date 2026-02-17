"""
SeeWhozThere Web Server v2

Enhanced version with user management, face recognition training, and API endpoints.
"""

import uvicorn
import os
import io
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import cv2

# Import our configuration settings
from app.config import TIMEZONE, PORT
from app.database import get_db
from app.face_recognition_engine import get_face_recognition_engine
from app.hailo_processor_v2 import get_processor


# --- Application Setup ---

app = FastAPI(title="SeeWhozThere v2")

# Define the absolute path to the 'app' directory
APP_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = APP_DIR.parent

# Mount static directories
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.mount("/data", StaticFiles(directory=PROJECT_ROOT / "data"), name="data")

# Setup Jinja2 for HTML templating
templates = Jinja2Templates(directory=APP_DIR / "templates")


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
async def get_dashboard(request: Request):
    """Serves the main dashboard page."""
    summary_data = get_daily_summary()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "summary": summary_data}
    )


# --- API Endpoints for User Management ---

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


@app.get("/api/status")
async def get_system_status():
    """Get current system status."""
    try:
        processor = get_processor()
        status = processor.get_status()
        
        return {
            "running": status['running'],
            "hailo_available": status['hailo_available'],
            "active_cameras": status['active_cameras'],
            "camera_names": status['camera_names'],
            "known_people": status['known_people'],
            "stats": status.get('stats', {})
        }
    except Exception as e:
        return {
            "running": False,
            "error": str(e)
        }


# --- Main Execution ---

def start():
    """Entry point for running the Uvicorn server."""
    is_development = os.environ.get("APP_ENV") == "development"
    
    print(f"--- SeeWhozThere v2 Web Server Starting in {'DEVELOPMENT' if is_development else 'PRODUCTION'} mode ---")
    
    reload_dirs = [str(APP_DIR)] if is_development else None
    
    uvicorn.run(
        "app.main_v2:app",
        host="0.0.0.0",
        port=PORT,
        reload=is_development,
        reload_dirs=reload_dirs
    )


if __name__ == "__main__":
    os.environ["APP_ENV"] = "development"
    start()
