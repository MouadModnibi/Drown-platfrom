import time
import re
from core.database import list_apps, get_replicas, insert_metric, init_database
from core.docker_ops import get_multiple_container_metrics
import json

LOG_DIR = "/var/log/caddy"
_log_offsets = {}  # in-memory: {app_name: last_byte_offset}

def count_requests_since_last_check(app_name):
    log_path = f"{LOG_DIR}/{app_name}.log"
    try:
        with open(log_path, "r") as f:
            last_offset = _log_offsets.get(app_name, 0)
            f.seek(last_offset)
            new_lines = f.readlines()
            _log_offsets[app_name] = f.tell()
    except FileNotFoundError:
        return 0

    count = 0
    for line in new_lines:
        try:
            entry = json.loads(line)
            if entry.get("logger") == "http.log.access.log0":
                count += 1
        except json.JSONDecodeError:
            continue

    return count

def parse_percent(value_str):
    """Convert '0.5%' -> 0.5"""
    try:
        return float(value_str.replace("%", "").strip())
    except (ValueError, AttributeError):
        return 0.0

def parse_mem_value(value_str):
    """Convert '1.2GiB' or '512MiB' -> value in MiB (float)"""
    value_str = value_str.strip()
    match = re.match(r"([\d.]+)\s*([a-zA-Z]+)", value_str)
    if not match:
        return 0.0
    num, unit = match.groups()
    num = float(num)
    unit = unit.lower()
    if unit in ("gib", "gb"):
        return num * 1024
    elif unit in ("mib", "mb"):
        return num
    elif unit in ("kib", "kb"):
        return num / 1024
    return num

def parse_mem_percent(mem_str):
    """Convert '32MiB / 512MiB' -> 6.25"""
    try:
        used, limit = mem_str.split("/")
        used_val = parse_mem_value(used)
        limit_val = parse_mem_value(limit)
        return round((used_val / limit_val) * 100, 2) if limit_val else 0.0
    except Exception:
        return 0.0

def collect_once():
    apps = list_apps()  # [(app_name, domain, status), ...]

    for app_name, domain, status in apps:
        if status != "running":
            continue

        replicas = get_replicas(app_name)  # [(replica_num, port, container_id, status), ...]
        container_ids = [r[2] for r in replicas if r[3] == "running" and r[2]]

        if not container_ids:
            continue

        stats = get_multiple_container_metrics(container_ids)

        total_cpu = 0.0
        total_ram = 0.0
        count = 0
        for cid, data in stats.items():
            if data:
                total_cpu += parse_percent(data.get("cpu", "0%"))
                total_ram += parse_mem_percent(data.get("memory", "0 / 0"))
                count += 1

        avg_cpu = round(total_cpu / count, 2) if count else 0.0
        avg_ram = round(total_ram / count, 2) if count else 0.0

        req_count = count_requests_since_last_check(app_name)
        insert_metric(app_name, avg_cpu, avg_ram, request_count=req_count)

def run_forever():
    init_database()  # ensures metrics table exists too

    while True:
        try:
            collect_once()
        except Exception as e:
            print(f"[metrics_collector] error: {e}")
        time.sleep(60)

if __name__ == "__main__":
    run_forever()