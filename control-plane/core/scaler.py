import logging
import os

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

    while len(get_replicas(app_name)) < desired_count:
        port = get_free_port()
        container_name = f"{app_name}-{next_num}"

        container_id = run_container(image_name, container_name, port, env_vars)

        try:
            wait_until_ready(port, container_name=container_name)
        except Exception as e:
            logging.error(f"Health check failed for {container_name}, cleaning up: {e}")
            stop_container(container_name)
            raise RuntimeError(
                f"Deployment failed: '{app_name}' did not respond on port 8080 "
                f"within the expected time. The container has been removed."
            ) from e

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

def redeploy_replicas(app_name, image_name):
    current = get_replicas(app_name)
    env_vars = get_configs(app_name)

    if not current:
        scale_app(app_name, image_name, 1)
        return

    for replica_num, old_port, old_container_id, status in current:
        old_container_name = f"{app_name}-{replica_num}"
        new_container_name = f"{app_name}-{replica_num}-new"

        # Start the new version on a temporary port
        new_port = get_free_port()

        new_container_id = run_container(
            image_name,
            new_container_name,
            new_port,
            env_vars,
        )

        try:
            wait_until_ready(new_port)
        except Exception as e:
            logging.error(
                f"Rolling deploy failed for replica {replica_num}: {e}"
            )
            stop_container(new_container_name)
            raise RuntimeError(
                f"Deploy failed: replica {replica_num} failed health check."
            ) from e

        #
        # Traffic switch
        #

        # Update database to point this replica to the NEW port
        add_replica(app_name, replica_num, new_port, new_container_id)

        # Regenerate + reload Caddy
        regenerate_caddy_config()
            # implement this if you don't already have it

        #
        # Safe to remove old container now
        #

        stop_container(old_container_name)

        subprocess.run(
            ["docker", "rename", new_container_name, old_container_name],
            check=True,
        )

        logging.info(
            f"✓ Replica {replica_num} updated with zero downtime"
        )

def delete_app(app_name):
    """
    Delete an app completely: stop containers, remove all DB records, regenerate caddy.
    
    Args:
        app_name: str - name of app to delete
        
    Returns:
        tuple: (success: bool, replica_count: int, message: str)
    """
    import subprocess
    from core.database import get_replicas, remove_app
    
    # Get replicas before deletion
    replicas = get_replicas(app_name)
    replica_count = len(replicas)
    
    # Stop and remove each container
    for replica_num, port, container_id, status in replicas:
        container_name = f"{app_name}-{replica_num}"
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
    
    # Remove ALL database records: replicas, configs, deployments, app row
    remove_app(app_name)
    
    # Remove the bare git repository from disk
    import shutil
    repo_path = f"/home/ubuntu/git-hook-test/{app_name}.git"
    if os.path.exists(repo_path):
        shutil.rmtree(repo_path)
    
    # Regenerate Caddy config
    regenerate_caddy_config()
    
    return True, replica_count, f"App '{app_name}' deleted ({replica_count} replica(s) removed)"
