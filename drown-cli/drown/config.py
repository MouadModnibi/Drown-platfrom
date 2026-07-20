"""Configuration management for Drown CLI."""

import json
import os
from pathlib import Path

# Default API base URL
DEFAULT_API_BASE = "https://dashboard.dr0wn.duckdns.org"

# Config file location
CONFIG_DIR = Path.home() / ".drown"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_api_base():
    """Get API base URL from environment or default."""
    return os.environ.get("DROWN_API_URL", DEFAULT_API_BASE)


def save_config(token, username):
    """Save authentication config to ~/.drown/config.json."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config = {
        "token": token,
        "username": username,
        "api_base": get_api_base()
    }
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    # Set restrictive permissions (Unix-like systems)
    if hasattr(os, 'chmod'):
        os.chmod(CONFIG_FILE, 0o600)


def load_config():
    """Load authentication config from ~/.drown/config.json."""
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        # Ensure api_base is set (for older config files)
        if "api_base" not in config:
            config["api_base"] = get_api_base()
        
        return config
    except (json.JSONDecodeError, IOError):
        return None


def delete_config():
    """Delete the config file (logout)."""
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        return True
    return False


def get_token():
    """Get the saved auth token, or None if not logged in."""
    config = load_config()
    return config["token"] if config else None


def get_username():
    """Get the saved username, or None if not logged in."""
    config = load_config()
    return config["username"] if config else None
