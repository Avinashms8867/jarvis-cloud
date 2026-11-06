"""
PROJECT AVI // COCKPIT & ALPHA OBSERVATORY SERVER (Port 8888)
Connects all 3 Tiers + FTMO MetaTrader 5 $100,000 Live Challenge Bridge:
- Tier 1: Agent 1 Conversational Assistant & Macro Catalyst Radar
- Tier 2: Agent 2 Thinking Core + FTMO Rule Governor & MT5 Bridge
- Tier 3: Agent 3 Swarm Engine (Multi-Strategy with 0.05% Friction Modeling)
- Memory: Dual Neo4j Knowledge Graph (Active-Active Replication + Mirror)
"""

import os
import sys
import json
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn

try:
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
except Exception:
    pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from tier2_cortex.dual_graph_memory import DualGraphMemory
from tier2_cortex.thinking_core import Agent2ThinkingCore
from tier2_cortex.ftmo_bridge import FTMOMT5Bridge
from tier3_evolution.swarm_engine import Agent3Swarm
from tier1_interface.catalyst_radar import MacroCatalystRadar
from tier1_interface.assistant import Agent1Assistant

PORT = 8888
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# ── Global Singletons ──
print("[BOOT] Initializing Singletons...", flush=True)
memory = DualGraphMemory()
swarm = Agent3Swarm(population_size=30, memory_engine=memory)
ftmo_bridge = FTMOMT5Bridge()
ftmo_connected = ftmo_bridge.connect()
agent2 = Agent2ThinkingCore(memory_engine=memory, swarm_engine=swarm, ftmo_bridge=ftmo_bridge, live_ftmo=True)
agent1 = Agent1Assistant(thinking_core=agent2, swarm_engine=swarm, memory_engine=memory, ftmo_bridge=ftmo_bridge)
print(f"[BOOT] Initialized! FTMO Connected: {ftmo_connected}", flush=True)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class AviHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/thinking":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            payload = {
                "active": agent2.is_thinking,
                "current_step": agent2.step_counter,
                "thoughts": agent2.get_recent_thoughts(),
                "latest_thought": agent2.get_latest_thought(),
                "active_signals": agent2.active_signals,
                "portfolio": agent2.portfolio.get_summary()
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif self.path == "/api/ftmo":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            payload = ftmo_bridge.get_status()
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif self.path == "/api/swarm":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            payload = {
                "generation": swarm.generation,
                "total_agents": len(swarm.population),
                "population": swarm.get_population_summary(),
                "champions": [c.to_dict() for c in swarm.promoted_champions]
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif self.path == "/api/reports":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            reports_path = os.path.abspath(os.path.join(ROOT_DIR, "..", "JARVIS_SYSTEM", "FTMO_OVERNIGHT_REPORTS.json"))
            if not os.path.exists(reports_path):
                reports_path = os.path.join(os.path.dirname(__file__), "..", "..", "JARVIS_SYSTEM", "FTMO_OVERNIGHT_REPORTS.json")
            
            reports = []
            if os.path.exists(reports_path):
                try:
                    with open(reports_path, "r", encoding="utf-8") as rf:
                        reports = json.load(rf)
                except Exception as e:
                    pass

            payload = {
                "reports": list(reversed(reports)),
                "total_snapshots": len(reports),
                "ftmo_account": ftmo_bridge.get_status() if ftmo_bridge else {}
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif self.path == "/api/macro": 
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            climate = MacroCatalystRadar.evaluate_macro_climate()
            self.wfile.write(json.dumps(climate).encode("utf-8"))
            return

        elif self.path == "/api/memory":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            payload = {
                "status": memory.get_status(),
                "snapshot": memory.get_graph_snapshot(),
                "recent_thoughts": memory.query_recent_thoughts(8)
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            payload = {
                "system": "Operational",
                "graph_status": memory.get_status(),
                "thinking_step": agent2.step_counter,
                "swarm_generation": swarm.generation,
                "portfolio": agent2.portfolio.get_summary(),
                "ftmo": ftmo_bridge.get_status()
            }
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/disarm":
            agent2.live_ftmo = False
            print("[ALERT] Live trading DISARMED via API at 02:30 AM cutoff.", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "live_ftmo": False}).encode("utf-8"))
            return

        if self.path == "/api/arm":
            agent2.live_ftmo = True
            print("[ALERT] Live trading ARMED via API.", flush=True)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "live_ftmo": True}).encode("utf-8"))
            return

        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                query = data.get("query", "")
                reply = agent1.answer_query(query)
            except Exception as e:
                reply = f"Error processing query: {e}"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
            return

        return super().do_POST()


def background_evolution():
    time.sleep(3)
    while True:
        try:
            swarm.run_epoch()
        except Exception as e:
            print(f"[SWARM] Epoch error: {e}", flush=True)
        time.sleep(25)


def main():
    os.makedirs(STATIC_DIR, exist_ok=True)
    server = ThreadedHTTPServer(("0.0.0.0", PORT), AviHandler)

    # Start cognitive and evolutionary background threads
    agent2.start(interval_seconds=10)
    evo_thread = threading.Thread(target=background_evolution, daemon=True)
    evo_thread.start()

    print("=======================================================", flush=True)
    print(f"  [ONLINE] PROJECT AVI ALPHA OBSERVATORY (PORT {PORT})", flush=True)
    print(f"  FTMO MT5: #{ftmo_bridge.login} on {ftmo_bridge.server} ({'CONNECTED' if ftmo_connected else 'STANDBY / ACTIVE GOVERNOR'})", flush=True)
    print(f"  URL: http://localhost:{PORT}/", flush=True)
    print("=======================================================", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server shutting down.", flush=True)
        server.server_close()


if __name__ == "__main__":
    main()
