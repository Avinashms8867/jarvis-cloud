"""
PROJECT AVI // TIER 3: EVOLUTIONARY SWARM ENGINE
Maintains a 30-agent population exploring multi-strategy Alpha setups.
Tests on real live Binance klines, culls bottom 30%, mutates top 30%,
and promotes champions passing the institutional gate into Dual Neo4j.
"""

from __future__ import annotations
import os
import json
import random
import logging
from typing import List, Dict, Any, Optional

from tier3_evolution.strategy_chromosome import StrategyChromosome
from tier3_evolution.market_feed import MarketDataFeed
from tier3_evolution.fast_simulator import FastSimulator

logger = logging.getLogger("avi.tier3.swarm")


class Agent3Swarm:
    """Tier 3 Swarm Controller managing tournament cycles."""

    def __init__(self, population_size: int = 30, memory_engine=None):
        self.pop_size = population_size
        self.memory = memory_engine
        self.generation: int = self._load_generation_from_neo4j()
        self.population: List[StrategyChromosome] = []
        self.promoted_champions: List[StrategyChromosome] = []
        self._init_population()

    def _load_generation_from_neo4j(self) -> int:
        """Queries Neo4j directly for the highest evolved generation."""
        if self.memory and hasattr(self.memory, "get_latest_swarm_generation"):
            try:
                gen = self.memory.get_latest_swarm_generation()
                if gen > 1:
                    logger.info(f"[SWARM] Directly loaded Generation {gen} from Neo4j.")
                    return gen
            except Exception as e:
                logger.warning(f"[SWARM] Could not load generation from Neo4j: {e}")
        return 1

    def _init_population(self) -> None:
        """Initializes balanced population across 3 assets and 3 quantitative archetypes."""
        symbols = ["ETHUSDT", "BTCUSDT", "SOLUSDT"]
        archetypes = ["TREND_PULLBACK", "LIQUIDITY_SWEEP", "VOLATILITY_BREAKOUT"]

        for i in range(self.pop_size):
            sym = symbols[i % len(symbols)]
            arch = archetypes[i % len(archetypes)]
            agent_id = f"W{i+1:02d}-G{self.generation}"
            self.population.append(StrategyChromosome.create_random(agent_id, sym, arch))

    def run_epoch(self) -> None:
        """Executes one tournament generation across all 30 agents."""
        logger.info(f"[SWARM] Commencing Tournament Generation {self.generation} (Friction: 0.05% taker fees)...")

        # Fetch live market data for each symbol
        market_data = {
            "ETHUSDT": MarketDataFeed.get_klines("ETHUSDT", interval="5m", limit=1000),
            "BTCUSDT": MarketDataFeed.get_klines("BTCUSDT", interval="5m", limit=1000),
            "SOLUSDT": MarketDataFeed.get_klines("SOLUSDT", interval="5m", limit=1000)
        }

        # 1. Backtest all agents with transaction friction
        for chrom in self.population:
            df = market_data.get(chrom.symbol)
            if df is None or len(df) < 100:
                continue

            results = FastSimulator.evaluate_chromosome(df, chrom)
            chrom.trades_count = results["trades_count"]
            chrom.wins = results["wins"]
            chrom.losses = results["losses"]
            chrom.win_rate = results["win_rate"]
            chrom.expectancy = results["expectancy"]
            chrom.profit_factor = results["profit_factor"]
            chrom.sharpe_ratio = results["sharpe_ratio"]
            chrom.max_drawdown = results["max_drawdown"]
            chrom.fitness = results["fitness"]
            chrom.status = results["status"]

            # Save passing champions to Dual Neo4j
            if chrom.status == "passed_gate":
                self.promoted_champions.append(chrom)
                if self.memory:
                    self.memory.save_strategy(
                        name=chrom.agent_id,
                        symbol=chrom.symbol,
                        entry_rule=chrom.to_dna_string(),
                        sl_tp=f"SL={chrom.sl_atr_mult}xATR, TP={chrom.tp_atr_mult}xATR",
                        win_rate=chrom.win_rate,
                        expectancy=chrom.expectancy,
                        status="passed_gate"
                    )

        # 2. Sort by fitness (descending)
        self.population.sort(key=lambda c: c.fitness, reverse=True)

        # 3. Cull bottom 30%
        cull_count = int(self.pop_size * 0.3)
        survivors = self.population[:-cull_count]

        # 4. Mutate top 30% to replace culled losers
        top_performers = survivors[:cull_count]
        new_offspring = []
        for i, parent in enumerate(top_performers):
            child = parent.mutate(mutation_rate=0.3)
            child.agent_id = f"W{self.pop_size - cull_count + i + 1:02d}-G{self.generation + 1}"
            child.generation = self.generation + 1
            new_offspring.append(child)

        self.population = survivors + new_offspring
        self.generation += 1

    def get_population_summary(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self.population]
