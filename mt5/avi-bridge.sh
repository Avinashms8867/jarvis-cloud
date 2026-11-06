#!/bin/bash
# PROJECT AVI // MT5 RPyC bridge on 64-bit Windows Python (port 8001), started by start.sh.
#
# Why 64-bit Python 3.11: the image's 32-bit Python 3.9 can only install MetaTrader5 5.0.36 (2021),
# which cannot talk to current terminal builds. Current MetaTrader5 wheels are 64-bit only.
# The bridge is avi_rpyc_server.py (rpyc classic server that pre-imports `datetime`, which
# mt5linux 0.1.9 clients assume), run under that Python. It is relaunched whenever nothing is
# listening on the port.
#
# NOTE: MetaTrader5.initialize() returns (-10005, 'IPC timeout') until the terminal is logged into
# a broker account. Log in once via the VNC desktop (port 3000); MT5 remembers it in /config.

PORT="${1:-8001}"
export WINEPREFIX="${WINEPREFIX:-/config/.wine}" WINEDEBUG="${WINEDEBUG:--all}"
PY='C:\Python311\python.exe'
PY_UNIX="$WINEPREFIX/drive_c/Python311/python.exe"
log() { echo "[avi-bridge] $*"; }

if [ ! -f "$PY_UNIX" ]; then
    log "installing 64-bit Python 3.11.9 into the Wine prefix..."
    curl -fsSL -o /tmp/py311.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    wine /tmp/py311.exe /quiet InstallAllUsers=0 'TargetDir=C:\Python311' PrependPath=0 \
        Include_test=0 Include_doc=0 Include_tcltk=0 Include_launcher=0
    rm -f /tmp/py311.exe
fi

if ! wine "$PY" -c "import MetaTrader5, rpyc, plumbum, numpy" >/dev/null 2>&1; then
    log "installing MetaTrader5 + rpyc into 64-bit Python..."
    wine "$PY" -m pip install --no-cache-dir --disable-pip-version-check \
        MetaTrader5==5.0.6231 "numpy<3" rpyc==6.0.2 plumbum
fi

while true; do
    if ! ss -tln | grep -q ":${PORT} "; then
        log "starting bridge on port ${PORT}"
        wine "$PY" 'Z:\Metatrader\avi_rpyc_server.py' "$PORT" &
    fi
    sleep 15
done
