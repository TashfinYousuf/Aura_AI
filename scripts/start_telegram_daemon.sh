#!/bin/bash
# FILE: scripts/start_telegram_daemon.sh
# Runs Aura Telegram Bot in the background so it never dies when terminal closes.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

PID_FILE="$PROJECT_DIR/.telegram_bot.pid"
LOG_FILE="$PROJECT_DIR/telegram_bot.log"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️ Telegram Bot is already running in background (PID: $PID)."
        echo "📜 View logs with: tail -f telegram_bot.log"
        exit 0
    else
        rm "$PID_FILE"
    fi
fi

echo "🚀 Starting Aura Telegram Bot in background (daemon mode)..."
nohup ./venv/bin/python backend/run_telegram.py > "$LOG_FILE" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$PID_FILE"

echo "✅ Aura Telegram Bot started successfully in background!"
echo "🆔 PID: $BOT_PID (saved in .telegram_bot.pid)"
echo "📜 Live logs: tail -f telegram_bot.log"
echo "🛑 To stop: ./scripts/stop_telegram_daemon.sh"

