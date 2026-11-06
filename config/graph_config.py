"""
PROJECT AVI // DUAL NEO4J CONFIGURATION
Manages connection credentials for both Local Community/Desktop and Cloud AuraDB.
"""

import os
from dataclasses import dataclass

def _load_env_file():
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip()
                        if k and not os.environ.get(k):
                            os.environ[k] = v
        except Exception:
            pass

_load_env_file()

@dataclass
class GraphConfig:
    # ── 1. Local Neo4j Instance (Primary Fast Cache) ──
    local_uri: str = os.getenv('LOCAL_NEO4J_URI', os.getenv('NEO4J_URI', 'bolt://127.0.0.1:7687'))
    local_user: str = os.getenv('LOCAL_NEO4J_USER', os.getenv('NEO4J_USER', 'neo4j'))
    local_password: str = os.getenv('LOCAL_NEO4J_PASSWORD', os.getenv('NEO4J_PASSWORD', 'password'))

    # ── 2. Cloud Neo4j AuraDB (Off-Site Persistent Mirror) ──
    aura_uri: str = os.getenv('AURA_NEO4J_URI', '')
    aura_user: str = os.getenv('AURA_NEO4J_USER', 'neo4j')
    aura_password: str = os.getenv('AURA_NEO4J_PASSWORD', '')

    # Sync policy
    enable_cloud_sync: bool = True
    async_cloud_mirror: bool = True

default_graph_config = GraphConfig()
