import subprocess
import time
import requests
import logging

from core.config import BASE_PORT, MAX_PORT, DEFAULT_BUILDER
from core.database import get_used_ports


def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def get_free_port():
    used_ports = set(get_used_ports())

    # Also check actual Docker containers, not just DB
    result = subprocess.run(["docker", "ps", "-a", "--format", "{{.Ports}}"],
                             capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if '->' in line:
            port = line.split('->')[0].split(':')[-1]
            if port.isdigit():
                used_ports.add(int(port))

    for port in range(BASE_PORT, MAX_PORT):
        if port not in used_ports:
            return port
    raise RuntimeError("No available ports")


def build_image(app_name, repo_path, builder=DEFAULT_BUILDER):
    logging.info(f"Building image for {app_name}...")
    try:
        run_command(["pack", "build", app_name, "--builder", builder, "--path", repo_path])
    except RuntimeError as e:
        raise RuntimeError(
            f"Build failed for '{app_name}'.\n"
            f"Details: {str(e)[-500:]}\n\n"
            f"Common causes:\n"
            f"  - Missing or invalid package.json / requirements.txt\n"
            f"  - No recognizable start command for your language/framework\n"
            f"  - For frontend frameworks (React/Vite/Expo web): you likely "
            f"need a 'serve' package + a 'heroku-postbuild' build step"
        ) from e
    logging.info("Image built successfully.")


def stop_container(container_name):
    subprocess.run(["docker", "rm", "-f", container_name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def run_container(image_name, container_name, port, env_vars=None):
    logging.info(f"Starting container {container_name} on port {port}")
    
    subprocess.run(["docker", "rm", "-f", container_name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cmd = ["docker", "run", "-d", "--name", container_name, "-p", f"{port}:8080"]

    for key, value in (env_vars or []):
        cmd.extend(["-e", f"{key}={value}"])

    cmd.append(image_name)

    container_id = run_command(cmd)
    logging.info(f"Container started: {container_id}")
    return container_id


def wait_until_ready(port, container_name=None, retries=20, delay=2):
    logging.info("Waiting for application...")
    for attempt in range(retries):
        try:
            r = requests.get(f"http://localhost:{port}", timeout=2)
            if r.status_code < 500:
                logging.info("Application is ready.")
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(delay)

    log_snippet = ""
    if container_name:
        try:
            logs = get_container_logs(container_name, follow=False)
            log_snippet = "\n".join(logs.strip().split("\n")[-15:])
        except Exception:
            log_snippet = "(could not retrieve logs)"

    raise RuntimeError(
        f"Application failed health check after {retries * delay} seconds "
        f"(no response on port 8080).\n\n"
        f"Last container logs:\n{log_snippet}\n\n"
        f"Common causes:\n"
        f"  - App is running a DEV server instead of a production server "
        f"(e.g. 'npm start' running react-scripts/expo/vite dev mode)\n"
        f"  - App isn't binding to port 8080 (check your Procfile/start script)\n"
        f"  - Missing dependency (Flask/gunicorn, serve, etc.)"
    )


def get_container_metrics(container_name):
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}|{{.MemUsage}}", container_name],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    cpu, mem = result.stdout.strip().split('|')
    return {"cpu": cpu, "memory": mem}

def get_multiple_container_metrics(container_names):
    """Get CPU/memory for multiple containers in a single docker call.
    container_names here are actually full container_id hashes from the DB;
    we match them against docker's short ID output."""
    if not container_names:
        return {}

    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", "{{.ID}}|{{.CPUPerc}}|{{.MemUsage}}"] + container_names,
        capture_output=True, text=True
    )

    short_id_metrics = {}
    if result.returncode == 0:
        for line in result.stdout.strip().split('\n'):
            if '|' in line:
                short_id, cpu, mem = line.split('|')
                short_id_metrics[short_id] = {"cpu": cpu, "memory": mem}

    # Map back to full container_id hashes by prefix match
    full_id_metrics = {}
    for full_id in container_names:
        short_id = full_id[:12]
        if short_id in short_id_metrics:
            full_id_metrics[full_id] = short_id_metrics[short_id]

    return full_id_metrics

def get_container_logs(container_name, follow=False):
    cmd = ["docker", "logs", container_name]
    if follow:
        cmd.append("-f")
    result = subprocess.run(cmd, capture_output=not follow, text=True)
    if follow:
        return None
    # docker logs can write to stdout AND stderr — combine both
    return result.stdout + result.stderr
