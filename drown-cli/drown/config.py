"""Configuration management for Drown CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path

# Default API base URL
DEFAULT_API_BASE = "https://api.dr0wn.duckdns.org"

# Config file location
CONFIG_DIR = Path.home() / ".drown"
CONFIG_FILE = CONFIG_DIR / "config.json"

# SSH key locations
SSH_PRIVATE_KEY = CONFIG_DIR / "id_ed25519"
SSH_PUBLIC_KEY = CONFIG_DIR / "id_ed25519.pub"


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


def generate_ssh_key():
    """
    Generate a new ed25519 SSH key pair for drown platform.
    
    Returns: (success: bool, message: str)
    """
    # Ensure config directory exists
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if key already exists
    if SSH_PRIVATE_KEY.exists() and SSH_PUBLIC_KEY.exists():
        return True, "existing"
    
    # Check if ssh-keygen is available
    try:
        subprocess.run(
            ["ssh-keygen", "-V"],
            capture_output=True,
            check=False
        )
    except FileNotFoundError:
        return False, "ssh-keygen not found. Please install OpenSSH or Git for Windows."
    
    # Generate key
    try:
        result = subprocess.run(
            [
                "ssh-keygen",
                "-t", "ed25519",
                "-f", str(SSH_PRIVATE_KEY),
                "-N", "",  # Empty passphrase
                "-C", "drown-platform-key"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Set correct permissions on private key (Unix only)
        if hasattr(os, 'chmod'):
            os.chmod(SSH_PRIVATE_KEY, 0o600)
        
        return True, "generated"
        
    except subprocess.CalledProcessError as e:
        return False, f"Failed to generate SSH key: {e.stderr}"


def read_public_key():
    """
    Read the public key file.
    
    Returns: public key content as string, or None if not found
    """
    if not SSH_PUBLIC_KEY.exists():
        return None
    
    try:
        with open(SSH_PUBLIC_KEY, 'r') as f:
            return f.read().strip()
    except IOError:
        return None


def update_ssh_config():
    """
    Safely update ~/.ssh/config to add/update the drown-platform host entry.
    
    Returns: (success: bool, message: str)
    """
    ssh_dir = Path.home() / ".ssh"
    config_path = ssh_dir / "config"
    identity_file = str(SSH_PRIVATE_KEY).replace('\\', '/')  # Use forward slashes for cross-platform
    
    # Ensure .ssh directory exists with correct permissions
    try:
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
    except Exception as e:
        return False, f"Failed to create .ssh directory: {e}"
    
    # Our desired config block
    drown_config = [
        "Host drown-platform",
        "    HostName 51.170.134.251",
        "    User ubuntu",
        f"    IdentityFile {identity_file}",
        "    IdentitiesOnly yes"
    ]
    
    # Read existing config
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                lines = f.readlines()
        except IOError as e:
            return False, f"Failed to read SSH config: {e}"
    else:
        lines = []
    
    # Parse: find if "Host drown-platform" exists
    drown_start = None
    drown_end = None
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Found start of our block
        if stripped.startswith("Host ") and "drown-platform" in stripped:
            drown_start = i
            
            # Find end of this Host block (next "Host" line or EOF)
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith("Host "):
                    drown_end = j
                    break
            else:
                drown_end = len(lines)
            break
    
    # Reconstruct config
    new_lines = []
    
    if drown_start is not None:
        # Replace existing drown-platform block
        new_lines.extend(lines[:drown_start])
        new_lines.extend([line + "\n" for line in drown_config])
        new_lines.append("\n")
        new_lines.extend(lines[drown_end:])
    else:
        # Append to end
        new_lines = lines
        
        # Ensure blank line before our block if file isn't empty
        if new_lines and not new_lines[-1].strip() == "":
            new_lines.append("\n")
        
        new_lines.extend([line + "\n" for line in drown_config])
        new_lines.append("\n")
    
    # Write atomically
    temp_path = config_path.with_suffix('.tmp')
    try:
        with open(temp_path, 'w') as f:
            f.writelines(new_lines)
        
        # Set permissions before rename (Unix only)
        if hasattr(os, 'chmod'):
            os.chmod(temp_path, 0o600)
        
        # Atomic rename
        temp_path.replace(config_path)
        
    except IOError as e:
        # Clean up temp file if it exists
        if temp_path.exists():
            temp_path.unlink()
        return False, f"Failed to write SSH config: {e}"
    
    # Verification step: read back and confirm
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Check that our Host block is present
        if "Host drown-platform" not in content:
            return False, "Verification failed: Host block not found after write"
        
        if "HostName 51.170.134.251" not in content:
            return False, "Verification failed: HostName not found after write"
        
        if identity_file not in content and str(SSH_PRIVATE_KEY) not in content:
            return False, "Verification failed: IdentityFile not found after write"
        
    except IOError as e:
        return False, f"Verification failed: Could not read back config: {e}"
    
    return True, "SSH config updated successfully"


def setup_ssh_key(username, token):
    """
    Complete SSH key setup: generate key, register with platform, update SSH config.
    
    Returns: (success: bool, messages: list of str)
    """
    from drown import api
    
    messages = []
    
    # Step 1: Generate or verify SSH key exists
    success, msg = generate_ssh_key()
    if not success:
        return False, [f"✗ {msg}"]
    
    if msg == "existing":
        messages.append("✓ Using existing SSH key")
    else:
        messages.append("✓ Generated SSH key")
    
    # Step 2: Read public key
    public_key = read_public_key()
    if not public_key:
        return False, messages + ["✗ Failed to read public key file"]
    
    # Step 3: Register key with platform
    success, result = api.register_ssh_key(token, public_key)
    if not success:
        error_msg = result.get('error', 'Unknown error')
        # Don't fail completely - user is still logged in for API operations
        messages.append(f"⚠ Failed to register SSH key: {error_msg}")
        messages.append("  You can still use 'drown apps', 'drown scale', etc.")
        messages.append("  Git push may require manual SSH configuration.")
        return True, messages  # Partial success
    
    messages.append("✓ Registered key with platform")
    
    # Step 4: Update SSH config
    success, msg = update_ssh_config()
    if not success:
        messages.append(f"⚠ SSH config update failed: {msg}")
        messages.append("  Git push may require manual configuration.")
        return True, messages  # Partial success
    
    messages.append("✓ SSH config updated — 'git push platform main' will work automatically")
    
    return True, messages
