#!/bin/bash
set -e

echo "==========================================================="
echo "  [STARTUP] PROJECT AVI 24/7 LINUX CLOUD RUNTIME"
echo "  Architecture: Linux / Docker (Python 3.12)"
echo "  Neo4j URI:    ${LOCAL_NEO4J_URI:-bolt://neo4j:7687}"
echo "  MT5 Bridge:   ${MT5_BRIDGE_HOST:-mt5-wine}:${MT5_BRIDGE_PORT:-8001}"
echo "  Reports Dir:  ${REPORTS_DIR:-/app/reports}"
echo "==========================================================="

mkdir -p "${REPORTS_DIR:-/app/reports}" /app/November

# Wait for Neo4j if configured
if [ -n "$LOCAL_NEO4J_URI" ]; then
    NEO_HOST=$(echo "$LOCAL_NEO4J_URI" | sed -e 's|^.*://||' -e 's|:.*$||')
    NEO_PORT=$(echo "$LOCAL_NEO4J_URI" | sed -e 's|^.*:||' -e 's|/.*$||')
    echo "[WAIT] Checking Neo4j at ${NEO_HOST}:${NEO_PORT:-7687}..."
    for i in {1..30}; do
        if nc -z "$NEO_HOST" "${NEO_PORT:-7687}" 2>/dev/null; then
            echo "[ONLINE] Neo4j reachable!"
            break
        fi
        sleep 1
    done
fi

# Wait for MT5 Wine Bridge if configured
if [ -n "$MT5_BRIDGE_HOST" ]; then
    echo "[WAIT] Checking MT5 Wine Bridge at ${MT5_BRIDGE_HOST}:${MT5_BRIDGE_PORT:-8001}..."
    for i in {1..30}; do
        if nc -z "$MT5_BRIDGE_HOST" "${MT5_BRIDGE_PORT:-8001}" 2>/dev/null; then
            echo "[ONLINE] MT5 Wine Bridge reachable!"
            break
        fi
        sleep 1
    done
fi

echo "[LAUNCH] Starting Cockpit Server & Alpha Observatory (server.py)..."
python ui/server.py &
PID_SERVER=$!

echo "[LAUNCH] Starting Continuous November Controller..."
if [ -f "continuous_november_controller.py" ]; then
    python continuous_november_controller.py &
    PID_CONTROLLER=$!
else
    echo "[WARN] continuous_november_controller.py not in current workdir, skipping controller."
    PID_CONTROLLER=0
fi

# Trap termination signals to shut down gracefully
trap 'echo "[SHUTDOWN] Stopping services..."; kill $PID_SERVER 2>/dev/null || true; [ $PID_CONTROLLER -ne 0 ] && kill $PID_CONTROLLER 2>/dev/null || true; exit 0' SIGTERM SIGINT

echo "[MONITOR] Both services running (Server PID: $PID_SERVER, Controller PID: $PID_CONTROLLER)."

# Dual-process supervisor loop: exit if either process dies
while true; do
    if ! kill -0 $PID_SERVER 2>/dev/null; then
        echo "[FATAL] ui/server.py exited unexpectedly! Exiting container for Docker restart..."
        [ $PID_CONTROLLER -ne 0 ] && kill -9 $PID_CONTROLLER 2>/dev/null || true
        exit 1
    fi

    if [ $PID_CONTROLLER -ne 0 ] && ! kill -0 $PID_CONTROLLER 2>/dev/null; then
        echo "[FATAL] continuous_november_controller.py exited unexpectedly! Exiting container for Docker restart..."
        kill -9 $PID_SERVER 2>/dev/null || true
        exit 1
    fi

    sleep 5
done

