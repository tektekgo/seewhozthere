import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import datetime
import os

# Import our configuration settings from config.py
from app.config import TIMEZONE, PORT

# Import database functions
from app.database import get_db

# --- Application Setup ---

# Create the main FastAPI application instance
app = FastAPI(title="SeeWhozThere")

# Define the absolute path to the 'app' directory
# This is a more robust way to handle paths
APP_DIR = Path(__file__).parent.resolve()

# Mount the 'static' directory using the absolute path
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

# Setup Jinja2 for HTML templating using the absolute path
templates = Jinja2Templates(directory=APP_DIR / "templates")


# --- Data Functions ---

def get_daily_summary():
    """Gets today's visitor summary from the database."""
    db = get_db()
    summary = db.get_today_summary()
    stats = db.get_statistics()
    
    # Transform database format to template format
    visitors = []
    unknown_count = 0
    
    for visitor in summary:
        # Format timestamps
        first_seen_time = visitor['first_seen'].strftime('%H:%M:%S') if visitor['first_seen'] else 'N/A'
        last_seen_time = visitor['last_seen'].strftime('%H:%M:%S') if visitor['last_seen'] else 'N/A'
        
        # Determine thumbnail URL
        thumbnail_url = visitor.get('thumbnail_path') or visitor.get('latest_snapshot') or '/static/mock_faces/unknown_1.jpg'
        
        is_known = visitor['visitor_id'] != 0
        if not is_known:
            unknown_count += 1
        
        visitors.append({
            "id": f"visitor_{visitor['visitor_id']}",
            "name": visitor['name'],
            "is_known": is_known,
            "first_seen": first_seen_time,
            "last_seen": last_seen_time,
            "sighting_count": visitor['sighting_count'],
            "thumbnail_url": thumbnail_url
        })
    
    return {
        "summary_date": datetime.date.today().isoformat(),
        "timezone": TIMEZONE,
        "visitors": visitors,
        "total_visitors": stats['total_visitors'],
        "unknown_count": unknown_count,
        "active_cameras": 0  # Will be populated when cameras are connected
    }

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Serves the main dashboard page.
    """
    print("Request received for the main dashboard.")
    
    # Get the real data from the database
    summary_data = get_daily_summary()
    
    # Render the index.html template, passing the data to it
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "summary": summary_data}
    )

# --- Main Execution ---

def start():
    """
    This function is the entry point for running the Uvicorn server.
    It checks an environment variable to determine if it should run in
    development (reload=True) or production (reload=False) mode.
    """
    is_development = os.environ.get("APP_ENV") == "development"

    print(f"--- SeeWhozThere Web Server Starting in {'DEVELOPMENT' if is_development else 'PRODUCTION'} mode ---")

    # In development mode, we specify which directory to watch for changes.
    # This prevents the reload loop issue.
    reload_dirs = [str(APP_DIR)] if is_development else None

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=is_development,
        reload_dirs=reload_dirs
    )

if __name__ == "__main__":
    # When running directly on the laptop, set the environment variable
    # before calling start(), so it runs in development mode.
    os.environ["APP_ENV"] = "development"
    start()
