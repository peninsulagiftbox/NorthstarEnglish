#!/usr/bin/env python3
"""Keep an auditable parent PID even when Node changes its process title."""
import signal
import subprocess
import sys
import time

child = subprocess.Popen(sys.argv[2:])
stop_requested = False


def stop(_signum, _frame):
    # Do not call wait/poll from a handler: it may interrupt a held subprocess lock.
    global stop_requested
    stop_requested = True


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
while not stop_requested and child.poll() is None:
    time.sleep(.2)
if stop_requested and child.poll() is None:
    child.terminate()
    try:
        child.wait(timeout=15)
    except subprocess.TimeoutExpired:
        child.kill()  # Only the exact child this supervisor created.
        child.wait()
sys.exit(0 if stop_requested else (child.returncode or 0))
