#!/bin/bash

# Resilience OS - OMEGA ONE CLICK STARTUP
# ==========================================
# 1. Kills old dashboard server instances
# 2. Checks/Starts Ollama (optional)
# 3. Starts new Dashboard Server
# 4. Opens Browser

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT_DIR="$(dirname "$DIR")"
LOG_FILE="/tmp/omega_startup.log"

echo "🌑 RESILIENCE OS - GO DARK PROTOCOL INITIALIZING..." | tee $LOG_FILE

# 1. KILL OLD SERVER
echo "1. Cleaning up old processes..." | tee -a $LOG_FILE
pkill -f "dashboard_server.py" || echo "   - No old server found."

# 2. CHECK OLLAMA
echo "2. Checking AI Engine..." | tee -a $LOG_FILE
if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
    echo "   - Ollama is RUNNING. (Good)" | tee -a $LOG_FILE
else
    echo "   - Ollama is OFF. Starting it..." | tee -a $LOG_FILE
    # Try to start ollama if installed
    if command -v ollama >/dev/null; then
        ollama serve > /tmp/ollama.log 2>&1 &
        echo "   - Ollama starting in background..." | tee -a $LOG_FILE
    else
        echo "   - Ollama not found. AI features may be limited." | tee -a $LOG_FILE
    fi
fi

# 3. START DASHBOARD
echo "3. Starting Dashboard Server..." | tee -a $LOG_FILE
cd "$ROOT_DIR/.."
nohup python3 "OS/01_SCRIPTS/dashboard_server.py" > /tmp/dashboard_server.log 2>&1 &
SERVER_PID=$!

# Wait for port 3000
echo "   - Waiting for port 3000..." | tee -a $LOG_FILE
for i in {1..30}; do
    if lsof -i :3000 > /dev/null; then
        echo "   - Server ONLINE." | tee -a $LOG_FILE
        break
    fi
    sleep 1
done

# 4. OPEN BROWSER
echo "4. Opening Dashboard..." | tee -a $LOG_FILE
sleep 2
open "http://localhost:3000"

echo "✅ SYSTEM READY." | tee -a $LOG_FILE
