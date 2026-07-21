"""CLI commands for Drown Platform."""

import click
import getpass
import subprocess
import sys
from pathlib import Path

from drown import api, config, __version__


@click.group()
@click.version_option(version=__version__, prog_name="drown")
def cli():
    """Drown Platform CLI - Manage your self-hosted PaaS."""
    pass


@cli.command()
def login():
    """Login to Drown Platform."""
    click.echo("Login to Drown Platform")
    click.echo(f"API: {config.get_api_base()}\n")
    
    username = click.prompt("Username")
    password = getpass.getpass("Password: ")
    
    click.echo("\nAuthenticating...")
    
    success, result = api.login(username, password)
    
    if success:
        token = result.get("token")
        username = result.get("username")
        
        config.save_config(token, username)
        
        click.secho(f"✓ Logged in as {username}", fg="green")
        
        # SSH key setup
        click.echo("\nSetting up SSH key for git push...")
        ssh_success, ssh_messages = config.setup_ssh_key(username, token)
        
        for message in ssh_messages:
            if message.startswith("✓"):
                click.secho(message, fg="green")
            elif message.startswith("⚠"):
                click.secho(message, fg="yellow")
            elif message.startswith("✗"):
                click.secho(message, fg="red", err=True)
            else:
                click.echo(message)
        
    else:
        click.secho(f"✗ Login failed: {result.get('error')}", fg="red", err=True)
        sys.exit(1)


@cli.command()
def logout():
    """Logout and remove saved credentials."""
    if config.delete_config():
        click.secho("✓ Logged out successfully", fg="green")
        click.echo(f"Removed {config.CONFIG_FILE}")
    else:
        click.echo("Not logged in")


@cli.command()
def apps():
    """List all your apps."""
    token = config.get_token()
    if not token:
        click.secho("✗ Please run 'drown login' first", fg="red", err=True)
        sys.exit(1)
    
    success, result = api.get_apps(token)
    
    if not success:
        click.secho(f"✗ Error: {result.get('error')}", fg="red", err=True)
        sys.exit(1)
    
    apps_list = result.get("apps", [])
    
    if not apps_list:
        click.echo("No apps found. Create one with 'drown create <app-name>'")
        return
    
    # Print table header
    click.echo(f"{'NAME':<20} {'DOMAIN':<35} {'STATUS':<10} {'REPLICAS':<8}")
    click.echo("-" * 75)
    
    # Print each app
    for app in apps_list:
        name = app.get("name", "")
        domain = app.get("domain", "N/A")
        status = app.get("status", "unknown")
        replicas = app.get("replicas", 0)
        
        # Color code status
        if status == "running":
            status_colored = click.style(status, fg="green")
        elif status == "stopped":
            status_colored = click.style(status, fg="red")
        else:
            status_colored = status
        
        click.echo(f"{name:<20} {domain:<35} {status_colored:<10} {replicas:<8}")


