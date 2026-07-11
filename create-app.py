#!/usr/bin/env python3
import os
import subprocess
import sys

REPOS_DIR = "/home/ubuntu/git-hook-test"
HOOK_SOURCE = f"{REPOS_DIR}/test-repo.git/hooks/post-receive"

def create_app(app_name):
    repo_path = f"{REPOS_DIR}/{app_name}.git"
    
    # Create bare repo
    os.makedirs(repo_path, exist_ok=True)
    subprocess.run(["git", "init", "--bare", repo_path], check=True)
    
    # Copy hook
    hook_dest = f"{repo_path}/hooks/post-receive"
    subprocess.run(["cp", HOOK_SOURCE, hook_dest], check=True)
    subprocess.run(["chmod", "+x", hook_dest], check=True)
    
    # Output connection string
    ssh_url = f"ssh://ubuntu@51.170.134.251{repo_path}"
    print(f"\n✓ App '{app_name}' created successfully!")
    print(f"Push with: git remote add platform {ssh_url}")
    print(f"Access at: https://{app_name}.massar.duckdns.org\n")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 create-app.py <app-name>")
        sys.exit(1)
    
    create_app(sys.argv[1])
