# MT5 on Wine: handover (2026-11-07)

State at handover: the full chain works in the Codespace. The engine reports
`[BOOT] Initialized! FTMO Connected: True`, `initialize()` returns `True (1, 'Success')` in about 1 s,
and FTMO-Demo account #1515102715 is connected with algo trading enabled.
No trading logic (`tier1_interface/`, `tier2_cortex/`, `tier3_evolution/`) was changed. All changes are infrastructure.

## 1. What changed tonight

### Root causes, in the order they were hit

| # | Symptom | Cause | Fix |
|---|---|---|---|
| 1 | `terminal64.exe`: "A debugger has been found running in your system" | Current MT5 builds have a protector that makes direct syscalls. Wine < 11.6 can't intercept them (WineHQ bug 58043, fixed in 11.6). The base image ships Wine 10.0. | `Dockerfile.mt5` installs `winehq-devel` 11.10 and fails the build if the version is below 11.6. Needs host kernel >= 5.11. |
| 2 | Wine upgrade failed: apt exit 100, `NO_PUBKEY 76F1A20FF987672F` | `gmag11/metatrader5_vnc:2.3` references `/etc/apt/keyrings/winehq-archive.key` but doesn't contain the file. | `Dockerfile.mt5` re-downloads the WineHQ key and pins fingerprint `D43F640145369C51D786DDEA76F1A20FF987672F`. |
| 3 | Nothing listening on port 8001 | The old `fix_mt5.sh` sed patch ran `python -m rpyc.cli.rpyc_classic`. In rpyc 6 that module defines `main()` but never calls it, so it exits 0 immediately. | Replaced by `mt5/avi-bridge.sh` and `mt5/avi_rpyc_server.py`. |
| 4 | Bridge ran but MT5 calls failed | The image's Wine Python is 32-bit 3.9, which only supports `MetaTrader5==5.0.36` (2021). That package also failed to import with numpy 2. | 64-bit Python 3.11.9 at `C:\Python311` in the prefix, with `MetaTrader5==5.0.6231`. |
| 5 | `initialize()` → `(-10005, 'IPC timeout')` after 60 s | **The terminal reports "initializing" until it is logged into a broker account.** It isn't a Wine bug: it also reproduces on native Windows. The generic MetaQuotes terminal doesn't know FTMO's servers. | In the GUI: File → Open an Account → search "FTMO" → FTMO Global Markets Ltd → Connect with an existing account → server **FTMO-Demo**, password saved. Ruled out first: path argument, `DISPLAY`, 32 vs 64-bit, and a fresh prefix. |
| 6 | `jarvis-core` image had `mt5linux 1.1.1` ("No container runtime available") | The image was built before the `mt5linux==0.1.9` pin. The rebuild then failed twice: on unreadable `./data/mt5-wine` in the build context, and on mt5linux 0.1.9's stale dependency pins (`numpy==1.21.4`, `rpyc==5.0.1`, ...). | Added `.dockerignore` excluding `data/`. `Dockerfile.linux` installs `mt5linux==0.1.9 --no-deps`. |
| 7 | Remote `NameError: name 'datetime' is not defined` | The mt5linux 0.1.9 client only runs `import MetaTrader5 as mt5` on the server, then sends `eval` strings like `mt5.history_deals_get(datetime.datetime(...))`. | `mt5/avi_rpyc_server.py` pre-imports `datetime` in every connection's namespace. |

### Commits (all on `main`)

- `d17a487`, `f40001e`, `0e84e3a`: `Dockerfile.mt5` (Wine >= 11.6 and the WineHQ key). `fix_mt5.sh` builds and recreates.
- `fe0cca3`: `mt5/start.sh` and `mt5/avi-bridge.sh` mounted into the container. Healthcheck added; `jarvis-core` waits for `service_healthy`.
- `a115d70`: `.dockerignore`.
- `8214c1e`: `Dockerfile.linux` installs mt5linux with `--no-deps`.
- `3e33a58`: `mt5/avi_rpyc_server.py` replaces the generated mt5linux server.

### State that lives only in `./data/mt5-wine` (the persistent `/config` volume, not in git)

- **Wine prefix:** `/config/.wine`. It was created under Wine 10 and auto-upgraded. It still has harmless earlier tweaks: `winedbg` DllOverride, AeDebug, and `WINEDLLOVERRIDES=mscoree=` in compose.
- **64-bit Python:** `C:\Python311` with MetaTrader5 5.0.6231, numpy, rpyc 6.0.2 and plumbum. `avi-bridge.sh` reinstalls them if missing.
- **FTMO login:** the server list (from the "Open an Account" search) and the saved login for #1515102715 on FTMO-Demo. The terminal reconnects by itself on restart; this was verified after recreating the container.
- **Legacy 32-bit Python:** `C:\Program Files (x86)\Python39-32` still exists, now with numpy 1.26.4. `start.sh` steps 5–6 still maintain it. It is unused.

