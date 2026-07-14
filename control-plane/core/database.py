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
