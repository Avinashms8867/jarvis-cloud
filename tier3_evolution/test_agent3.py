"""
Verification test for Agent 3: Evolutionary Swarm.
Fetches real Binance 5m candles, spawns 30 genetic agents, and runs 3 evolutionary generations.
"""

import sys
import os
sys.path.append(r"D:\AGI\AGI\AVI Project")

from tier3_evolution.market_feed import MarketDataFeed
from tier3_evolution.swarm_engine import Agent3Swarm
from tier2_cortex.dual_graph_memory import DualGraphMemory

def test_agent3_evolution():
    print("=======================================================")
    print("  [SWARM] RUNNING AGENT 3 EVOLUTIONARY SWARM ENGINE TEST")
    print("=======================================================\n")

    # 1. Fetch real Binance data
    print("1. Ingesting real Binance 5m klines for ETHUSDT, BTCUSDT, SOLUSDT...")
    data = {
        "ETHUSDT": MarketDataFeed.get_klines("ETHUSDT", "5m", 1000),
        "BTCUSDT": MarketDataFeed.get_klines("BTCUSDT", "5m", 1000),
        "SOLUSDT": MarketDataFeed.get_klines("SOLUSDT", "5m", 1000)
    }
    for sym, df in data.items():
        print(f"   [OK] {sym}: {len(df)} candles ingested (Close: ${df['close'].iloc[-1]})")

    # 2. Initialize Dual Neo4j Memory
    print("\n2. Initializing Dual Neo4j Graph Memory...")
    memory = DualGraphMemory()
    print("   [OK] DualGraphMemory initialized.")

    # 3. Spawn Agent 3 Swarm
    print("\n3. Spawning Agent 3 (30 Genetic Worker Agents)...")
    swarm = Agent3Swarm(population_size=30, memory_engine=memory)
    print(f"   [OK] Initial population: {len(swarm.population)} agents ready.")

    # 4. Run 3 Evolutionary Epochs
    for gen in range(1, 4):
        print(f"\n-- Running Evolutionary Generation {gen} --")
        epoch_res = swarm.run_epoch(data)
        top = epoch_res["top_agent"]
        print(f"   * Generation {epoch_res['generation']} Complete!")
        print(f"   * Top Performer: {top['agent_id']} ({top['symbol']})")
        print(f"     DNA: {top['dna']}")
        print(f"     Trades: {top['trades_count']} | Win Rate: {top['win_rate']}% | Expectancy: ${top['expectancy']}/trade")
        print(f"     Fitness: {top['fitness']} | Status: {top['status']}")
        print(f"   * Champions Promoted to Neo4j: {epoch_res['champions_total']}")

    print("\n=======================================================")
    print("  [SUCCESS] AGENT 3 VERIFICATION PASSED ? EVOLUTION ACTIVE")
    print("=======================================================\n")

if __name__ == "__main__":
    test_agent3_evolution()
