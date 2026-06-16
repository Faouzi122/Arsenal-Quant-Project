#!/bin/bash
# Stop script for Antigravity Engine - Real L402 Gateway Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="${SCRIPT_DIR}/gateway.pid"

if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if ps -p ${PID} > /dev/null; then
        echo "[SYSTEM] Terminating L402 Gateway Server (PID ${PID})..."
        kill ${PID}
        sleep 1
        if ps -p ${PID} > /dev/null; then
            echo "[WARNING] Server did not exit cleanly. Force killing..."
            kill -9 ${PID}
        fi
        echo "[SUCCESS] Gateway Server stopped."
    else
        echo "[INFO] Gateway was not running."
    fi
    rm "${PID_FILE}"
else
    echo "[INFO] No gateway.pid file found."
fi
