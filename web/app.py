import sys
import re
import subprocess
import os
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, jsonify, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
import math

# Add parent directory to path to import from control-plane
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'control-plane'))

from core import database, docker_ops

app = Flask(__name__)

# Secret key management - persisted to survive restarts
SECRET_KEY_FILE = os.path.join(os.path.dirname(__file__), '.secret_key')
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'r') as f:
        app.secret_key = f.read().strip()
else:
    app.secret_key = secrets.token_hex(32)
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(app.secret_key)


# Auth decorator and helpers
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current logged-in user info from session."""
    user_id = session.get('user_id')
    if user_id:
        user_data = database.get_user_by_id(user_id)
        if user_data:
            return {'id': user_data[0], 'username': user_data[1]}
    return None

def get_user_from_token():
    """Verify the Authorization header token and return the user, or None."""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.replace('Bearer ', '', 1)
    user = database.get_user_by_token(token)
    if user:
        return {'id': user[0], 'username': user[1]}
    return None

def can_access_app(user, app_name):
    """
    Check if user can access an app (owns it OR is admin).
    Works with BOTH session-based and token-based user dicts.
    
    Args:
        user: dict with 'id' key (from get_current_user() OR get_user_from_token())
        app_name: str
        
    Returns:
        tuple: (can_access: bool, owner_id: int|None, reason: str)
    """
    if not user:
        return False, None, "unauthorized"
    
    owner_id = database.get_app_owner(app_name)
    
    if owner_id is None:
        return False, None, "not_found"
    
    if owner_id == user['id']:
        return True, owner_id, "owner"
    
    if database.is_user_admin(user['id']):
        return True, owner_id, "admin"
    
    return False, owner_id, "forbidden"

def is_valid_app_name(name):
    """Only allow lowercase letters, numbers, and hyphens, 3-30 chars"""
    return bool(re.match(r'^[a-z0-9]([a-z0-9-]{1,28}[a-z0-9])?$', name))

@app.context_processor
def inject_user():
    """Make current_user and is_admin available in all templates."""
    user = get_current_user()
    is_admin = database.is_user_admin(user['id']) if user else False
    return dict(current_user=user, is_admin=is_admin)


def calculate_app_age_days(created_at_str):
    """Calculate days since app was created."""
    try:
        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        delta = now - created_at
        return delta.total_seconds() / 86400  # Convert to days
    except:
        return 0


# ===== AUTH ROUTES =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    # Already logged in, redirect to homepage
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('login.html', error="Username and password are required")
        
        user = database.get_user_by_username(username)
        
        if user and check_password_hash(user[2], password):
            # Successful login
            session['user_id'] = user[0]
            database.log_action(
                user[0], user[1], 'login',
                ip_address=request.remote_addr
            )
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            database.log_action(
                None, username, 'login_failed',
                details='invalid credentials',
                ip_address=request.remote_addr
            )
            return render_template('login.html', error="Invalid username or password", username=username)
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page."""
    # Already logged in, redirect to homepage
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not username:
            errors.append("Username is required")
        elif len(username) < 3:
            errors.append("Username must be at least 3 characters")
        elif database.get_user_by_username(username):
            errors.append("Username already taken")
        
        if not password:
            errors.append("Password is required")
        elif len(password) < 6:
            errors.append("Password must be at least 6 characters")
        
        if password != confirm_password:
            errors.append("Passwords do not match")
        
        if errors:
            return render_template('register.html', errors=errors, username=username)
        
        # Create user
        password_hash = generate_password_hash(password)
        database.create_user(username, password_hash)
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')


@app.route('/logout')
def logout():
    """Logout and clear session."""
    user = get_current_user()
    if user:
        database.log_action(
            user['id'], user['username'], 'logout',
            ip_address=request.remote_addr
        )
    session.clear()
    return redirect(url_for('login'))


# ===== PROTECTED ROUTES =====