## 2. How the bridge is structured

```
jarvis-core (Linux, Python 3.12)
  tier2_cortex/ftmo_bridge.py → tier2_cortex/mt5_compat.py
    mt5linux 0.1.9: MetaTrader5(host="mt5-wine", port=8001)     ← connects ONCE, at import time
        │  RPyC "classic" protocol, rpyc 6.0.2 on both sides
        ▼
jarvis-mt5 (gmag11/metatrader5_vnc:2.3 + Wine 11.10, image avi-mt5:wine11)
  wine C:\Python311\python.exe Z:\Metatrader\avi_rpyc_server.py 8001
    AviSlaveService (rpyc SlaveService; namespace pre-imports datetime + MetaTrader5)
        │  MetaTrader5 5.0.6231 → named-pipe IPC (same prefix /config/.wine, display :1)
        ▼
  terminal64.exe build 6306 ── logged in → FTMO-Demo (FTMO Global Markets Ltd)
```

**Startup inside jarvis-mt5:** the KasmVNC autostart runs `/Metatrader/start.sh`, which is the repo's `mt5/start.sh` mounted read-only. It is the image's own script with only step 7 changed.

1. Mono, MT5 install if missing, launch `terminal64.exe`, legacy 32-bit Python steps.
2. Step 7 runs `/Metatrader/avi-bridge.sh 8001`:
   - Installs Python 3.11 and the packages if missing.
   - Then loops forever: every 15 s, if nothing is listening on `:8001`, it starts `avi_rpyc_server.py`.

**Compose wiring:**
- `mt5-wine` healthcheck: `ss -tln | grep -q ':8001 '`, with a 600 s start period.
- `jarvis-core` has `depends_on: mt5-wine: service_healthy`.

**Two constraints to keep in mind:**
- `mt5_compat` creates its connection once, at import. **If `jarvis-mt5` restarts while the stack is running, run `docker compose restart jarvis-core`.** Nothing reconnects automatically.
  - On a Codespace or Docker restart, the containers restart on their own, without `depends_on` ordering. `entrypoint.sh` therefore waits up to 300 s for `mt5-wine:8001` (commit `b32c4a5`); a cold start takes about 150 s.
  - Before that commit, the engine gave up after 30 s and booted with `FTMO Connected: False`.
- `initialize()` returns `(-10005, 'IPC timeout')` whenever the terminal isn't logged in or connected. Check the login first.

## 3. Health checks

Run these from `/workspaces/jarvis-cloud` in the Codespace.

```bash
# 1. Containers + bridge health
docker compose ps
docker inspect -f '{{.State.Health.Status}}' jarvis-mt5          # healthy
docker exec jarvis-mt5 wine --version                            # wine-11.10 (must be >= 11.6)

# 2. GUI: terminal running, logged in, no debugger dialog
docker exec jarvis-mt5 ps -eo pid,etime,args | grep '[t]erminal64'
docker exec -u abc -e DISPLAY=:1 jarvis-mt5 sh -c \
  'xwininfo -root -tree | grep -E "\"[^\"]+\": \(" | grep -vE "Default IME|Openbox"'
#   expect: "1515102715 - FTMO-Demo: Demo Account - Hedge - FTMO Global Markets Ltd"
#   a "terminal64.exe" dialog window here means the debugger check fired (Wine < 11.6)
#   visual check: Codespaces Ports tab → 3000 → KasmVNC (user admin, password = VNC_PASSWORD)

# 3. Terminal journal (UTF-16): connection/authorization lines
docker exec jarvis-mt5 sh -c 'd="/config/.wine/drive_c/Program Files/MetaTrader 5/logs"; \
  iconv -f UTF-16LE -t UTF-8 "$d/$(ls -t "$d" | grep -v metaeditor | head -1)" | tr -d "\r" | tail -20'

# 4. Port 8001: check INSIDE the container. A host-side probe is unreliable, because
#    docker-proxy accepts TCP connections even when nothing is listening behind it.
docker exec jarvis-mt5 ss -tln | grep ':8001 '
docker logs jarvis-mt5 2>&1 | grep -E 'avi-bridge|avi-rpyc|7/7' | tail -5

# 5. End-to-end through the same client the engine uses
docker exec jarvis-core python -c "
from mt5linux import MetaTrader5; import datetime
m = MetaTrader5(host='mt5-wine', port=8001)
print('initialize', m.initialize(), m.last_error())
ti, ai = m.terminal_info(), m.account_info()
print('connected', ti.connected, '| algo trading', ti.trade_allowed, '| account', ai.login, ai.server, ai.balance)
now = datetime.datetime.now(); print('deals 7d', len(m.history_deals_get(now - datetime.timedelta(days=7), now) or []))
print('BTCUSD', m.symbol_select('BTCUSD', True), m.symbol_info_tick('BTCUSD'))"
#   expect: initialize True (1, 'Success'); connected True; algo trading True

# 6. Engine side
docker logs jarvis-core 2>&1 | grep -E 'BOOT|ONLINE|FTMO' | tail -10
#   expect: "[ONLINE] MT5 Wine Bridge reachable!", "[BOOT] Initialized! FTMO Connected: True"
```

