import logging

from core.config import MAX_REPLICAS_PER_APP
from core.database import get_replicas, add_replica, remove_replica, get_configs
from core.docker_ops import get_free_port, run_container, stop_container, wait_until_ready
from core.caddy import regenerate_caddy_config


def scale_app(app_name, image_name, desired_count):
    if desired_count > MAX_REPLICAS_PER_APP:
        raise ValueError(f"Cannot scale above {MAX_REPLICAS_PER_APP} replicas")

    current = get_replicas(app_name)
    current_count = len(current)

    if desired_count > current_count:
        _scale_up(app_name, image_name, current, desired_count)
    elif desired_count < current_count:
        _scale_down(app_name, current, desired_count)
    else:
        logging.info(f"{app_name} already at {desired_count} replicas.")

    regenerate_caddy_config()


def _scale_up(app_name, image_name, current, desired_count):
    env_vars = get_configs(app_name)
    existing_nums = [r[0] for r in current]
    next_num = max(existing_nums, default=0) + 1

    while len(existing_nums) + 1 <= desired_count if False else len(get_replicas(app_name)) < desired_count:
        port = get_free_port()
        container_name = f"{app_name}-{next_num}"

        container_id = run_container(image_name, container_name, port, env_vars)
        wait_until_ready(port)

        add_replica(app_name, next_num, port, container_id)
        logging.info(f"✓ Replica {next_num} created for {app_name} on port {port}")

        next_num += 1


def _scale_down(app_name, current, desired_count):
    # Keep the lowest replica numbers, remove the highest ones
    sorted_replicas = sorted(current, key=lambda r: r[0])  # by replica_num
    to_remove = sorted_replicas[desired_count:]

    for replica_num, port, container_id, status in to_remove:
        container_name = f"{app_name}-{replica_num}"
        stop_container(container_name)
        remove_replica(app_name, replica_num)
        logging.info(f"✓ Replica {replica_num} removed for {app_name}")