@app.route('/')
def index():
    """Landing page for unauthenticated visitors; dashboard for logged-in users."""
    if 'user_id' not in session:
        return render_template('landing.html')

    user = get_current_user()
    
    # Get apps owned by this user
    apps_data = database.list_apps_by_owner(user['id'])
    
    # Calculate depth and get replica count for each app
    apps = []
    total_replicas = 0
    
    for app_name, domain, status in apps_data:
        # Get created_at from apps table
        conn = database.get_connection()
        c = conn.cursor()
        c.execute('SELECT created_at FROM apps WHERE app_name=?', (app_name,))
        created_at_row = c.fetchone()
        conn.close()
        
        created_at = created_at_row[0] if created_at_row else None
        days_old = calculate_app_age_days(created_at) if created_at else 0
        
        replicas = database.get_replicas(app_name)
        replica_count = len(replicas)
        total_replicas += replica_count
        
        apps.append({
            'name': app_name,
            'domain': domain,
            'status': status,
            'days_old': days_old,
            'created_at': created_at,
            'replica_count': replica_count,
        })
    
    # Calculate stats
    stats = {
        'total_apps': len(apps),
        'total_replicas': total_replicas,
        'oldest_app_days': int(max([a['days_old'] for a in apps])) if apps else 0
    }
    
    return render_template('index.html', apps=apps, stats=stats)


@app.route('/app/<app_name>')
@login_required
def app_detail(app_name):
    """Detailed view of a single app."""
    user = get_current_user()
    
    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    
    if not can_access:
        if reason == "not_found":
            return "App not found or not assigned to any user", 404
        return "Forbidden: You don't have access to this app", 403
    
    # Get app info
    app_data = database.get_app(app_name)
    if not app_data:
        return "App not found", 404
    
    app = {
        'name': app_data[0],
        'domain': app_data[1],
        'builder': app_data[2],
        'status': app_data[3]
    }
    
    # Get replicas with metrics (batch fetch for performance)
    replicas_data = database.get_replicas(app_name)
    
    # Batch fetch all metrics at once
    container_ids = [container_id for _, _, container_id, _ in replicas_data if container_id]
    all_metrics = docker_ops.get_multiple_container_metrics(container_ids)
    
    replicas = []
    for replica_num, port, container_id, status in replicas_data:
        metrics = all_metrics.get(container_id) if container_id else None
        replicas.append({
            'num': replica_num,
            'port': port,
            'container_id': container_id,
            'status': status,
            'metrics': metrics
        })
    
    # Get deployment history
    deployments_data = database.get_deployment_history(app_name, limit=10)
    deployments = []
    for status, message, created_at in deployments_data:
        try:
            dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
            delta = datetime.now() - dt
            
            if delta.days > 0:
                time_ago = f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
            elif delta.seconds >= 3600:
                hours = delta.seconds // 3600
                time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif delta.seconds >= 60:
                minutes = delta.seconds // 60
                time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                time_ago = "just now"
        except:
            time_ago = created_at
        
        deployments.append({
            'status': status,
            'message': message,
            'time_ago': time_ago,
            'created_at': created_at
        })
    
    # Get config keys (not values by default)
    configs_data = database.get_configs(app_name)
    configs = [{'key': key, 'value': value} for key, value in configs_data]
    
    # Get logs from first replica if available
    logs = ""
    if replicas and replicas[0]['container_id']:
        try:
            logs = docker_ops.get_container_logs(replicas[0]['container_id'], follow=False)
            # Get last 50 lines
            logs = '\n'.join(logs.split('\n')[-50:])
        except:
            logs = "Unable to fetch logs"
    
    return render_template('app_detail.html', 
                         app=app, 
                         replicas=replicas, 
                         deployments=deployments,
                         configs=configs,
                         logs=logs)


