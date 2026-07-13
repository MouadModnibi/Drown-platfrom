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
    # Remove container
    subprocess.run(["docker", "rm", "-f", app_name], capture_output=True)
    
    # Remove from database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM apps WHERE app_name=?', (app_name,))
    conn.commit()
    conn.close()
    
    # Regenerate Caddy
    subprocess.run(["python3", "/home/ubuntu/mini-heroku/control-plane/control_plane.py", "--regenerate-caddy"], capture_output=True)
    
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Mini-Heroku Platform CLI')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # list command
    subparsers.add_parser('list', help='List all running apps')
    
    # logs command
    logs_parser = subparsers.add_parser('logs', help='View app logs')
    logs_parser.add_argument('app_name')
    logs_parser.add_argument('-f', '--follow', action='store_true', help='Follow log output')
    
    # delete command
    delete_parser = subparsers.add_parser('delete', help='Delete an app')
    delete_parser.add_argument('app_name')
    
    # info command
    info_parser = subparsers.add_parser('info', help='Get app info')
    info_parser.add_argument('app_name')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_apps()
    elif args.command == 'logs':
        get_logs(args.app_name, args.follow)
    elif args.command == 'delete':
        delete_app(args.app_name)
    elif args.command == 'info':
        get_app_info(args.app_name)
    else:
        parser.print_help()
