#!/usr/bin/env python3
"""
simple_scheduler.py

A basic scheduler: at specified times, run external scripts.
Add more entries to JOBS to schedule additional scripts.
"""

import time
import subprocess
import schedule
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# ------------------------------
# CONFIGURATION: Add your jobs here
# ------------------------------
# Each entry is a tuple: (HH:MM, path_to_script)
JOBS = [
    ("16:57", "emailscript.py"),
]

def run_script(path: str):
    """Invoke the given script as a subprocess."""
    script = Path(path)
    if not script.exists():
        logging.error(f"Script not found: {path}")
        return
    logging.info(f"Starting script: {path}")
    try:
        # If it's a Python script, you can explicitly call python3:
        # cmd = ["python3", str(script)]
        # Otherwise, rely on shebang/executable bit:
        cmd = [str(script)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"Finished {path} (exit {result.returncode})")
        if result.stdout:
            logging.info(f"  Output:\n{result.stdout}")
        if result.stderr:
            logging.warning(f"  Errors:\n{result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Script {path} failed (exit {e.returncode})")
        logging.error(e.stderr or e.stdout)

def schedule_jobs():
    """Register all jobs with the scheduler."""
    for t, script in JOBS:
        # schedule.every().day.at() uses 24‑hour "HH:MM" format
        schedule.every().day.at(t).do(run_script, path=script)
        logging.info(f"Scheduled {script} at {t} daily")

def main():
    logging.info("Scheduler starting up")
    schedule_jobs()
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Scheduler stopped by user")

if __name__ == "__main__":
    main()
