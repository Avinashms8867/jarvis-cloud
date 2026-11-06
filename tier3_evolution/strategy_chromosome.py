"""
PROJECT AVI // ALPHA STRATEGY CHROMOSOME
Defines institutional genetic DNA across 3 distinct quantitative archetypes:
1. TREND_PULLBACK: Trend confirmation (EMA 50/200) + RSI momentum exhaustion entry
2. LIQUIDITY_SWEEP: Bollinger 2.5-sigma envelope breach + wick rejection
3. VOLATILITY_BREAKOUT: ATR compression + volume surge expansion break
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class StrategyChromosome:
    agent_id: str
    symbol: str
    strategy_type: str  # "TREND_PULLBACK" | "LIQUIDITY_SWEEP" | "VOLATILITY_BREAKOUT"
    
    # Quantitative Parameters
    rsi_period: int = 14
    rsi_trigger: float = 65.0       # Threshold for pullback/exhaustion
    rsi_lower_trigger: float = 35.0
    ema_fast: int = 20
    ema_slow: int = 50
    ema_trend: int = 200
    bb_period: int = 20
    bb_std: float = 2.5
    vol_surge_mult: float = 1.6
    donchian_period: int = 20

    # Risk Parameters (Strict Volatility Bounds)
    sl_atr_mult: float = 1.8        # Minimum 1.5x - 2.5x ATR
    tp_atr_mult: float = 3.6        # Minimum 1:2 R:R (3.0x - 5.0x ATR)
    be_threshold_r: float = 1.0     # Move to breakeven at 1.0R profit
    max_holding_bars: int = 48      # Max 4 hours on 5m bars

    # Fitness & Empirical Performance (Post-Fee)
    generation: int = 1
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    expectancy: float = 0.0         # Dollars per trade post-friction
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    fitness: float = 0.0
    status: str = "evaluating"      # "evaluating" | "passed_gate" | "culled"

    @classmethod
    def create_random(cls, agent_id: str, symbol: str, strategy_type: str = "TREND_PULLBACK") -> StrategyChromosome:
        """Instantiates a randomized chromosome within institutional quantitative ranges."""
        if strategy_type == "TREND_PULLBACK":
            return cls(
                agent_id=agent_id,
                symbol=symbol,
                strategy_type="TREND_PULLBACK",
                rsi_period=random.choice([9, 14, 21]),
                rsi_trigger=round(random.uniform(58.0, 68.0), 1),
                rsi_lower_trigger=round(random.uniform(32.0, 42.0), 1),
                ema_fast=random.choice([10, 20]),
                ema_slow=random.choice([50, 100]),
                ema_trend=200,
                sl_atr_mult=round(random.uniform(1.5, 2.2), 2),
                tp_atr_mult=round(random.uniform(3.2, 5.0), 2),
                be_threshold_r=1.0,
                max_holding_bars=random.choice([36, 48, 72])
            )
        elif strategy_type == "LIQUIDITY_SWEEP":
            return cls(
                agent_id=agent_id,
                symbol=symbol,
                strategy_type="LIQUIDITY_SWEEP",
                bb_period=20,
                bb_std=round(random.uniform(2.2, 2.8), 2),
                rsi_period=14,
                rsi_trigger=round(random.uniform(68.0, 75.0), 1),
                rsi_lower_trigger=round(random.uniform(25.0, 32.0), 1),
                sl_atr_mult=round(random.uniform(1.4, 1.9), 2),
                tp_atr_mult=round(random.uniform(2.8, 4.2), 2),
                be_threshold_r=0.9,
                max_holding_bars=random.choice([24, 36, 48])
            )
        else:  # VOLATILITY_BREAKOUT
            return cls(
                agent_id=agent_id,
                symbol=symbol,
                strategy_type="VOLATILITY_BREAKOUT",
                donchian_period=random.choice([15, 20, 30]),
                vol_surge_mult=round(random.uniform(1.4, 2.0), 2),
                sl_atr_mult=round(random.uniform(1.8, 2.5), 2),
                tp_atr_mult=round(random.uniform(3.8, 6.0), 2),
                be_threshold_r=1.2,
                max_holding_bars=random.choice([48, 72, 96])
            )

    def mutate(self, mutation_rate: float = 0.25) -> StrategyChromosome:
        """Applies Gaussian perturbation to numeric hyperparameters."""
        mutated = StrategyChromosome(
            agent_id=f"{self.agent_id}_m",
            symbol=self.symbol,
            strategy_type=self.strategy_type,
            rsi_period=self.rsi_period,
            rsi_trigger=self.rsi_trigger,
            rsi_lower_trigger=self.rsi_lower_trigger,
            ema_fast=self.ema_fast,
            ema_slow=self.ema_slow,
            ema_trend=self.ema_trend,
            bb_period=self.bb_period,
            bb_std=self.bb_std,
            vol_surge_mult=self.vol_surge_mult,
            donchian_period=self.donchian_period,
            sl_atr_mult=self.sl_atr_mult,
            tp_atr_mult=self.tp_atr_mult,
            be_threshold_r=self.be_threshold_r,
            max_holding_bars=self.max_holding_bars,
            generation=self.generation + 1
        )

        if random.random() < mutation_rate:
            mutated.sl_atr_mult = max(1.5, min(2.5, round(self.sl_atr_mult + random.gauss(0, 0.15), 2)))
        if random.random() < mutation_rate:
            mutated.tp_atr_mult = max(3.0, min(6.0, round(self.tp_atr_mult + random.gauss(0, 0.3), 2)))
        if random.random() < mutation_rate:
            mutated.rsi_trigger = max(55.0, min(75.0, round(self.rsi_trigger + random.gauss(0, 1.5), 1)))
        if random.random() < mutation_rate:
            mutated.rsi_lower_trigger = max(25.0, min(45.0, round(self.rsi_lower_trigger + random.gauss(0, 1.5), 1)))

        return mutated

    def to_dna_string(self) -> str:
        rr = round(self.tp_atr_mult / self.sl_atr_mult, 1)
        if self.strategy_type == "TREND_PULLBACK":
            return f"TREND_PULLBACK: EMA({self.ema_fast}/{self.ema_slow}) + RSI({self.rsi_period}) | SL={self.sl_atr_mult}xATR | TP={self.tp_atr_mult}xATR (1:{rr})"
        elif self.strategy_type == "LIQUIDITY_SWEEP":
            return f"LIQUIDITY_SWEEP: BB(20, {self.bb_std}s) + RSI({self.rsi_period}) | SL={self.sl_atr_mult}xATR | TP={self.tp_atr_mult}xATR (1:{rr})"
        else:
            return f"VOL_BREAKOUT: Donchian({self.donchian_period}) + Vol>{self.vol_surge_mult}x | SL={self.sl_atr_mult}xATR | TP={self.tp_atr_mult}xATR (1:{rr})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "symbol": self.symbol,
            "strategy_type": self.strategy_type,
            "dna": self.to_dna_string(),
            "generation": self.generation,
            "trades_count": self.trades_count,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "expectancy": self.expectancy,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "fitness": self.fitness,
            "status": self.status
        }
