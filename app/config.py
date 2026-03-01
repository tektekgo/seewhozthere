import configparser
from pathlib import Path

# Build the path to the config file (it's in the parent directory of app/)
CONFIG_PATH = Path(__file__).parent.parent / "config.ini"


def _load_config() -> configparser.RawConfigParser:
    """Load and return the config file. Uses RawConfigParser to avoid
    interpolation issues with special characters (%, $, etc.) in RTSP URLs."""
    config = configparser.RawConfigParser()
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Error: Configuration file not found at {CONFIG_PATH}. "
            "Please create it from the template."
        )
    config.read(str(CONFIG_PATH))
    return config


def get_cameras() -> dict:
    """Read cameras fresh from config.ini each time. Call this at service
    start-up so a restart always picks up the latest camera list."""
    config = _load_config()
    if config.has_section("CAMERAS"):
        return dict(config.items("CAMERAS"))
    return {}


# Load once at import time for settings that don't change at runtime
_config = _load_config()

# --- Exported settings ---

# General settings
TIMEZONE = _config.get("GENERAL", "timezone", fallback="UTC")
PORT = _config.getint("GENERAL", "port", fallback=7222)
DATABASE_PATH = _config.get("GENERAL", "database_path", fallback="data/seewhozthere.db")

# Scheduler settings
SCHEDULER_ENABLED = _config.getboolean("SCHEDULER", "enabled", fallback=False)
SCHEDULER_SEND_TIME = _config.get("SCHEDULER", "send_time", fallback="20:00")
SCHEDULER_SERVICE = _config.get("SCHEDULER", "service", fallback="telegram")

# Telegram settings
TELEGRAM_BOT_TOKEN = _config.get("TELEGRAM", "bot_token", fallback="")
TELEGRAM_CHAT_ID = _config.get("TELEGRAM", "chat_id", fallback="")

# Security settings
SECURITY_PASSPHRASE = _config.get("SECURITY", "passphrase", fallback="changeme")
SECURITY_SESSION_HOURS = _config.getint("SECURITY", "session_hours", fallback=24)
# Login is enabled whenever a non-empty passphrase is set
SECURITY_LOGIN_ENABLED = bool(SECURITY_PASSPHRASE.strip())

# Camera settings — loaded at import time for backwards compatibility.
# NOTE: Use get_cameras() in long-running services so a restart picks up changes.
CAMERAS = get_cameras()