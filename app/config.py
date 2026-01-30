import configparser
from pathlib import Path

# Build the path to the config file (it's in the parent directory)
config_path = Path(__file__).parent.parent / "config.ini"

# Create a config parser object
config = configparser.ConfigParser()

# Check if the config file exists before trying to read it
if not config_path.exists():
    raise FileNotFoundError(
        f"Error: Configuration file not found at {config_path}. "
        "Please create it from the template."
    )

config.read(config_path)

# --- Now we can export settings for the rest of the app to use ---

# General settings
TIMEZONE = config.get("GENERAL", "timezone", fallback="UTC")
PORT = config.getint("GENERAL", "port", fallback=7222)
DATABASE_PATH = config.get("GENERAL", "database_path", fallback="data/seewhozthere.db")

# Scheduler settings
SCHEDULER_ENABLED = config.getboolean("SCHEDULER", "enabled", fallback=False)
SCHEDULER_SEND_TIME = config.get("SCHEDULER", "send_time", fallback="20:00")
SCHEDULER_SERVICE = config.get("SCHEDULER", "service", fallback="telegram")

# Telegram settings
TELEGRAM_BOT_TOKEN = config.get("TELEGRAM", "bot_token", fallback="")
TELEGRAM_CHAT_ID = config.get("TELEGRAM", "chat_id", fallback="")

# Camera settings
# This reads the entire [CAMERAS] section into a dictionary
CAMERAS = dict(config.items("CAMERAS"))

# Example of how to use it elsewhere in the app:
# from app.config import CAMERAS
# for camera_name, url in CAMERAS.items():
#     print(f"Found camera: {camera_name} with URL: {url}")