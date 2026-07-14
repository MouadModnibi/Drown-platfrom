import subprocess
import socket
import logging
import time
import requests
import shutil
import sys
import sqlite3
import json
import os

DB_PATH = "/home/ubuntu/mini-heroku/apps.db"

BASE_PORT = 4000
MAX_PORT = 5000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def check_command(command):
    if shutil.which(command) is None:
        raise RuntimeError(f"{command} is not installed.")


def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def init_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY,
            app_name TEXT UNIQUE,
            port INTEGER UNIQUE,
            container_id TEXT,
            domain TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def save_app_to_db(app_name, port, container_id, domain):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO apps (app_name, port, container_id, domain, status)
        VALUES (?, ?, ?, ?, 'running')
    ''', (app_name, port, container_id, domain))
    conn.commit()
    conn.close()


def get_free_port():
    result = subprocess.run(["docker", "ps", "--format", "{{.Ports}}"], capture_output=True, text=True)
    used_ports = []
    for line in result.stdout.split('\n'):
        if ':' in line:
            port = line.split('->')[0].split(':')[-1]
            if port.isdigit():
                used_ports.append(int(port))

    for port in range(BASE_PORT, MAX_PORT):
        if port not in used_ports:
            return port
    raise RuntimeError("No available ports")


# -------------------------------------------------
# Build
# -------------------------------------------------

def build_image(app_name, repo_path):
    logging.info("Building image...")

    run_command([
        "pack",
        "build",
        app_name,
        "--builder",
        "heroku/builder:24",
        "--path",
        repo_path
    ])

    logging.info("Image built successfully.")


# -------------------------------------------------
# Cleanup
# -------------------------------------------------

def stop_old_container(app_name):
    logging.info("Removing old container (if exists)...")

    subprocess.run(
        ["docker", "rm", "-f", app_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# -------------------------------------------------
# Run
# -------------------------------------------------

def run_container(app_name, port):
    logging.info(f"Starting container on port {port}")

    # Get environment variables from database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, value FROM app_configs WHERE app_name=?', (app_name,))
    configs = c.fetchall()
    conn.close()
    
    # Build docker run command with env vars
    cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        app_name,
        "-p",
        f"{port}:8080",
    ]
    
    # Add all environment variables
    for key, value in configs:
        cmd.extend(["-e", f"{key}={value}"])
    
    cmd.append(app_name)
    
    container_id = run_command(cmd)

    logging.info(f"Container started: {container_id}")
    logging.info(f"Environment variables: {len(configs)} config(s) set")

    return container_id


# -------------------------------------------------
# Health Check
# -------------------------------------------------

def wait_until_ready(port):
    logging.info("Waiting for application...")

    for attempt in range(20):
        try:
            r = requests.get(
                f"http://localhost:{port}",
                timeout=2
            )

            if r.status_code < 500:
                logging.info("Application is ready.")
                return

        except requests.exceptions.RequestException as e:
            logging.debug(f"Health check attempt {attempt+1}/20 failed: {e}")

        time.sleep(2)

    raise RuntimeError("Application failed health check after 40 seconds.")


# -------------------------------------------------
# Caddy Routing
# -------------------------------------------------

def regenerate_caddy_config():
    """Regenerate entire Caddyfile from database"""
    logging.info("Regenerating Caddy config from database...")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT app_name, port, domain FROM apps WHERE status="running"')
    apps = c.fetchall()
    conn.close()
    
    caddyfile_path = "/etc/caddy/Caddyfile"
    content = ""
    
    for app_name, port, domain in apps:
        content += f"""
{domain} {{
    reverse_proxy localhost:{port}
}}
"""
    
    with open(caddyfile_path, "w") as f:
        f.write(content)
    
    subprocess.run(["sudo", "systemctl", "reload", "caddy"], check=True)
    logging.info("Caddy config regenerated successfully")


# -------------------------------------------------
# Deployment
# -------------------------------------------------

def deploy(app_name, repo_path):
    check_command("docker")
    check_command("pack")

    init_database()
    port = get_free_port()

    # Check for custom domain config
    custom_domain = "massar.duckdns.org"  # default
    config_file = f"{repo_path}/mini-heroku.json"
    
    try:
        if os.path.exists(config_file):
            with open(config_file) as f:
                config = json.load(f)
                if "domain" in config:
                    custom_domain = config["domain"]
                    logging.info(f"Custom domain found: {custom_domain}")
    except Exception as e:
        logging.warning(f"Could not read config file: {e}")

    build_image(app_name, repo_path)
    stop_old_container(app_name)
    container_id = run_container(app_name, port)
    wait_until_ready(port)
    
    save_app_to_db(app_name, port, container_id, custom_domain)
    regenerate_caddy_config()

    deployment = {
        "application": app_name,
        "container_id": container_id,
        "port": port,
        "domain": custom_domain,
        "status": "running"
    }

    logging.info(deployment)

    return deployment


# -------------------------------------------------
# Main
# -------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage:")
        print("python3 control_plane.py <app_name> <repo_path>")
        sys.exit(1)

    try:

        deployment = deploy(
            sys.argv[1],
            sys.argv[2]
        )

        print("\nDeployment Successful")
        print("----------------------")

        for key, value in deployment.items():
            print(f"{key}: {value}")

    except Exception as e:

        logging.error(e)
        sys.exit(1)
