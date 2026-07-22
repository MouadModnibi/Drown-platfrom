import sqlite3
from core.config import DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_database():
    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT UNIQUE NOT NULL,
            domain TEXT,
            builder TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
# Add owner_id column to apps table if it doesn't exist yet (safe migration)
    c.execute("PRAGMA table_info(apps)")
    columns = [row[1] for row in c.fetchall()]
    if 'owner_id' not in columns:
        c.execute("ALTER TABLE apps ADD COLUMN owner_id INTEGER")    
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    if 'api_token' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN api_token TEXT")
    
    # Add is_admin column to users table if it doesn't exist yet (safe migration)
    c.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in c.fetchall()]
    if 'is_admin' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")


    c.execute('''
        CREATE TABLE IF NOT EXISTS replicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            replica_num INTEGER NOT NULL,
            port INTEGER UNIQUE NOT NULL,
            container_id TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(app_name, replica_num),
            FOREIGN KEY(app_name) REFERENCES apps(app_name)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS app_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(app_name, key)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT NOT NULL,
            status TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()


# ---------------- apps ----------------

def upsert_app(app_name, domain, builder):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO apps (app_name, domain, builder, status)
        VALUES (?, ?, ?, 'running')
        ON CONFLICT(app_name) DO UPDATE SET
            domain=excluded.domain,
            builder=excluded.builder,
            status='running'
    ''', (app_name, domain, builder))
    conn.commit()
    conn.close()


def get_app(app_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT app_name, domain, builder, status FROM apps WHERE app_name=?', (app_name,))
    row = c.fetchone()
    conn.close()
    return row


def list_apps():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT app_name, domain, status FROM apps')
    rows = c.fetchall()
    conn.close()
    return rows


# ---------------- replicas ----------------

def get_used_ports():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT port FROM replicas')
    ports = [row[0] for row in c.fetchall()]
    conn.close()
    return ports


def get_replicas(app_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT replica_num, port, container_id, status
        FROM replicas WHERE app_name=? ORDER BY replica_num
    ''', (app_name,))
    rows = c.fetchall()
    conn.close()
    return rows


def add_replica(app_name, replica_num, port, container_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO replicas (app_name, replica_num, port, container_id, status)
        VALUES (?, ?, ?, ?, 'running')
    ''', (app_name, replica_num, port, container_id))
    conn.commit()
    conn.close()


def remove_replica(app_name, replica_num):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM replicas WHERE app_name=? AND replica_num=?', (app_name, replica_num))
    conn.commit()
    conn.close()


def remove_all_replicas(app_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM replicas WHERE app_name=?', (app_name,))
    conn.commit()
    conn.close()


def remove_app(app_name):
    """Remove the app record and all related data from the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM replicas WHERE app_name=?', (app_name,))
    c.execute('DELETE FROM app_configs WHERE app_name=?', (app_name,))
    c.execute('DELETE FROM deployments WHERE app_name=?', (app_name,))
    c.execute('DELETE FROM apps WHERE app_name=?', (app_name,))
    conn.commit()
    conn.close()


# ---------------- configs ----------------

def get_configs(app_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT key, value FROM app_configs WHERE app_name=?', (app_name,))
    rows = c.fetchall()
    conn.close()
    return rows


def set_config(app_name, key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO app_configs (app_name, key, value)
        VALUES (?, ?, ?)
    ''', (app_name, key, value))
    conn.commit()
    conn.close()


def unset_config(app_name, key):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM app_configs WHERE app_name=? AND key=?', (app_name, key))
    conn.commit()
    conn.close()

# ---------------- users ----------------

def create_user(username, password_hash):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
    ''', (username, password_hash))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id


def get_user_by_username(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, username, password_hash FROM users WHERE username=?', (username,))
    row = c.fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, username FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def set_app_owner(app_name, owner_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE apps SET owner_id=? WHERE app_name=?', (owner_id, app_name))
    conn.commit()
    conn.close()


def list_apps_by_owner(owner_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT app_name, domain, status FROM apps WHERE owner_id=?', (owner_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_app_owner(app_name):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT owner_id FROM apps WHERE app_name=?', (app_name,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None
# ---------------- deployments (history) ----------------

def log_deployment(app_name, status, message=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO deployments (app_name, status, message)
        VALUES (?, ?, ?)
    ''', (app_name, status, message))
    conn.commit()
    conn.close()


def get_deployment_history(app_name, limit=10):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT status, message, created_at FROM deployments
        WHERE app_name=? ORDER BY created_at DESC LIMIT ?
    ''', (app_name, limit))
    rows = c.fetchall()
    conn.close()
    return rows

def set_user_token(user_id, token):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET api_token=? WHERE id=?', (token, user_id))
    conn.commit()
    conn.close()


def get_user_by_token(token):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT id, username FROM users WHERE api_token=?', (token,))
    row = c.fetchone()
    conn.close()
    return row


# ---------------- admin ----------------

def is_user_admin(user_id):
    """Check if user has admin privileges."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT is_admin FROM users WHERE id=?', (user_id,))
    result = c.fetchone()
    conn.close()
    return bool(result[0]) if result else False


def get_all_apps_with_owners():
    """Get all apps with owner information (admin only)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT 
            a.app_name, 
            a.domain, 
            a.status, 
            a.owner_id,
            u.username,
            a.created_at
        FROM apps a
        LEFT JOIN users u ON a.owner_id = u.id
        ORDER BY a.created_at DESC
    ''')
    apps = c.fetchall()
    conn.close()
    return apps


def update_username(user_id, new_username):
    """Update a user's username. Returns True on success, False if name is taken."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET username=? WHERE id=?', (new_username, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_password(user_id, new_password_hash):
    """Update a user's password hash."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE users SET password_hash=? WHERE id=?', (new_password_hash, user_id))
    conn.commit()
    conn.close()


def get_user_password_hash(user_id):
    """Get a user's current password hash for verification."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None
