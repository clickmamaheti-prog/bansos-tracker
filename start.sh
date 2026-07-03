#!/bin/bash
#############################################
# GPS Tracker Bot — Auto Start Script
# cd /root/gps-tracker-bot && ./start.sh
############################################=

cd "$(dirname "$0")"

# Config
export BOT_TOKEN="8813008108:***"
export BASE_URL="https://bansos.jokichannel.eu.org"
export NODE_OPTIONS="--max-old-space-size=256"

# Kill old processes
pkill -f "python3 bot.py" 2>/dev/null
sleep 1

# Start Cloudflare Tunnel (diprioritaskan)
if command -v cloudflared &>/dev/null; then
    cloudflared tunnel --config /root/.cloudflared/config.yml \
      --credentials-file /root/.cloudflared/8dc7779d-7dc1-4957-9839-41fe8f4a231a.json \
      run &
    sleep 3
    echo "🔗 Cloudflare Tunnel -> https://bansos.jokichannel.eu.org"
fi

# Reset DB if --reset flag
if [ "$1" == "--reset" ]; then
    rm -f tracker.db
    echo "💾 Database reset"
fi

# Start Bot
echo "🤖 Starting GPS Tracker Bot..."
echo "🌐 BASE_URL: $BASE_URL"
python3 bot.py
