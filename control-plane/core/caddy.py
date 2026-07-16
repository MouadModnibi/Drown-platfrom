import subprocess
import logging

from core.config import CADDYFILE_PATH
from core.database import list_apps, get_replicas, get_app


def regenerate_caddy_config():
    logging.info("Regenerating Caddy config...")

    content = "import /etc/caddy/Caddyfile.dashboard\n"

    for app_name, domain, status in list_apps():
        if status != "running":
            continue

        replicas = get_replicas(app_name)
        running_ports = [port for _, port, _, status in replicas if status == "running"]

        if not running_ports:
            continue

        upstreams = " ".join(f"localhost:{p}" for p in running_ports)

        content += f"""
{domain} {{
    reverse_proxy {upstreams}
}}
"""

    if not content.strip():
        # No apps running — write a minimal valid empty config
        content = "# no apps deployed\n"

    with open(CADDYFILE_PATH, "w") as f:
        f.write(content)

    subprocess.run(["sudo", "systemctl", "reload", "caddy"], check=True)
    logging.info("Caddy config reloaded.")