@cli.command()
@click.argument("app_name")
def create(app_name):
    """Create a new app."""
    token = config.get_token()
    if not token:
        click.secho("✗ Please run 'drown login' first", fg="red", err=True)
        sys.exit(1)
    
    click.echo(f"Creating app '{app_name}'...")
    
    success, result = api.create_app(token, app_name)
    
    if not success:
        error = result.get('error', '')
        
        # If app already exists, try linking instead
        if 'already' in error.lower() or 'exists' in error.lower():
            click.echo(f"App '{app_name}' already exists, linking to it...")
            success, result = api.link_app(token, app_name)
            
            if not success:
                click.secho(f"✗ Error: {result.get('error')}", fg="red", err=True)
                sys.exit(1)
        else:
            click.secho(f"✗ Error: {error}", fg="red", err=True)
            sys.exit(1)
    
    domain = result.get("domain", "N/A")
    git_remote_raw = result.get("git_remote")
    
    # Convert git remote to use drown-platform host alias
    # Original: ssh://ubuntu@51.170.134.251/home/ubuntu/git-hook-test/<app>.git
    # New: ssh://ubuntu@drown-platform/home/ubuntu/git-hook-test/<app>.git
    git_remote = git_remote_raw
    if git_remote_raw and "51.170.134.251" in git_remote_raw:
        git_remote = git_remote_raw.replace("51.170.134.251", "drown-platform")
    
    click.secho(f"✓ App '{app_name}' ready!", fg="green")
    click.echo(f"Domain: {domain}")
    
    # Check if we're in a git repo
    git_dir = Path(".git")
    if git_dir.exists() and git_remote:
        click.echo("\nAdding git remote 'platform'...")
        
        try:
            # Check if remote already exists
            result_check = subprocess.run(
                ["git", "remote", "get-url", "platform"],
                capture_output=True,
                text=True
            )
            
            if result_check.returncode == 0:
                click.secho("⚠ Remote 'platform' already exists. Skipping.", fg="yellow")
            else:
                # Add the remote
                subprocess.run(
                    ["git", "remote", "add", "platform", git_remote],
                    check=True,
                    capture_output=True
                )
                click.secho(f"✓ Git remote 'platform' added", fg="green")
        except subprocess.CalledProcessError as e:
            click.secho(f"⚠ Failed to add git remote: {e}", fg="yellow")
        except FileNotFoundError:
            click.secho("⚠ Git not found. Please install git to use auto-remote feature.", fg="yellow")
    
    # Print deployment instructions
    click.echo(f"\nTo deploy, push your code:")
    click.echo(f"  git push platform main")


@cli.command()
@click.argument("app_name")
@click.argument("count", type=int)
def scale(app_name, count):
    """Scale an app to COUNT replicas."""
    token = config.get_token()
    if not token:
        click.secho("✗ Please run 'drown login' first", fg="red", err=True)
        sys.exit(1)
    
    if count < 0:
        click.secho("✗ Replica count must be non-negative", fg="red", err=True)
        sys.exit(1)
    
    click.echo(f"Scaling '{app_name}' to {count} replica(s)...")
    
    success, result = api.scale_app(token, app_name, count)
    
    if not success:
        click.secho(f"✗ Error: {result.get('error')}", fg="red", err=True)
        sys.exit(1)
    
    new_count = result.get("replicas", count)
    click.secho(f"✓ Scaled '{app_name}' to {new_count} replica(s)", fg="green")


@cli.command()
@click.argument("app_name")
def logs(app_name):
    """View logs for an app."""
    token = config.get_token()
    if not token:
        click.secho("✗ Please run 'drown login' first", fg="red", err=True)
        sys.exit(1)
    
    success, result = api.get_logs(token, app_name)
    
    if not success:
        click.secho(f"✗ Error: {result.get('error')}", fg="red", err=True)
        sys.exit(1)
    
    logs_text = result.get("logs", "")
    
    if logs_text:
        click.echo(logs_text)
    else:
        click.echo("No logs available")


@cli.command()
@click.argument("app_name")
def metrics(app_name):
    """View resource metrics for an app."""
    token = config.get_token()
    if not token:
        click.secho("✗ Please run 'drown login' first", fg="red", err=True)
        sys.exit(1)
    
    success, result = api.get_metrics(token, app_name)
    
    if not success:
        click.secho(f"✗ Error: {result.get('error')}", fg="red", err=True)
        sys.exit(1)
    
    replicas = result.get("replicas", [])
    
    if not replicas:
        click.echo(f"No replicas found for '{app_name}'")
        return
    
    # Print table header
    click.echo(f"{'REPLICA':<10} {'PORT':<8} {'STATUS':<10} {'CPU':<10} {'MEMORY':<15}")
    click.echo("-" * 55)
    
    # Print each replica
    for replica in replicas:
        replica_num = replica.get("replica_num", "?")
        port = replica.get("port", "N/A")
        status = replica.get("status", "unknown")
        cpu = replica.get("cpu", "N/A")
        memory = replica.get("memory", "N/A")
        
        # Color code status
        if status == "running":
            status_colored = click.style(status, fg="green")
        elif status == "stopped":
            status_colored = click.style(status, fg="red")
        else:
            status_colored = status
        
        click.echo(f"{replica_num:<10} {port:<8} {status_colored:<10} {cpu:<10} {memory:<15}")


if __name__ == "__main__":
    cli()
