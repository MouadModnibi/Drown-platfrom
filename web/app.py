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

def is_valid_app_name(name):
    """Only allow lowercase letters, numbers, and hyphens, 3-30 chars"""
    return bool(re.match(r'^[a-z0-9]([a-z0-9-]{1,28}[a-z0-9])?$', name))

@app.context_processor
def inject_user():
    """Make current_user available in all templates."""
    return dict(current_user=get_current_user())


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
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
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
    session.clear()
    return redirect(url_for('login'))


# ===== PROTECTED ROUTES =====

@app.route('/')
@login_required
def index():
    """Homepage showing all apps owned by the current user."""
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
    
    # Check ownership
    owner_id = database.get_app_owner(app_name)
    
    if owner_id is None:
        return "App not found or not assigned to any user", 404
    
    if owner_id != user['id']:
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
    
    # Check ownership
    owner_id = database.get_app_owner(app_name)
    if owner_id != user['id']:
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
    user = get_user_from_token()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    owner_id = database.get_app_owner(app_name)
    if owner_id is None:
        return jsonify({'error': 'app not found'}), 404
    if owner_id != user['id']:
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
    user = get_user_from_token()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    owner_id = database.get_app_owner(app_name)
    if owner_id is None:
        return jsonify({'error': 'app not found'}), 404
    if owner_id != user['id']:
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
    return jsonify({'app': app_name, 'replicas': len(replicas)}), 200


@app.route('/api/apps/<app_name>/logs', methods=['GET'])
def api_app_logs(app_name):
    user = get_user_from_token()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    owner_id = database.get_app_owner(app_name)
    if owner_id is None:
        return jsonify({'error': 'app not found'}), 404
    if owner_id != user['id']:
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
    user = get_user_from_token()
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

    remote_url = f"ssh://ubuntu@51.170.134.251{repo_path}"

    return jsonify({
        'app': app_name,
        'domain': domain,
        'git_remote': remote_url,
        'push_instructions': f"git remote add platform {remote_url} && git push platform main"
    }), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



