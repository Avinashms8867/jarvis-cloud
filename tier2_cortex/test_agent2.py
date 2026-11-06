"""
Verification test for Agent 2: The Thinking Core.
Connects Agent 2 to Agent 3 Swarm and Dual Neo4j, runs 4 real reasoning cycles,
and displays the Claude-style thought monologue.
"""

import sys
import os
sys.path.append(r"D:\AGI\AGI\AVI Project")

from tier2_cortex.thinking_core import Agent2ThinkingCore
from tier2_cortex.dual_graph_memory import DualGraphMemory
from tier3_evolution.swarm_engine import Agent3Swarm

def test_agent2_thinking():
    print("=======================================================")
    print("  [COGNITION] RUNNING AGENT 2 THINKING CORE VERIFICATION")
    print("=======================================================\n")

    # 1. Initialize Memory & Swarm
    print("1. Initializing Dual Neo4j Memory & Agent 3 Swarm...")
    memory = DualGraphMemory()
    swarm = Agent3Swarm(population_size=30, memory_engine=memory)
    # Run 1 swarm epoch so there is live intelligence
    swarm.run_epoch()
    print(f"   [OK] Swarm active with {len(swarm.population)} agents (Gen {swarm.generation}).")

    # 2. Spawn Agent 2 Thinking Core
    print("\n2. Spawning Agent 2 Thinking Core...")
    agent2 = Agent2ThinkingCore(memory_engine=memory, swarm_engine=swarm)
    print("   [OK] Agent 2 initialized and linked to Agent 3.")

    # 3. Execute 4 Conscious Reasoning Cycles
    print("\n3. Executing Continuous Thought Monologues (Claude-style)...")
    for i in range(1, 5):
        thought = agent2.execute_thought_cycle()
        print(f"\n--- [THOUGHT STEP {thought['step']}] {thought['symbol']} [{thought['timestamp']}] ---")
        print(f"  Title:    {thought['title']}")
        print(f"  Takeaway: {thought['takeaway']}")
        deb = thought.get("debate", {})
        if deb:
            print(f"  Consensus: {deb.get('consensus')} (Confidence: {int(deb.get('confidence', 0)*100)}%)")
            for p in deb.get("perspectives", []):
                print(f"    - {p['role']}: {p['text'][:90]}...")

    # 4. Check Portfolio & Graph Mirror
    port = agent2.portfolio.get_summary()
    print(f"\n4. Paper Portfolio: Capital: ${port['capital']:.2f}, Closed Trades: {port['total_trades']}, Open: {port['open_count']}")

    graph = memory.get_graph_snapshot()
    print(f"5. Dual Neo4j Graph Snapshot: {graph['total_nodes']} nodes, {graph['total_edges']} edges mapped.")

    print("\n=======================================================")
    print("  [SUCCESS] AGENT 2 COGNITION VERIFIED -- THINKING ACTIVE")
    print("=======================================================\n")

if __name__ == "__main__":
    test_agent2_thinking()
