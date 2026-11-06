#!/bin/bash
# PROJECT AVI // MT5 RECOVERY
# Rebuilds jarvis-mt5 on Wine >= 11.6 (see Dockerfile.mt5 for the root cause).
# Usage:  bash fix_mt5.sh          # build + recreate + verify
#         bash fix_mt5.sh --win11  # also set the Wine prefix to Windows 11 (fallback if the error persists)
set -euo pipefail

echo "=========================================================="
echo "  PROJECT AVI // MT5 RECOVERY (Wine >= 11.6)"
echo "=========================================================="

# Wine's syscall emulation uses Linux Syscall User Dispatch: kernel >= 5.11 required.
kernel="$(uname -r)"
if [ "$(printf '%s\n' 5.11 "${kernel%%-*}" | sort -V | head -n1)" != "5.11" ]; then
    echo "FATAL: host kernel ${kernel} < 5.11; Wine cannot emulate MT5's direct syscalls here."
    exit 1
fi
echo "[1/4] Host kernel ${kernel} OK (>= 5.11)"

# The Wine build needs a few GB on the Docker data disk; apt fails with "exit code 100" when it runs out.
docker_root="$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo /var/lib/docker)"
free_gb="$(df -BG --output=avail "$docker_root" 2>/dev/null | tail -1 | tr -dc '0-9')"
echo "      Free space for Docker (${docker_root}): ${free_gb:-?} GB"
if [ -n "$free_gb" ] && [ "$free_gb" -lt 4 ]; then
    echo "FATAL: need >= 4 GB free for the Wine build. Free space first, e.g.:"
    echo "  docker builder prune -af"
    echo "  docker image rm gmag11/metatrader5_vnc:latest   # old base image, replaced by :2.3"
    echo "  docker system df                                 # see what else is using space"
    exit 1
fi

echo "[2/4] Building avi-mt5:wine11 (replaces Wine 10.0 with winehq-devel >= 11.6)..."
if ! docker compose build --progress=plain mt5-wine 2>&1 | tee mt5-build.log; then
    echo "=========================================================="
    echo "  BUILD FAILED. apt errors from mt5-build.log:"
    grep -nE '(^|#[0-9]+ [0-9.]+ )(E:|W:|Err:)|No space left|held|unmet|Unable to locate' mt5-build.log | tail -25 || true
    echo "=========================================================="
    exit 1
fi

echo "[3/4] Recreating jarvis-mt5 from the new image..."
docker compose up -d --force-recreate mt5-wine
sleep 5
docker exec jarvis-mt5 wine --version

if [ "${1:-}" = "--win11" ]; then
    echo "      Setting Wine prefix Windows version to win11..."
    docker exec -u abc -e WINEPREFIX=/config/.wine jarvis-mt5 \
        wine reg add 'HKCU\Software\Wine' /v Version /t REG_SZ /d win11 /f
    docker compose restart mt5-wine
fi

echo "[4/4] Container logs:"
sleep 5
docker logs jarvis-mt5 --tail 20
echo "=========================================================="
echo "  Open http://localhost:3000 - terminal64.exe should start without the debugger dialog."
echo "  If it still appears: bash fix_mt5.sh --win11"
echo "=========================================================="
