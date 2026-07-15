import os
import json
import logging

from core.config import DEFAULT_DOMAIN, DEFAULT_BUILDER
from core.database import init_database, upsert_app, log_deployment, get_replicas
from core.docker_ops import build_image
from core.scaler import scale_app


def deploy(app_name, repo_path):
    init_database()

    custom_domain = f"{app_name}.{DEFAULT_DOMAIN}"
    config_file = os.path.join(repo_path, "mini-heroku.json")

    try:
        if os.path.exists(config_file):
            with open(config_file) as f:
                config = json.load(f)
                if "domain" in config:
                    custom_domain = config["domain"]
    except Exception as e:
        logging.warning(f"Could not read config file: {e}")

    try:
        build_image(app_name, repo_path, DEFAULT_BUILDER)
        upsert_app(app_name, custom_domain, DEFAULT_BUILDER)

        # Keep same replica count as before, or 1 if first deploy
        existing_replicas = get_replicas(app_name)
        target_count = len(existing_replicas) if existing_replicas else 1

        scale_app(app_name, app_name, target_count)

        log_deployment(app_name, "success", f"Deployed with {target_count} replica(s)")

        return {
            "application": app_name,
            "domain": custom_domain,
            "replicas": target_count,
            "status": "running"
        }

    except Exception as e:
        log_deployment(app_name, "failed", str(e))
        raise
