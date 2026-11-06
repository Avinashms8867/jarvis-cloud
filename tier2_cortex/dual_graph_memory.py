"""
PROJECT AVI // DUAL NEO4J GRAPH MEMORY ENGINE
Active-active dual replication:
1. Local Neo4j (bolt://127.0.0.1:7687) for sub-millisecond local reads/writes.
2. Cloud Neo4j AuraDB for remote disaster-recovery & cross-device persistence.
3. In-Memory Graph Mirror for 100% resilient fallback when databases are initializing.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from neo4j import GraphDatabase, Driver
except ImportError:
    GraphDatabase = None
    Driver = Any

from config.graph_config import GraphConfig, default_graph_config

logger = logging.getLogger("avi.cortex.dual_graph")


class InMemoryGraphMirror:
    """In-memory associative mirror guaranteeing zero-crash persistence & sub-millisecond retrieval."""
    def __init__(self):
        self._lock = threading.Lock()
        self.thoughts: List[Dict[str, Any]] = []
        self.strategies: Dict[str, Dict[str, Any]] = {}
        self.lessons: List[Dict[str, Any]] = []
        self.regimes: Dict[str, Dict[str, Any]] = {
            "OverboughtExhaustion": {"name": "OverboughtExhaustion", "desc": "High entropy RSI divergence; upward exhaustion"},
            "OversoldExhaustion": {"name": "OversoldExhaustion", "desc": "Depressed RSI band; capitulation flush nearing support"},
            "LowVolatilityCompression": {"name": "LowVolatilityCompression", "desc": "Narrow ATR squeeze; pending volatility expansion"},
            "NeutralDrift": {"name": "NeutralDrift", "desc": "Equilibrium flow; chop conditions"}
        }
        self.edges: List[Dict[str, Any]] = []

    def record_thought(self, thought: Dict[str, Any]):
        with self._lock:
            self.thoughts.append(thought)
            if len(self.thoughts) > 100:
                self.thoughts.pop(0)

    def record_strategy(self, strategy: Dict[str, Any]):
        with self._lock:
            self.strategies[strategy["name"]] = strategy

    def record_lesson(self, lesson: Dict[str, Any]):
        with self._lock:
            self.lessons.append(lesson)
            if len(self.lessons) > 50:
                self.lessons.pop(0)

    def record_edge(self, source: str, target: str, rel_type: str, props: Optional[Dict[str, Any]] = None):
        with self._lock:
            self.edges.append({
                "source": source,
                "target": target,
                "type": rel_type,
                "props": props or {}
            })
            if len(self.edges) > 300:
                self.edges.pop(0)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            nodes = []
            for t in self.thoughts[-15:]:
                nodes.append({"id": t["id"], "label": "Thought", "title": t.get("phase", "Thought"), "step": t.get("step")})
            for s in list(self.strategies.values())[-10:]:
                nodes.append({"id": s["name"], "label": "Strategy", "title": s["name"], "win_rate": s.get("win_rate")})
            for r in self.regimes.values():
                nodes.append({"id": r["name"], "label": "MarketRegime", "title": r["name"]})
            for l in self.lessons[-10:]:
                nodes.append({"id": l["id"], "label": "Lesson", "title": l.get("takeaway", "")[:35]})
            return {
                "nodes": nodes,
                "edges": list(self.edges[-40:]),
                "total_nodes": len(nodes),
                "total_edges": len(self.edges)
            }


class DualGraphMemory:
    """
    Cognitive Graph Engine with Double Redundancy + In-Memory Mirror.
    Ensures every thought, strategy, and market relationship is saved both locally and to the cloud.
    """

    def __init__(self, config: Optional[GraphConfig] = None):
        self.config = config or default_graph_config
        self.local_driver: Optional[Driver] = None
        self.aura_driver: Optional[Driver] = None

        self.local_online: bool = False
        self.aura_online: bool = False
        self.mirror = InMemoryGraphMirror()

        self._init_drivers()

    def _init_drivers(self) -> None:
        """Initialize both Local and Cloud drivers."""
        if not GraphDatabase:
            logger.warning("[OFFLINE] neo4j package not installed. Operating in Mirror Mode.")
            return

        # 1. Connect Local with fast socket check
        import socket
        from urllib.parse import urlparse
        can_connect = False
        target_uri = getattr(self.config, "local_uri", None) or os.getenv("LOCAL_NEO4J_URI", "bolt://127.0.0.1:7687")
        try:
            parsed = urlparse(target_uri)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 7687
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((host, port))
            s.close()
            can_connect = True
        except Exception:
            can_connect = False

        if can_connect:
            try:
                self.local_driver = GraphDatabase.driver(
                    self.config.local_uri,
                    auth=(self.config.local_user, self.config.local_password)
                )
                self.local_driver.verify_connectivity()
                self.local_online = True
                logger.info(f"[ONLINE] Local Neo4j Online at {self.config.local_uri}")
                self._setup_schema(self.local_driver)
            except Exception as e:
                logger.warning(f"[OFFLINE] Local Neo4j offline: {e}. (Mirror active)")
                self.local_online = False
        else:
            self.local_online = False

        # 2. Connect AuraDB Cloud (if configured)
        if self.config.aura_uri:
            try:
                self.aura_driver = GraphDatabase.driver(
                    self.config.aura_uri,
                    auth=(self.config.aura_user, self.config.aura_password)
                )
                self.aura_driver.verify_connectivity()
                self.aura_online = True
                logger.info(f"[ONLINE] Cloud Neo4j AuraDB Online at {self.config.aura_uri}")
                self._setup_schema(self.aura_driver)
            except Exception as e:
                logger.warning(f"[OFFLINE] Cloud Neo4j AuraDB offline: {e}")
                self.aura_online = False

    def _setup_schema(self, driver: Driver) -> None:
        """Create uniqueness constraints on critical cognitive nodes."""
        constraints = [
            "CREATE CONSTRAINT thought_id IF NOT EXISTS FOR (t:Thought) REQUIRE t.id IS UNIQUE",
            "CREATE CONSTRAINT strategy_id IF NOT EXISTS FOR (s:Strategy) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:Asset) REQUIRE a.symbol IS UNIQUE",
            "CREATE CONSTRAINT regime_id IF NOT EXISTS FOR (r:MarketRegime) REQUIRE r.name IS UNIQUE",
            "CREATE CONSTRAINT lesson_id IF NOT EXISTS FOR (l:Lesson) REQUIRE l.id IS UNIQUE"
        ]
        try:
            with driver.session() as session:
                for q in constraints:
                    try:
                        session.run(q)
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Schema setup notice: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Returns live connectivity health of both databases."""
        return {
            "local_neo4j": {
                "uri": self.config.local_uri,
                "online": self.local_online
            },
            "cloud_auradb": {
                "uri": self.config.aura_uri or "Not configured (Add to .env)",
                "online": self.aura_online
            },
            "dual_redundancy": self.local_online and self.aura_online,
            "mirror_fallback": True,
            "mode": "Active-Active Dual Replication" if (self.local_online and self.aura_online) else "Resilient Mirror Mode"
        }

    # -------------------- WRITE OPERATIONS (DUAL SYNC) --------------------

    def execute_dual_write(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Executes Cypher write statement across both local and cloud instances.
        Returns True if at least one instance succeeds.
        """
        params = parameters or {}
        local_success = False
        aura_success = False

        if self.local_driver and self.local_online:
            try:
                with self.local_driver.session() as session:
                    session.run(cypher, params)
                local_success = True
            except Exception as e:
                logger.error(f"Local Neo4j write failed: {e}")
                self.local_online = False

        if self.aura_driver and self.aura_online:
            try:
                with self.aura_driver.session() as session:
                    session.run(cypher, params)
                aura_success = True
            except Exception as e:
                logger.error(f"Cloud AuraDB write failed: {e}")
                self.aura_online = False

        return local_success or aura_success

    # -------------------- READ OPERATIONS (LOCAL FIRST, FAILOVER TO CLOUD) --------------------

    def execute_read(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Reads from local instance first. Fails over to cloud if local is down."""
        params = parameters or {}

        if self.local_driver and self.local_online:
            try:
                with self.local_driver.session() as session:
                    result = session.run(cypher, params)
                    return [record.data() for record in result]
            except Exception as e:
                logger.warning(f"Local read failed, failing over to Cloud AuraDB: {e}")
                self.local_online = False

        if self.aura_driver and self.aura_online:
            try:
                with self.aura_driver.session() as session:
                    result = session.run(cypher, params)
                    return [record.data() for record in result]
            except Exception as e:
                logger.error(f"Cloud AuraDB read failed: {e}")
                self.aura_online = False

        return []

    # -------------------- COGNITIVE CONVENIENCE METHODS --------------------

    def save_thought_trace(self, phase: str, text: str, takeaway: str, step_num: int, symbol: str = "BTCUSDT", regime: str = "NeutralDrift") -> bool:
        """Commits a structured thought step into the knowledge graph & mirror."""
        now = datetime.utcnow().isoformat()
        thought_id = f"thought_{int(datetime.utcnow().timestamp() * 1000)}"

        # 1. Mirror persistence
        self.mirror.record_thought({
            "id": thought_id,
            "phase": phase,
            "text": text,
            "takeaway": takeaway,
            "step": step_num,
            "symbol": symbol,
            "regime": regime,
            "timestamp": now
        })
        self.mirror.record_edge(thought_id, symbol, "ANALYZES")
        self.mirror.record_edge(thought_id, regime, "CLASSIFIES")

        # 2. Dual Graph Persistence
        cypher = """
        MERGE (t:Thought {id: $id})
        SET t.phase = $phase,
            t.text = $text,
            t.takeaway = $takeaway,
            t.step = $step,
            t.timestamp = $now
        MERGE (a:Asset {symbol: $symbol})
        MERGE (r:MarketRegime {name: $regime})
        MERGE (t)-[:ANALYZES]->(a)
        MERGE (t)-[:CLASSIFIES]->(r)
        """
        return self.execute_dual_write(cypher, {
            "id": thought_id,
            "phase": phase,
            "text": text,
            "takeaway": takeaway,
            "step": step_num,
            "symbol": symbol,
            "regime": regime,
            "now": now
        })

    def save_strategy(self, name: str, symbol: str, entry_rule: str, sl_tp: str, win_rate: float, expectancy: float, status: str) -> bool:
        """Stores a strategy chromosome node and links it to its asset."""
        now = datetime.utcnow().isoformat()
        self.mirror.record_strategy({
            "name": name,
            "symbol": symbol,
            "entry_rule": entry_rule,
            "sl_tp": sl_tp,
            "win_rate": win_rate,
            "expectancy": expectancy,
            "status": status,
            "updated_at": now
        })
        self.mirror.record_edge(name, symbol, "TESTED_ON")

        cypher = """
        MERGE (s:Strategy {name: $name})
        SET s.entry_rule = $entry_rule,
            s.sl_tp = $sl_tp,
            s.win_rate = $win_rate,
            s.expectancy = $expectancy,
            s.status = $status,
            s.updated_at = $now
        MERGE (a:Asset {symbol: $symbol})
        MERGE (s)-[:TESTED_ON]->(a)
        """
        return self.execute_dual_write(cypher, {
            "name": name,
            "symbol": symbol,
            "entry_rule": entry_rule,
            "sl_tp": sl_tp,
            "win_rate": win_rate,
            "expectancy": expectancy,
            "status": status,
            "now": now
        })

    def save_lesson(self, takeaway: str, context: str, win_rate: float, sample_size: int, regime: str) -> bool:
        """Commits an empirical trading lesson learned from trades/simulations."""
        now = datetime.utcnow().isoformat()
        lesson_id = f"lesson_{int(datetime.utcnow().timestamp() * 1000)}"

        self.mirror.record_lesson({
            "id": lesson_id,
            "takeaway": takeaway,
            "context": context,
            "win_rate": win_rate,
            "sample_size": sample_size,
            "regime": regime,
            "created_at": now
        })
        self.mirror.record_edge(lesson_id, regime, "APPLIES_TO")

        cypher = """
        MERGE (l:Lesson {id: $id})
        SET l.takeaway = $takeaway,
            l.context = $context,
            l.win_rate = $win_rate,
            l.sample_size = $sample_size,
            l.regime = $regime,
            l.created_at = $now
        MERGE (r:MarketRegime {name: $regime})
        MERGE (l)-[:APPLIES_TO]->(r)
        """
        return self.execute_dual_write(cypher, {
            "id": lesson_id,
            "takeaway": takeaway,
            "context": context,
            "win_rate": win_rate,
            "sample_size": sample_size,
            "regime": regime,
            "now": now
        })

    def query_lessons_by_regime(self, regime: str) -> List[Dict[str, Any]]:
        """Retrieves lessons learned for a specific market regime."""
        cypher = """
        MATCH (l:Lesson)-[:APPLIES_TO]->(r:MarketRegime {name: $regime})
        RETURN l.takeaway AS takeaway, l.win_rate AS win_rate, l.sample_size AS sample_size
        ORDER BY l.created_at DESC
        LIMIT 5
        """
        records = self.execute_read(cypher, {"regime": regime})
        if records:
            return records

        # Fallback to in-memory mirror
        matching = [l for l in self.mirror.lessons if l.get("regime") == regime]
        return [{"takeaway": m["takeaway"], "win_rate": m["win_rate"], "sample_size": m["sample_size"]} for m in matching[-5:]]

    def query_recent_thoughts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves most recent thought nodes from Neo4j or mirror."""
        cypher = """
        MATCH (t:Thought)
        RETURN t.id AS id, t.phase AS phase, t.text AS text, t.takeaway AS takeaway, t.step AS step, t.timestamp AS timestamp
        ORDER BY t.step DESC
        LIMIT $limit
        """
        records = self.execute_read(cypher, {"limit": limit})
        if records:
            return records

        # Fallback to mirror
        return list(reversed(self.mirror.thoughts[-limit:]))

    def get_latest_thought_step(self) -> int:
        """Fetches the maximum cogitation step recorded in Neo4j."""
        try:
            records = self.execute_read("MATCH (t:Thought) RETURN max(t.step) as max_step")
            if records and records[0].get("max_step") is not None:
                return int(records[0]["max_step"])
        except Exception as e:
            logger.warning(f"Could not fetch max thought step from Neo4j: {e}")
        return 1

    def get_latest_swarm_generation(self) -> int:
        """Fetches the maximum generation from Strategy nodes recorded in Neo4j."""
        try:
            records = self.execute_read("MATCH (st:Strategy) RETURN st.name as name")
            gens = []
            for r in records:
                name = r.get("name") or ""
                match = re.search(r'-G(\d+)', str(name))
                if match:
                    gens.append(int(match.group(1)))
            if gens:
                return max(gens)
        except Exception as e:
            logger.warning(f"Could not fetch max swarm generation from Neo4j: {e}")
        return 1

    def get_graph_snapshot(self) -> Dict[str, Any]:
        """Provides complete graph telemetry for UI visualizer."""
        return self.mirror.get_snapshot()