### Troubleshooting

| Symptom | Action |
|---|---|
| Debugger dialog | `wine --version` < 11.6. Rebuild from `Dockerfile.mt5` (needs about 7 GB free). |
| `(-10005, 'IPC timeout')` | The terminal isn't logged in. In KasmVNC: File → Login to Trade Account → server FTMO-Demo. If FTMO servers are missing from the list: File → Open an Account → search "FTMO". |
| `NameError: datetime` | The bridge isn't `avi_rpyc_server.py`. Check `docker logs jarvis-mt5 \| grep avi-rpyc`. |
| Engine shows FTMO disconnected after an MT5 restart | `docker compose restart jarvis-core` |
| Nothing on `:8001` | `avi-bridge.sh` retries every 15 s. Check `docker logs jarvis-mt5` for `[avi-bridge]` lines. |

## 4. Production host: Azure VM (since 2026-11-09)

The stack now runs 24/7 on an Azure VM. **The Codespace no longer runs anything:** its containers were removed with
`docker compose down`, and its `data/` folder is kept only as a backup. Never run the stack in two places at once,
because both would trade account #1515102715.

| | |
|---|---|
| VM | `avi-vm`, resource group `avi-rg`, Central India, `Standard_B2als_v2` (2 vCPU, 4 GB), Ubuntu 24.04, 64 GB StandardSSD |
| Access | `ssh -i ~/.ssh/avi_azure avi@20.219.128.198`. Key auth only; the NSG opens only port 22. |
| Repo | `~/jarvis-cloud`. Run docker with `sudo`. |
| Swap | 2 GB `/swapfile`, `vm.swappiness=10` (an emergency net, not RAM) |
| Secrets | `~/jarvis-cloud/.env`, mode 600. FTMO_MT5_*, NEO4J_PASSWORD and VNC_USER/VNC_PASSWORD (random, VM-only). |
| MT5 data | `./data/mt5-wine`, copied from the Codespace: prefix, Python 3.11 and the saved FTMO-Demo login |
| Usage | About 1.8 GB RAM in use, about 2 GB available. Engine about 0.3 GB, MT5 about 0.45 GB, Neo4j about 0.57 GB. |

- **GUI and Observatory:** `ssh -i ~/.ssh/avi_azure -L 3000:127.0.0.1:3000 -L 8888:127.0.0.1:8888 avi@20.219.128.198`,
  then open http://localhost:3000 (VNC) and http://localhost:8888. Get the VNC password with `grep VNC_ ~/jarvis-cloud/.env`.
- **The health checks in section 3** work the same on the VM; prefix the docker commands with `sudo`.
- **`.env` gotcha:** docker compose expands `$VAR` inside `.env` values. The FTMO password contains `$`, so it must be
  single-quoted (`FTMO_MT5_PASSWORD='...'`). Unquoted, it was silently truncated, and `initialize(login, password, server)`
  failed with `(-6, 'Terminal: Authorization failed')`, which also logged the terminal out.
- **Credentials:** since commit `34213c8`, `ftmo_bridge.py` reads FTMO_MT5_* from the environment instead of hardcoded
  values. **The old password is still in public git history**, so rotate it.
- **Neo4j on the VM started empty**, with a new random password. Migrate the PC graph here, not to the Codespace.

## 5. Open items and cautions

- **Codespace.** It's no longer used for running the stack. It idles out after 30 min. Its disk was nearly full, so don't run `fix_mt5.sh` there.
- **Azure credit.** The $100 student credit at about $18/month for the VM lasts about 5 months. When the credit runs out, Azure stops the VM.
- **Password rotation.** Rotate the FTMO demo password; the old one is in the public git history. After rotating, update `~/jarvis-cloud/.env` on the VM and run `sudo docker compose up -d jarvis-core`.
- **Neo4j migration.** Migrating the local PC graph to the VM is pending.
- **Shell pitfall when debugging.** `pkill -f <pattern>` inside `sh -c '...'` matches the shell's own command line and kills it. Kill by PID, or use a `[b]racket` pattern.
