#!/usr/bin/env python3
import sqlite3
import subprocess
import argparse
import sys

DB_PATH = "/home/ubuntu/mini-heroku/apps.db"

def list_apps():
    """List all running apps"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT app_name, port, domain, status FROM apps WHERE status="running"')
    apps = c.fetchall()
    conn.close()
    
    if not apps:
        print("No running apps")
        return
    
    print("\n📦 Running Apps:")
    print("-" * 60)
    for app_name, port, domain, status in apps:
        print(f"  {app_name:20} | Port: {port:5} | {domain}")
    print("-" * 60)

def get_logs(app_name, follow=False):
    """Get logs from an app"""
    cmd = ["docker", "logs", app_name]
    if follow:
        cmd.append("-f")
    
    result = subprocess.run(cmd, capture_output=not follow, text=True)
    if not follow:
        print(result.stdout)
    
    if result.returncode != 0:
        print(f"Error: App '{app_name}' not found or error retrieving logs")

def delete_app(app_name):
    """Delete an app"""
    subprocess.run(["docker", "rm", "-f", app_name], capture_output=True)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM apps WHERE app_name=?', (app_name,))
    conn.commit()
    conn.close()
    
    print(f"✓ App '{app_name}' deleted")

def get_app_info(app_name):
    """Get info about one app"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT app_name, port, domain, container_id, status FROM apps WHERE app_name=?', (app_name,))
    app = c.fetchone()
    conn.close()
    
    if not app:
        print(f"App '{app_name}' not found")
        return
    
    app_name, port, domain, container_id, status = app
    print(f"\n📋 App Info:")
    print(f"  Name: {app_name}")
    print(f"  Domain: {domain}")
    print(f"  Port: {port}")
    print(f"  Container ID: {container_id}")
    print(f"  Status: {status}\n")

def set_config(app_name, key, value):
    """Set environment variable for an app"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO app_configs (app_name, key, value)
        VALUES (?, ?, ?)
    ''', (app_name, key, value))
    conn.commit()
    conn.close()
    
    print(f"✓ Config set: {key}={value}")
    print(f"⚠️  Redeploy app for changes to take effect: git push platform main")

def get_config(app_name, key):
    """Get one environment variable"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT value FROM app_configs WHERE app_name=? AND key=?', (app_name, key))
    result = c.fetchone()
    conn.close()
    
    if not result:
        print(f"Config '{key}' not found for app '{app_name}'")
        return
    
    print(f"{key}={result[0]}")

def list_configs(app_name):
    """List all environment variables for an app"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT key, value FROM app_configs WHERE app_name=?', (app_name,))
    configs = c.fetchall()
    conn.close()
    
    if not configs:
        print(f"No configs set for app '{app_name}'")
        return
    
    print(f"\n⚙️  Config for '{app_name}':")
    print("-" * 60)
    for key, value in configs:
        print(f"  {key}={value}")
    print("-" * 60)

def unset_config(app_name, key):
    """Delete an environment variable"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM app_configs WHERE app_name=? AND key=?', (app_name, key))
    conn.commit()
    conn.close()
    
    print(f"✓ Config deleted: {key}")
    print(f"⚠️  Redeploy app for changes to take effect: git push platform main")
     

def get_metrics(app_name):
    """Get CPU and memory metrics for an app"""
    result = subprocess.run(
        ["docker", "stats", "--no-stream", "--format", 
         "{{.CPUPerc}}|{{.MemUsage}}", app_name],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Error: App '{app_name}' not found or not running")
        return
    
    cpu, mem = result.stdout.strip().split('|')
    print(f"\n📊 Metrics for '{app_name}':")
    print(f"  CPU: {cpu}")
    print(f"  Memory: {mem}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mini-Heroku Platform CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
	# metrics command
    metrics_parser = subparsers.add_parser('metrics', help='Get app CPU/memory metrics')
    metrics_parser.add_argument('app_name')
    
    subparsers.add_parser('list', help='List all running apps')
    
    logs_parser = subparsers.add_parser('logs', help='View app logs')
    logs_parser.add_argument('app_name')
    logs_parser.add_argument('-f', '--follow', action='store_true', help='Follow log output')
    
    delete_parser = subparsers.add_parser('delete', help='Delete an app')
    delete_parser.add_argument('app_name')
    
    info_parser = subparsers.add_parser('info', help='Get app info')
    info_parser.add_argument('app_name')
    
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
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_apps()
    elif args.command == 'logs':
        get_logs(args.app_name, args.follow)
    elif args.command == 'delete':
        delete_app(args.app_name)
    elif args.command == 'info':
        get_app_info(args.app_name)
    elif args.command == 'config:set':
        key, value = args.config.split('=', 1)
        set_config(args.app_name, key, value)
    elif args.command == 'config:get':
        get_config(args.app_name, args.key)
    elif args.command == 'config:list':
        list_configs(args.app_name)
    elif args.command == 'config:unset':
        unset_config(args.app_name, args.key)
    elif args.command == 'metrics':
        get_metrics(args.app_name)
    else:
        parser.print_help()
