#!/bin/bash
# Start script for Antigravity Engine - Real L402 Gateway Server
# Runs with low process priority (nice/ionice) to preserve Lenovo Celeron CPU

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${SCRIPT_DIR}/gateway.pid"

if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if ps -p ${PID} > /dev/null; then
        echo "[INFO] Gateway already running with PID ${PID}"
        exit 0
    fi
fi

echo "[SYSTEM] Starting Real L402 Gateway Server in background..."
# Run with nice/ionice
nice -n 19 ionice -c 3 python3 "${SCRIPT_DIR}/l402_gateway_real.py" > "${SCRIPT_DIR}/logs/gateway_production.log" 2>&1 &
NEW_PID=$!

echo ${NEW_PID} > "${PID_FILE}"
echo "[SUCCESS] Gateway started with PID ${NEW_PID}. Logs: logs/gateway_production.log"
sleep 1
