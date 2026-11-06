# ☁️ PROJECT AVI // 24/7 CLOUD PRODUCTION DEPLOYMENT GUIDE
**Target Environment:** Oracle Always Free Ubuntu (x86_64 `VM.Standard.E2.1.Micro`) / Docker  
**Stack Components:** Neo4j 5 Community + Headless Wine MT5 (RPyC Bridge) + Jarvis Trading Cortex & 06:00 AM Cutoff Governor  
**Security Posture:** Zero exposed public ports (`127.0.0.1` change-locked behind SSH tunnel)

---

## ⚡ Complete Production Runbook

### Step 0: Create Mandatory 4 GB Swap File (Run BEFORE Docker)
Oracle's `E2.1.Micro` instance has 1 GB physical RAM. Docker builds and first-time Wine prefix initialization will trigger Linux OOM-killer without swap:
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify 4 GB swap active:
free -h
```

---

### Step 1: Clone Repository & Deploy Container Stack
```bash
git clone <your-repo-url> /opt/avi-project && cd /opt/avi-project
docker compose up -d
```

---

### Step 2: Establish Secure Combined SSH Tunnel
Run this single command from your local Windows PowerShell or terminal:
```powershell
ssh -i ~/.ssh/oracle_key -L 3000:127.0.0.1:3000 -L 8888:127.0.0.1:8888 ubuntu@<ORACLE_VM_PUBLIC_IP>
```
* Port `3000`: Web-VNC desktop for MT5 GUI.
* Port `8888`: Project AVI Alpha Observatory Dashboard.
* Both ports bind exclusively to `127.0.0.1` on the server—nothing is exposed to the public internet.

---

### Step 3: First-Time MT5 Authentication & RAM Optimization
1. Open your browser and navigate to:
   ```
   http://localhost:3000
   ```
2. Log in with Web-VNC credentials:
   - **User:** `admin` (or `${VNC_USER}`)
   - **Password:** `ftmo24x7` (or `${VNC_PASSWORD}`)
3. Inside the virtual desktop, MetaTrader 5 will be running.
4. **Log in to your FTMO Demo account:**
   - **Login:** Your FTMO Account Number
   - **Password:** Your FTMO Trader Password
   - **Server:** `FTMO-Demo`
5. **Apply RAM & CPU Optimizations (`Tools -> Options` or `Ctrl+O`):**
   - **Charts tab:** Set *Max bars in chart* to **`5000`** (saves ~200MB Wine RAM).
   - **Events tab:** **Uncheck** *Enable audio notifications* (eliminates Wine ALSA/PulseAudio CPU spikes).
   - **Server tab:** **Check** *Keep personal settings and data at startup*.
   - **Expert Advisors tab:** **Check** *Allow Algorithmic Trading*.
   - Click `OK`.
6. **Close your browser tab.**
   > **Permanent Persistence:** Because `/config` inside the MT5 container is bound to `./data/mt5-wine`, your terminal session, certificates, credentials, and settings remain permanently saved across container restarts.

---

## 🕒 Exact 06:00:00 AM IST Session Cutoff Guarantee
`TZ=Asia/Kolkata` is baked directly into `jarvis-core`.
* The system evaluates current time strictly according to Indian Standard Time regardless of where the physical cloud server is hosted.
* At **06:00:00 AM IST sharp**, `continuous_november_controller.py` executes market orders to close 100% of open positions to cash and generates the day's HTML dossier in `/app/reports/November/`.

---

## 🔍 Telemetry & Operational Verification Commands

### View Container Health
```bash
docker compose ps
```

### Stream Live Core Trading & Controller Logs
```bash
docker compose logs -f jarvis-core
```

### Stream MT5 Wine & RPyC Logs
```bash
docker compose logs -f mt5-wine
```

### View Live Alpha Observatory UI
Open your browser at:
```
http://localhost:8888
```
All cognitive thought cycles, swarm generation metrics, and active positions stream in real time.