@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for refreshing stats without full page reload."""
    user = get_current_user()
    
    # Get apps owned by this user
    apps = database.list_apps_by_owner(user['id'])
    
    total_replicas = 0
    for app_name, _, _ in apps:
        replicas = database.get_replicas(app_name)
        total_replicas += len(replicas)
    
    # Get oldest app
    conn = database.get_connection()
    c = conn.cursor()
    c.execute('SELECT created_at FROM apps WHERE owner_id=? ORDER BY created_at ASC LIMIT 1', (user['id'],))
    oldest = c.fetchone()
    conn.close()
    
    oldest_app_days = 0
    if oldest:
        oldest_app_days = int(calculate_app_age_days(oldest[0]))
    
    return jsonify({
        'total_apps': len(apps),
        'total_replicas': total_replicas,
        'oldest_app_days': oldest_app_days
    })


@app.route('/api/app/<app_name>/metrics')
@login_required
def api_app_metrics(app_name):
    """API endpoint for refreshing app metrics."""
    user = get_current_user()
    
    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'App not found'}), 404
        return jsonify({'error': 'Forbidden'}), 403
    
    # Batch fetch metrics for performance
    replicas_data = database.get_replicas(app_name)
    container_ids = [container_id for _, _, container_id, _ in replicas_data if container_id]
    all_metrics = docker_ops.get_multiple_container_metrics(container_ids)
    
    replicas = []
    for replica_num, port, container_id, status in replicas_data:
        metrics = all_metrics.get(container_id) if container_id else None
        replicas.append({
            'num': replica_num,
            'status': status,
            'metrics': metrics
        })
    
    return jsonify({'replicas': replicas})


@app.route('/metrics')
@login_required
def platform_metrics():
    """Platform-wide metrics overview page (scoped to user's apps)."""
    user = get_current_user()
    
    # Get apps owned by this user
    apps = database.list_apps_by_owner(user['id'])
    
    all_replicas = []
    all_container_ids = []
    
    # First pass: collect all container IDs
    for app_name, domain, status in apps:
        replicas_data = database.get_replicas(app_name)
        for replica_num, port, container_id, status in replicas_data:
            if container_id:
                all_container_ids.append(container_id)
            all_replicas.append({
                'app_name': app_name,
                'replica_num': replica_num,
                'port': port,
                'container_id': container_id,
                'status': status,
            })
    
    # Batch fetch all metrics at once for performance
    all_metrics = docker_ops.get_multiple_container_metrics(all_container_ids)
    
    # Second pass: attach metrics to replicas
    total_cpu = 0
    metrics_count = 0
    
    for replica_info in all_replicas:
        container_id = replica_info['container_id']
        metrics = all_metrics.get(container_id) if container_id else None
        replica_info['metrics'] = metrics
        
        if metrics:
            try:
                cpu_val = float(metrics['cpu'].replace('%', ''))
                total_cpu += cpu_val
                metrics_count += 1
                replica_info['cpu_numeric'] = cpu_val
            except:
                replica_info['cpu_numeric'] = 0
            
            try:
                mem_parts = metrics['memory'].split('/')
                mem_used = mem_parts[0].strip()
                replica_info['memory_display'] = mem_used
            except:
                replica_info['memory_display'] = metrics['memory']
        else:
            replica_info['cpu_numeric'] = 0
            replica_info['memory_display'] = 'N/A'
    
    avg_cpu = (total_cpu / metrics_count) if metrics_count > 0 else 0
    all_replicas.sort(key=lambda x: x.get('cpu_numeric', 0), reverse=True)
    
    return render_template('metrics.html', 
                         replicas=all_replicas,
                         total_replicas=len(all_replicas),
                         avg_cpu=avg_cpu,
                         total_apps=len(apps))


@app.route('/create-app', methods=['GET', 'POST'])
@login_required
def create_app_page():
    """Create app page (web UI)."""
    if request.method == 'POST':
        app_name = request.form.get('app_name', '').strip().lower()
        
        if not is_valid_app_name(app_name):
            return render_template('create_app.html', 
                                 error="Invalid app name. Use lowercase letters, numbers, and hyphens only (3-30 characters).")
        
        # Call the API endpoint (which supports session auth)
        user = get_current_user()
        
        # Check if app already exists
        if database.get_app_owner(app_name) is not None:
            return render_template('create_app.html', 
                                 error="App name already taken. Please choose a different name.")
        
        # Create the app
        repo_base = "/home/ubuntu/git-hook-test"
        repo_path = f"{repo_base}/{app_name}.git"
        hook_source = f"{repo_base}/test-repo.git/hooks/post-receive"
        
        if os.path.exists(repo_path):
            return render_template('create_app.html', 
                                 error="Repository already exists on disk. Please contact support.")
        
        try:
            subprocess.run(["git", "init", "--bare", repo_path], check=True, capture_output=True, text=True)
            subprocess.run(["cp", hook_source, f"{repo_path}/hooks/post-receive"], check=True, capture_output=True, text=True)
            subprocess.run(["chmod", "+x", f"{repo_path}/hooks/post-receive"], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            return render_template('create_app.html', 
                                 error=f"Failed to create repository: {e.stderr}")
        
        domain = f"{app_name}.dr0wn.duckdns.org"
        database.upsert_app(app_name, domain, "heroku/builder:24")
        database.set_app_owner(app_name, user['id'])
        
        # Redirect to onboarding guide
        return redirect(url_for('onboarding_guide', app_name=app_name))
    
    return render_template('create_app.html')


@app.route('/onboarding/<app_name>')
@login_required
def onboarding_guide(app_name):
    """Onboarding guide after creating an app."""
    user = get_current_user()
    
    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return "App not found", 404
        return "Forbidden", 403
    
    # Get app info
    app_data = database.get_app(app_name)
    if not app_data:
        return "App not found", 404
    
    domain = app_data[1]
    
    return render_template('onboarding.html', app_name=app_name, domain=domain)


@app.route('/help')
@login_required
def help_page():
    """Help and troubleshooting page."""
    return render_template('help.html')


# ===== PROFILE / SETTINGS ROUTE =====

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile and account settings page."""
    user = get_current_user()
    username_success = None
    username_error = None
    password_success = None
    password_error = None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_username':
            new_username = request.form.get('new_username', '').strip()
            if not new_username:
                username_error = "Username is required"
            elif len(new_username) < 3:
                username_error = "Username must be at least 3 characters"
            elif new_username == user['username']:
                username_error = "That's already your username"
            elif database.get_user_by_username(new_username):
                username_error = "Username already taken"
            else:
                ok = database.update_username(user['id'], new_username)
                if ok:
                    database.log_action(
                        user['id'], user['username'], 'username_change',
                        details=f"{user['username']} -> {new_username}",
                        ip_address=request.remote_addr
                    )
                    # Update session display name immediately
                    username_success = f"Username changed to \"{new_username}\""
                    # Re-fetch user so the template shows the new name
                    user = get_current_user()
                else:
                    username_error = "Username already taken"

        elif action == 'update_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            current_hash = database.get_user_password_hash(user['id'])
            if not current_hash or not check_password_hash(current_hash, current_password):
                password_error = "Current password is incorrect"
            elif not new_password:
                password_error = "New password is required"
            elif len(new_password) < 6:
                password_error = "Password must be at least 6 characters"
            elif new_password != confirm_password:
                password_error = "Passwords do not match"
            else:
                new_hash = generate_password_hash(new_password)
                database.update_password(user['id'], new_hash)
                database.log_action(
                    user['id'], user['username'], 'password_change',
                    ip_address=request.remote_addr
                )
                password_success = "Password updated successfully"

    return render_template(
        'profile.html',
        user=user,
        username_success=username_success,
        username_error=username_error,
        password_success=password_success,
        password_error=password_error,
    )



@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400

    user = database.get_user_by_username(username)
    if not user or not check_password_hash(user[2], password):
        return jsonify({'error': 'invalid credentials'}), 401

    token = secrets.token_hex(32)
    database.set_user_token(user[0], token)

    return jsonify({'token': token, 'username': user[1]}), 200


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'username and password required'}), 400
    if len(username) < 3:
        return jsonify({'error': 'username must be at least 3 characters'}), 400
    if len(password) < 6:
        return jsonify({'error': 'password must be at least 6 characters'}), 400
    if database.get_user_by_username(username):
        return jsonify({'error': 'username already taken'}), 409

    password_hash = generate_password_hash(password)
    user_id = database.create_user(username, password_hash)

    token = secrets.token_hex(32)
    database.set_user_token(user_id, token)

    return jsonify({'token': token, 'username': username, 'id': user_id}), 201


@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    is_admin = database.is_user_admin(user['id'])
    return jsonify({
        'user': {
            'id': user['id'],
            'username': user['username'],
            'is_admin': is_admin
        }
    }), 200

@app.route('/api/apps', methods=['GET'])
def api_list_apps():
    user = get_user_from_token()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    apps_data = database.list_apps_by_owner(user['id'])
    apps = []
    for app_name, domain, status in apps_data:
        replicas = database.get_replicas(app_name)
        apps.append({
            'name': app_name,
            'domain': domain,
            'status': status,
            'replicas': len(replicas)
        })

    return jsonify({'apps': apps}), 200

@app.route('/api/apps/<app_name>/metrics', methods=['GET'])
def api_app_metrics_v2(app_name):
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'app not found'}), 404
        return jsonify({'error': 'forbidden'}), 403

    replicas_data = database.get_replicas(app_name)
    container_ids = [container_id for _, _, container_id, _ in replicas_data if container_id]
    all_metrics = docker_ops.get_multiple_container_metrics(container_ids)

    replicas = []
    for replica_num, port, container_id, status in replicas_data:
        metrics = all_metrics.get(container_id)
        replicas.append({
            'replica_num': replica_num,
            'port': port,
            'status': status,
            'cpu': metrics['cpu'] if metrics else None,
            'memory': metrics['memory'] if metrics else None
        })

    return jsonify({'app': app_name, 'replicas': replicas}), 200

@app.route('/api/apps/<app_name>/scale', methods=['POST'])
def api_scale_app(app_name):
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'app not found'}), 404
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json(silent=True) or {}
    desired_count = data.get('replicas')

    if not isinstance(desired_count, int) or desired_count < 1:
        return jsonify({'error': 'replicas must be a positive integer'}), 400

    try:
        from core.scaler import scale_app
        scale_app(app_name, app_name, desired_count)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'scaling failed: {str(e)}'}), 500

    replicas = database.get_replicas(app_name)
    database.log_action(
        user['id'], user['username'], 'app_scale',
        target=app_name,
        details=f"replicas={len(replicas)}",
        ip_address=request.remote_addr
    )
    return jsonify({'app': app_name, 'replicas': len(replicas)}), 200


@app.route('/api/apps/<app_name>/logs', methods=['GET'])
def api_app_logs(app_name):
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'app not found'}), 404
        return jsonify({'error': 'forbidden'}), 403

    replicas = database.get_replicas(app_name)
    if not replicas:
        return jsonify({'error': 'no running replicas'}), 404

    replica_num, port, container_id, status = replicas[0]
    try:
        logs = docker_ops.get_container_logs(container_id, follow=False)
        logs = '\n'.join(logs.split('\n')[-50:])
    except Exception as e:
        return jsonify({'error': f'could not fetch logs: {str(e)}'}), 500

    return jsonify({'app': app_name, 'logs': logs}), 200

@app.route('/api/apps/create', methods=['POST'])
def api_create_app():
    # Support both token auth (CLI) and session auth (web UI)
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    app_name = data.get('name', '').strip().lower()

    if not is_valid_app_name(app_name):
        return jsonify({'error': 'invalid app name: use lowercase letters, numbers, hyphens only, 3-30 chars'}), 400

    if database.get_app_owner(app_name) is not None or database.get_app(app_name):
        return jsonify({'error': 'app name already taken'}), 409

    repo_base = "/home/ubuntu/git-hook-test"
    repo_path = f"{repo_base}/{app_name}.git"
    hook_source = f"{repo_base}/test-repo.git/hooks/post-receive"

    if os.path.exists(repo_path):
        return jsonify({'error': 'repo already exists on disk'}), 409

    try:
        subprocess.run(["git", "init", "--bare", repo_path], check=True, capture_output=True, text=True)
        subprocess.run(["cp", hook_source, f"{repo_path}/hooks/post-receive"], check=True, capture_output=True, text=True)
        subprocess.run(["chmod", "+x", f"{repo_path}/hooks/post-receive"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'failed to create repo: {e.stderr}'}), 500

    domain = f"{app_name}.dr0wn.duckdns.org"
    database.upsert_app(app_name, domain, "heroku/builder:24")
    database.set_app_owner(app_name, user['id'])

    database.log_action(
        user['id'], user['username'], 'app_create',
        target=app_name,
        ip_address=request.remote_addr
    )

    remote_url = f"ssh://ubuntu@51.170.134.251{repo_path}"

    return jsonify({
        'app': app_name,
        'domain': domain,
        'git_remote': remote_url,
        'push_instructions': f"git remote add platform {remote_url} && git push platform main"
    }), 201


@app.route('/api/apps/<app_name>/link', methods=['POST'])
def api_link_app(app_name):
    """
    Get git remote info for an existing app (for CLI linkage).
    Like 'create' but for apps that already exist.
    """
    # Support both token auth (CLI) and session auth (web UI)
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    
    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'app not found'}), 404
        return jsonify({'error': 'forbidden'}), 403
    
    # Get app info
    app_data = database.get_app(app_name)
    domain = app_data[1] if app_data else f"{app_name}.dr0wn.duckdns.org"
    
    # Return git remote info
    repo_path = f"/home/ubuntu/git-hook-test/{app_name}.git"
    remote_url = f"ssh://ubuntu@drown-platform{repo_path}"
    
    return jsonify({
        'app': app_name,
        'domain': domain,
        'git_remote': remote_url,
        'push_instructions': f"git push platform main"
    }), 200


@app.route('/api/keys/register', methods=['POST'])
def api_register_key():
    user = get_user_from_token()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    public_key = data.get('public_key', '').strip()

    if not public_key or not public_key.startswith(('ssh-ed25519', 'ssh-rsa')):
        return jsonify({'error': 'invalid public key format'}), 400

    if '\n' in public_key or '\r' in public_key:
        return jsonify({'error': 'invalid public key format'}), 400

    # Extract just the key material (second field) to match existing entries
    # regardless of which user/command= prefix they currently have
    key_parts = public_key.split()
    if len(key_parts) < 2:
        return jsonify({'error': 'invalid public key format'}), 400
    key_material = key_parts[1]

    authorized_keys_path = "/home/ubuntu/.ssh/authorized_keys"
    wrapper_script = "/home/ubuntu/mini-heroku/control-plane/git-shell-wrapper.sh"

    try:
        # Read existing entries, filtering out ANY line that contains this
        # exact key material (regardless of which user it was tied to before)
        existing_lines = []
        if os.path.exists(authorized_keys_path):
            with open(authorized_keys_path, "r") as f:
                existing_lines = f.readlines()

        filtered_lines = [
            line for line in existing_lines
            if key_material not in line
        ]

        new_entry = (
            f'command="{wrapper_script} {user["id"]}",'
            f'no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty '
            f'{public_key}\n'
        )
        filtered_lines.append(new_entry)

        with open(authorized_keys_path, "w") as f:
            f.writelines(filtered_lines)

    except Exception as e:
        return jsonify({'error': f'failed to register key: {str(e)}'}), 500

    database.log_action(
        user['id'], user['username'], 'ssh_key_register',
        ip_address=request.remote_addr
    )
    return jsonify({'message': 'key registered successfully'}), 200


# ===== DELETE APP ROUTES =====

@app.route('/app/<app_name>/delete', methods=['POST'])
@login_required
def delete_app_route(app_name):
    """Delete an app (web UI)."""
    user = get_current_user()
    
    # Check ownership (owner OR admin)
    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'App not found'}), 404
        return jsonify({'error': 'Forbidden'}), 403
    
    # Verify the confirmation name matches
    data = request.get_json(silent=True) or {}
    confirm_name = data.get('confirm_name', '').strip()
    
    if confirm_name != app_name:
        return jsonify({'error': 'App name confirmation does not match'}), 400
    
    # Delete the app
    from core.scaler import delete_app
    try:
        success, replica_count, message = delete_app(app_name)
        # Distinguish: admin deleting someone else's app vs owner deleting own
        is_admin_action = (reason == 'admin')
        log_details = f"admin deleted app owned by uid={owner_id}" if is_admin_action else f"owner deleted own app"
        database.log_action(
            user['id'], user['username'], 'app_delete',
            target=app_name,
            details=log_details,
            ip_address=request.remote_addr
        )
        return jsonify({'success': True, 'message': message}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete app: {str(e)}'}), 500


# ===== ADMIN ROUTES =====

@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard showing all apps across all users."""
    user = get_current_user()
    
    # Check if user is admin
    if not database.is_user_admin(user['id']):
        return redirect(url_for('index'))
    
    # Get all apps with owner information
    apps_data = database.get_all_apps_with_owners()
    
    apps = []
    for app_name, domain, status, owner_id, owner_username, created_at in apps_data:
        replicas = database.get_replicas(app_name)
        apps.append({
            'name': app_name,
            'domain': domain,
            'status': status,
            'owner_id': owner_id,
            'owner_username': owner_username or 'Unassigned',
            'replica_count': len(replicas),
            'created_at': created_at
        })
    
    return render_template('admin.html', apps=apps)


@app.route('/admin/delete/<app_name>', methods=['POST'])
@login_required
def admin_delete_app(app_name):
    """Admin delete action (can delete any app)."""
    user = get_current_user()
    
    # Check if user is admin
    if not database.is_user_admin(user['id']):
        return jsonify({'error': 'Forbidden: Admin access required'}), 403
    
    # Verify the confirmation name matches
    data = request.get_json(silent=True) or {}
    confirm_name = data.get('confirm_name', '').strip()
    
    if confirm_name != app_name:
        return jsonify({'error': 'App name confirmation does not match'}), 400
    
    # Capture owner before deletion for the audit record
    owner_id = database.get_app_owner(app_name)

    # Delete the app
    from core.scaler import delete_app
    try:
        success, replica_count, message = delete_app(app_name)
        database.log_action(
            user['id'], user['username'], 'app_delete',
            target=app_name,
            details=f"admin deleted app owned by uid={owner_id}",
            ip_address=request.remote_addr
        )
        return jsonify({'success': True, 'message': message}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to delete app: {str(e)}'}), 500


@app.route('/admin/audit-log')
@login_required
def admin_audit_log():
    """Audit log page — admin only."""
    user = get_current_user()
    if not database.is_user_admin(user['id']):
        return redirect(url_for('index'))

    action_filter = request.args.get('action', '').strip() or None
    user_filter_raw = request.args.get('user_id', '').strip()
    user_filter = int(user_filter_raw) if user_filter_raw.isdigit() else None
    limit = min(int(request.args.get('limit', 200)), 500)

    rows = database.get_audit_log(limit=limit, user_id=user_filter, action=action_filter)
    entries = []
    for row_id, uid, uname, action, target, details, ip, created_at in rows:
        entries.append({
            'id': row_id,
            'user_id': uid,
            'username': uname or '—',
            'action': action,
            'target': target or '—',
            'details': details or '',
            'ip_address': ip or '—',
            'created_at': created_at,
        })

    # Distinct action types for the filter dropdown
    all_rows = database.get_audit_log(limit=5000)
    action_types = sorted({r[3] for r in all_rows})

    return render_template(
        'audit_log.html',
        entries=entries,
        action_types=action_types,
        current_action=action_filter or '',
        current_limit=limit,
    )


@app.route('/api/admin/audit-log', methods=['GET'])
def api_admin_audit_log():
    """JSON audit log — admin only."""
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401
    if not database.is_user_admin(user['id']):
        return jsonify({'error': 'forbidden'}), 403

    action_filter = request.args.get('action') or None
    user_filter_raw = request.args.get('user_id', '')
    user_filter = int(user_filter_raw) if user_filter_raw.isdigit() else None
    limit = min(int(request.args.get('limit', 100)), 500)

    rows = database.get_audit_log(limit=limit, user_id=user_filter, action=action_filter)
    entries = [
        {
            'id': r[0], 'user_id': r[1], 'username': r[2],
            'action': r[3], 'target': r[4], 'details': r[5],
            'ip_address': r[6], 'created_at': r[7],
        }
        for r in rows
    ]
    return jsonify({'entries': entries, 'count': len(entries)}), 200


@app.route('/api/admin/apps', methods=['GET'])
def api_admin_apps():
    """Admin-only endpoint returning all apps and owners across the platform."""
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    if not database.is_user_admin(user['id']):
        return jsonify({'error': 'forbidden'}), 403

    apps_data = database.get_all_apps_with_owners()
    apps = []
    for app_name, domain, status, owner_id, owner_username, created_at in apps_data:
        replicas = database.get_replicas(app_name)
        apps.append({
            'name': app_name,
            'domain': domain,
            'status': status,
            'owner_id': owner_id,
            'owner_username': owner_username or 'Unassigned',
            'replica_count': len(replicas),
            'created_at': created_at
        })

    return jsonify({'apps': apps}), 200


@app.route('/api/apps/<app_name>', methods=['DELETE'])
@app.route('/api/apps/<app_name>/delete', methods=['DELETE', 'POST'])
def api_delete_app(app_name):
    """Delete an app via token-authenticated API (owner or admin allowed)."""
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'app not found'}), 404
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json(silent=True) or {}
    confirm_name = data.get('confirm_name', '').strip()
    if confirm_name != app_name:
        return jsonify({'error': 'app name confirmation does not match'}), 400

    from core.scaler import delete_app
    try:
        success, replica_count, message = delete_app(app_name)
        return jsonify({'success': True, 'message': message}), 200
    except Exception as e:
        return jsonify({'error': f'failed to delete app: {str(e)}'}), 500


@app.route('/api/apps/<app_name>/deployments', methods=['GET'])
def api_app_deployments(app_name):
    """Get deployment history for an app."""
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'app not found'}), 404
        return jsonify({'error': 'forbidden'}), 403

    deployments_data = database.get_deployment_history(app_name, limit=10)
    deployments = []
    for status, message, created_at in deployments_data:
        deployments.append({
            'status': status,
            'message': message,
            'created_at': created_at
        })

    return jsonify({'app': app_name, 'deployments': deployments}), 200


