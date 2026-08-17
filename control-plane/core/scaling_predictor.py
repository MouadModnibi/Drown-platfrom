import time
import logging
from datetime import datetime
from core.database import list_apps, get_hourly_pattern, get_replicas, get_recent_metrics
from core.scaler import scale_app
from core.config import MAX_REPLICAS_PER_APP

CPU_THRESHOLD = 60.0
MIN_SAMPLES = 5
CPU_EMERGENCY_THRESHOLD = 85.0


def predict_and_scale():
    for app_name, domain, status in list_apps():
        if status != "running":
            continue

        pattern = get_hourly_pattern(app_name, days=14)
        if not pattern:
            continue

        now = datetime.now()
        current_dow = str(now.weekday() + 1 if now.weekday() < 6 else 0)
        next_hour = str((now.hour + 1) % 24).zfill(2)

        upcoming = [row for row in pattern if row[0] == current_dow and row[1] == next_hour]
        if not upcoming:
            continue

        dow, hour, avg_cpu, avg_ram, sample_count = upcoming[0]
        if sample_count < MIN_SAMPLES:
            continue

        current_replicas = get_replicas(app_name)
        running_count = len([r for r in current_replicas if r[3] == "running"])

        if avg_cpu >= CPU_THRESHOLD and running_count < MAX_REPLICAS_PER_APP:
            logging.info(f"[predictor] Predicted peak for {app_name} at {next_hour}:00 (avg_cpu={avg_cpu}%) — scaling up")
            try:
                scale_app(app_name, app_name, running_count + 1)
            except Exception as e:
                logging.error(f"[predictor] scale_app failed for {app_name}: {e}")

        elif avg_cpu < CPU_THRESHOLD * 0.5 and running_count > 1:
            logging.info(f"[predictor] Load normalized for {app_name} — scaling down")
            try:
                scale_app(app_name, app_name, running_count - 1)
            except Exception as e:
                logging.error(f"[predictor] scale_app failed for {app_name}: {e}")


def reactive_check():
    for app_name, domain, status in list_apps():
        if status != "running":
            continue

        recent = get_recent_metrics(app_name, limit=1)
        if not recent:
            continue

        _, cpu, ram, _ = recent[0]
        current_replicas = get_replicas(app_name)
        running_count = len([r for r in current_replicas if r[3] == "running"])

        if cpu >= CPU_EMERGENCY_THRESHOLD and running_count < MAX_REPLICAS_PER_APP:
            logging.info(f"[reactive] {app_name} CPU={cpu}% — emergency scale up")
            try:
                scale_app(app_name, app_name, running_count + 1)
            except Exception as e:
                logging.error(f"[reactive] scale_app failed for {app_name}: {e}")


def run_forever():
    cycle = 0
    while True:
        try:
            reactive_check()
            if cycle % 15 == 0:
                predict_and_scale()
        except Exception as e:
            print(f"[scaling_predictor] error: {e}")
        cycle += 1
        time.sleep(60)


if __name__ == "__main__":
    run_forever()