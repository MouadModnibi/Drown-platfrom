#!/usr/bin/env python3
import sys
sys.path.insert(0, "/home/ubuntu/mini-heroku/control-plane")

import sqlite3
import subprocess
import argparse
from core.docker_ops import get_container_metrics
from core.caddy import regenerate_caddy_config

from core.database import (
    list_apps as db_list_apps,
    get_replicas,
    get_app,
    remove_all_replicas,
    get_configs,
    set_config as db_set_config,
    unset_config as db_unset_config,
)


def list_apps():
    apps = db_list_apps()
    if not apps:
        print("No running apps")
        return

    print("\n📦 Running Apps:")
    print("-" * 60)
    for app_name, domain, status in apps:
        replicas = get_replicas(app_name)
        ports = [str(r[1]) for r in replicas]
        print(f"  {app_name:20} | Replicas: {len(replicas)} | Ports: {','.join(ports)} | {domain}")
    print("-" * 60)


def get_logs(app_name, follow=False):
    replicas = get_replicas(app_name)
    if not replicas:
        print(f"App '{app_name}' not found or has no running replicas")
        return

    replica_num, port, container_id, status = replicas[0]
    container_name = f"{app_name}-{replica_num}"

    cmd = ["docker", "logs", container_name]
    if follow:
        cmd.append("-f")

    result = subprocess.run(cmd, capture_output=not follow, text=True)
    if not follow:
        print(result.stdout)
    if result.returncode != 0:
        print(f"Error retrieving logs for '{container_name}'")


def delete_app(app_name):
    replicas = get_replicas(app_name)
    for replica_num, port, container_id, status in replicas:
        container_name = f"{app_name}-{replica_num}"
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    remove_all_replicas(app_name)
    regenerate_caddy_config()

    print(f"✓ App '{app_name}' deleted ({len(replicas)} replica(s) removed)")


def get_app_info(app_name):
    app = get_app(app_name)
    if not app:
        print(f"App '{app_name}' not found")
        return

    app_name, domain, builder, status = app
    replicas = get_replicas(app_name)

    print(f"\n📋 App Info:")
    print(f"  Name: {app_name}")
    print(f"  Domain: {domain}")
    print(f"  Builder: {builder}")
    print(f"  Status: {status}")
    print(f"  Replicas: {len(replicas)}")
    for replica_num, port, container_id, r_status in replicas:
        print(f"    - {app_name}-{replica_num} | port {port} | {r_status}")
    print()


def get_metrics(app_name):
    replicas = get_replicas(app_name)
    if not replicas:
        print(f"App '{app_name}' not found or not running")
        return

    print(f"\n📊 Metrics for '{app_name}':")
    for replica_num, port, container_id, status in replicas:
        container_name = f"{app_name}-{replica_num}"
        metrics = get_container_metrics(container_name)
        if metrics:
            print(f"  {container_name} | CPU: {metrics['cpu']} | Mem: {metrics['memory']}")
        else:
            print(f"  {container_name} | not running")
    print()


def set_config(app_name, key, value):
    db_set_config(app_name, key, value)
    print(f"✓ Config set: {key}={value}")
    print(f"⚠️  Redeploy app for changes to take effect: git push platform main")


def get_config(app_name, key):
    configs = get_configs(app_name)
    match = dict(configs).get(key)
    if match is None:
        print(f"Config '{key}' not found for app '{app_name}'")
        return
    print(f"{key}={match}")


def list_configs(app_name):
    configs = get_configs(app_name)
    if not configs:
        print(f"No configs set for app '{app_name}'")
        return

    print(f"\n⚙️  Config for '{app_name}':")
    print("-" * 60)
    for key, value in configs:
        print(f"  {key}={value}")
    print("-" * 60)


def unset_config(app_name, key):
    db_unset_config(app_name, key)
    print(f"✓ Config deleted: {key}")
    print(f"⚠️  Redeploy app for changes to take effect: git push platform main")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mini-Heroku Platform CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    subparsers.add_parser('list', help='List all running apps')

    logs_parser = subparsers.add_parser('logs', help='View app logs')
    logs_parser.add_argument('app_name')
    logs_parser.add_argument('-f', '--follow', action='store_true', help='Follow log output')

    delete_parser = subparsers.add_parser('delete', help='Delete an app')
    delete_parser.add_argument('app_name')

    info_parser = subparsers.add_parser('info', help='Get app info')
    info_parser.add_argument('app_name')

    metrics_parser = subparsers.add_parser('metrics', help='Get app CPU/memory metrics')
    metrics_parser.add_argument('app_name')

    config_set_parser = subparsers.add_parser('config:set', help='Set environment variable')
    config_set_parser.add_argument('app_name')
    config_set_parser.add_argument('config', help='KEY=VALUE')

    config_get_parser = subparsers.add_parser('config:get', help='Get environment variable')
    config_get_parser.add_argument('app_name')
    config_get_parser.add_argument('key')

    config_list_parser = subparsers.add_parser('config:list', help='List all configs')
    config_list_parser.add_argument('app_name')

    config_unset_parser = subparsers.add_parser('config:unset', help='Delete config')
    config_unset_parser.add_argument('app_name')
    config_unset_parser.add_argument('key')

    scale_parser = subparsers.add_parser('scale', help='Scale an app to N replicas')
    scale_parser.add_argument('app_name')
    scale_parser.add_argument('count', type=int)

    args = parser.parse_args()

    if args.command == 'list':
        list_apps()
    elif args.command == 'logs':
        get_logs(args.app_name, args.follow)
    elif args.command == 'delete':
        delete_app(args.app_name)
    elif args.command == 'info':
        get_app_info(args.app_name)
    elif args.command == 'metrics':
        get_metrics(args.app_name)
    elif args.command == 'config:set':
        key, value = args.config.split('=', 1)
        set_config(args.app_name, key, value)
    elif args.command == 'config:get':
        get_config(args.app_name, args.key)
    elif args.command == 'config:list':
        list_configs(args.app_name)
    elif args.command == 'config:unset':
        unset_config(args.app_name, args.key)
    elif args.command == 'scale':
        from core.scaler import scale_app
        scale_app(args.app_name, args.app_name, args.count)
        print(f"✓ {args.app_name} scaled to {args.count} replica(s)")
    else:
        parser.print_help()
