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


# --- Mock Data Function ---
# This function simulates the data we will eventually get from our database.
def get_mock_daily_summary():
    """Generates a fake list of visitor sightings for demonstration."""
    return {
        "summary_date": datetime.date.today().isoformat(),
        "timezone": TIMEZONE,
        "visitors": [
            {
                "id": "person_01",
                "name": "Bob",
                "is_known": True,
                "first_seen": "09:15:32",
                "last_seen": "14:20:01",
                "sighting_count": 3,
                "thumbnail_url": "/static/mock_faces/bob.jpg"
            },
            {
                "id": "person_02",
                "name": "Unknown",
                "is_known": False,
                "first_seen": "11:30:15",
                "last_seen": "11:30:15",
                "sighting_count": 1,
                "thumbnail_url": "/static/mock_faces/unknown_1.jpg"
            },
            {
                "id": "person_03",
                "name": "Delivery Driver",
                "is_known": True,
                "first_seen": "12:05:45",
                "last_seen": "12:05:45",
                "sighting_count": 1,
                "thumbnail_url": "/static/mock_faces/delivery.jpg"
            },
        ]
    }

# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Serves the main dashboard page.
    """
    print("Request received for the main dashboard.")
    
    # Get the (mock) data for today's summary
    summary_data = get_mock_daily_summary()
    
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
