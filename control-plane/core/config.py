import os

DEFAULT_DB_PATH = "/home/ubuntu/mini-heroku/apps.db"
if os.path.exists(DEFAULT_DB_PATH):
    DB_PATH = DEFAULT_DB_PATH
else:
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'apps.db'))
CADDYFILE_PATH = "/etc/caddy/Caddyfile"

BASE_PORT = 4000
MAX_PORT = 5000

DEFAULT_BUILDER = "heroku/builder:24"
DEFAULT_DOMAIN = "dr0wn.duckdns.org"

MAX_REPLICAS_PER_APP = 5