@app.route('/api/apps/<app_name>/config', methods=['GET', 'POST', 'DELETE'])
def api_app_config(app_name):
    """Manage environment configuration keys/values for an app."""
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    can_access, owner_id, reason = can_access_app(user, app_name)
    if not can_access:
        if reason == "not_found":
            return jsonify({'error': 'app not found'}), 404
        return jsonify({'error': 'forbidden'}), 403

    if request.method == 'GET':
        configs_data = database.get_configs(app_name)
        configs = [{'key': key, 'value': value} for key, value in configs_data]
        return jsonify({'app': app_name, 'configs': configs}), 200

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        key = data.get('key', '').strip()
        value = data.get('value', '')
        if not key:
            return jsonify({'error': 'config key is required'}), 400
        database.set_config(app_name, key, value)
        database.log_action(
            user['id'], user['username'], 'config_set',
            target=app_name,
            details=key,  # log key name only — never the value
            ip_address=request.remote_addr
        )
        configs_data = database.get_configs(app_name)
        configs = [{'key': k, 'value': v} for k, v in configs_data]
        return jsonify({'app': app_name, 'configs': configs}), 200

    elif request.method == 'DELETE':
        data = request.get_json(silent=True) or {}
        key = data.get('key', '').strip()
        if not key:
            return jsonify({'error': 'config key is required'}), 400
        database.unset_config(app_name, key)
        database.log_action(
            user['id'], user['username'], 'config_unset',
            target=app_name,
            details=key,
            ip_address=request.remote_addr
        )
        configs_data = database.get_configs(app_name)
        configs = [{'key': k, 'value': v} for k, v in configs_data]
        return jsonify({'app': app_name, 'configs': configs}), 200


