#!/usr/bin/env bash
# Restart the local server (port 8000). Uses a PID file: pkill -f would also match the calling shell.
cd "$(dirname "$0")/.."
PIDF=data/logs/server.pid
if [ -f $PIDF ]; then kill "$(cat $PIDF)" 2>/dev/null; sleep 1; fi
env -u PYTHONPATH .venv/bin/python -m uvicorn app.main:app --port 8000 > data/logs/server.txt 2>&1 &
echo $! > $PIDF
