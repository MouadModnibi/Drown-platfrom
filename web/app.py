import sys
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
import math

# Add parent directory to path to import from control-plane
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'control-plane'))

from core import database, docker_ops

app = Flask(__name__)

def calculate_app_age_days(created_at_str):
    """Calculate days since app was created."""
    try:
        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        delta = now - created_at
        return delta.total_seconds() / 86400  # Convert to days
    except:
        return 0


def calculate_app_age_days(created_at_str):
    """Calculate days since app was created."""
    try:
        created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        delta = now - created_at
        return delta.total_seconds() / 86400  # Convert to days
    except:
        return 0


def calculate_ocean_depth(days_old, max_depth=700, scale_factor=50):
    """
    Non-linear depth calculation: depth = min(max_depth, sqrt(days_old) * scale_factor)
    This makes new apps sink fast, then slow down asymptotically.
    """
    depth = math.sqrt(days_old) * scale_factor
    return min(depth, max_depth)


@app.route('/')
def index():
    """Homepage showing all apps."""
    conn = database.get_connection()
    c = conn.cursor()
    
    # Get all apps with created_at timestamp
    c.execute('SELECT app_name, domain, status, created_at FROM apps')
    apps_data = c.fetchall()
    conn.close()
    
    # Calculate depth and get replica count for each app
    apps = []
    total_replicas = 0
    
    for app_name, domain, status, created_at in apps_data:
        days_old = calculate_app_age_days(created_at)
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
def app_detail(app_name):
    """Detailed view of a single app."""
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
    
    # Get replicas with metrics (batched into ONE docker call instead of N)
    replicas_data = database.get_replicas(app_name)
    container_names = [container_id for _, _, container_id, _ in replicas_data if container_id]
    all_metrics = docker_ops.get_multiple_container_metrics(container_names)

    replicas = []
    for replica_num, port, container_id, status in replicas_data:
        metrics = all_metrics.get(container_id)
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
def api_stats():
    """API endpoint for refreshing stats without full page reload."""
    conn = database.get_connection()
    c = conn.cursor()
    c.execute('SELECT app_name FROM apps')
    apps = c.fetchall()
    conn.close()
    
    total_replicas = 0
    for (app_name,) in apps:
        replicas = database.get_replicas(app_name)
        total_replicas += len(replicas)
    
    # Get oldest app
    conn = database.get_connection()
    c = conn.cursor()
    c.execute('SELECT created_at FROM apps ORDER BY created_at ASC LIMIT 1')
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
def api_app_metrics(app_name):
    """API endpoint for refreshing app metrics."""
    replicas_data = database.get_replicas(app_name)
    replicas = []
    for replica_num, port, container_id, status in replicas_data:
        metrics = docker_ops.get_container_metrics(container_id) if container_id else None
        replicas.append({
            'num': replica_num,
            'status': status,
            'metrics': metrics
        })
    
    return jsonify({'replicas': replicas})


@app.route('/metrics')
def platform_metrics():
    """Platform-wide metrics overview page."""
    apps = database.list_apps()
    
    all_replicas = []
    total_cpu = 0
    metrics_count = 0
    
    for app_name, domain, status in apps:
        replicas_data = database.get_replicas(app_name)
        for replica_num, port, container_id, status in replicas_data:
            metrics = docker_ops.get_container_metrics(container_id) if container_id else None
            
            replica_info = {
                'app_name': app_name,
                'replica_num': replica_num,
                'port': port,
                'container_id': container_id,
                'status': status,
                'metrics': metrics
            }
            
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
            
            all_replicas.append(replica_info)
    
    avg_cpu = (total_cpu / metrics_count) if metrics_count > 0 else 0
    all_replicas.sort(key=lambda x: x.get('cpu_numeric', 0), reverse=True)
    
    return render_template('metrics.html', 
                         replicas=all_replicas,
                         total_replicas=len(all_replicas),
                         avg_cpu=avg_cpu,
                         total_apps=len(apps))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
