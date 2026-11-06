#!/bin/bash
set -e

echo "=========================================================="
echo "  PROJECT AVI // AUTONOMOUS MT5 CLOUD RECOVERY SCRIPT     "
echo "=========================================================="

# 1. Recreate mt5-wine container with full capabilities
echo "[1/5] Recreating jarvis-mt5 container with SYS_PTRACE and WINEDLLOVERRIDES..."
docker compose up -d --force-recreate mt5-wine

# Wait 3 seconds for container to spin up
sleep 3

# 2. Patch start.sh inside container to use Wine RPyC server
echo "[2/5] Patching /Metatrader/start.sh for RPyC bridge..."
docker exec jarvis-mt5 sed -i 's/python3 -m mt5linux.*python.exe \&/$wine_executable python -m rpyc.cli.rpyc_classic --host 0.0.0.0 -p $mt5server_port \&/' /Metatrader/start.sh

# 3. Install mt5linux 0.1.9 without broken dependencies
echo "[3/5] Installing mt5linux 0.1.9 in Linux environment..."
docker exec jarvis-mt5 pip install --break-system-packages --no-cache-dir --no-deps mt5linux==0.1.9 || true

# 4. Install Wine-Staging 11.10 (Fixes WineHQ Bug 58043 anti-debug check)
echo "[4/5] Upgrading to Wine-Staging 11.10 (Upstream Anti-Debug Bypass)..."
docker exec jarvis-mt5 bash -c "apt-get update && apt-get install --allow-downgrades -y winehq-staging wine-staging wine-staging-amd64 wine-staging-i386"

# 5. Fix permissions and restart mt5-wine
echo "[5/5] Normalizing /config permissions and restarting MT5..."
docker exec jarvis-mt5 chown -R abc:abc /config || true
docker compose restart mt5-wine

echo "=========================================================="
echo "  RECOVERY COMPLETE! Container logs:"
echo "=========================================================="
sleep 5
docker logs jarvis-mt5 --tail 20
