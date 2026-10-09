#!/bin/bash
# FILE: scripts/stop_telegram_daemon.sh
# Stops the background Aura Telegram Bot daemon.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PID_FILE="$PROJECT_DIR/.telegram_bot.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "ℹ️ No running Telegram Bot PID file found."
    # Also check if any rogue run_telegram.py process is running
    PIDS=$(pgrep -f "run_telegram.py")
    if [ -n "$PIDS" ]; then
        echo "Killing running instance(s): $PIDS"
        kill -9 $PIDS
        echo "✅ Stopped."
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" > /dev/null 2>&1; then
    echo "🛑 Stopping Telegram Bot (PID: $PID)..."
    kill "$PID"
    sleep 1
    if ps -p "$PID" > /dev/null 2>&1; then
        kill -9 "$PID"
    fi
    rm "$PID_FILE"
    echo "✅ Aura Telegram Bot stopped."
else
    echo "ℹ️ Telegram Bot process $PID was not running."
    rm "$PID_FILE"
fi