@app.route('/api/user/profile', methods=['PUT', 'POST'])
def api_user_profile():
    """Update profile settings (username or password)."""
    user = get_user_from_token() or get_current_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    data = request.get_json(silent=True) or {}
    action = data.get('action')

    if action == 'update_username':
        new_username = data.get('new_username', '').strip()
        if not new_username:
            return jsonify({'error': 'new_username is required'}), 400
        if len(new_username) < 3:
            return jsonify({'error': 'username must be at least 3 characters'}), 400
        if new_username == user['username']:
            return jsonify({'error': 'that is already your username'}), 400
        if database.get_user_by_username(new_username):
            return jsonify({'error': 'username already taken'}), 409

        ok = database.update_username(user['id'], new_username)
        if ok:
            database.log_action(
                user['id'], user['username'], 'username_change',
                details=f"{user['username']} -> {new_username}",
                ip_address=request.remote_addr
            )
            return jsonify({'message': f'username updated to {new_username}', 'username': new_username}), 200
        else:
            return jsonify({'error': 'username already taken'}), 409

    elif action == 'update_password':
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return jsonify({'error': 'current_password and new_password required'}), 400
        if len(new_password) < 6:
            return jsonify({'error': 'new password must be at least 6 characters'}), 400

        current_hash = database.get_user_password_hash(user['id'])
        if not current_hash or not check_password_hash(current_hash, current_password):
            return jsonify({'error': 'current password is incorrect'}), 400

        new_hash = generate_password_hash(new_password)
        database.update_password(user['id'], new_hash)
        database.log_action(
            user['id'], user['username'], 'password_change',
            ip_address=request.remote_addr
        )
        return jsonify({'message': 'password updated successfully'}), 200

    else:
        return jsonify({'error': 'invalid action'}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



