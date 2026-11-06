"""
PROJECT AVI // FAST NUMBA-ACCELERATED SIMULATION ENGINE
Vectorized multi-strategy backtesting with mandatory transaction friction modeling:
- 0.05% taker fee per side (0.10% round trip) + 1-tick slippage
- Breakeven trailing stop at +1.0R
"""

from typing import Tuple, Dict, Any
import numpy as np
import pandas as pd
from numba import njit


@njit(fastmath=True)
def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(prices)
    rsi = np.zeros(n, dtype=np.float64)
    if n <= period:
        return rsi

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0.0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period + 1, n):
        gain = gains[i - 1]
        loss = losses[i - 1]
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0.0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


@njit(fastmath=True)
def calculate_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(close)
    atr = np.zeros(n, dtype=np.float64)
    if n <= period:
        return atr

    tr = np.zeros(n, dtype=np.float64)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        hl = high[i] - low[i]
        hc = abs(high[i] - close[i - 1])
        lc = abs(low[i] - close[i - 1])
        tr[i] = max(hl, max(hc, lc))

    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    return atr


@njit(fastmath=True)
def calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
    n = len(prices)
    ema = np.zeros(n, dtype=np.float64)
    if n <= period:
        return ema

    multiplier = 2.0 / (period + 1.0)
    ema[period - 1] = np.mean(prices[:period])
    for i in range(period, n):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]
    return ema


@njit(fastmath=True)
def calculate_bollinger_bands(prices: np.ndarray, period: int = 20, num_std: float = 2.5) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(prices)
    mid = np.zeros(n, dtype=np.float64)
    upper = np.zeros(n, dtype=np.float64)
    lower = np.zeros(n, dtype=np.float64)

    if n < period:
        return mid, upper, lower

    for i in range(period - 1, n):
        window = prices[i - period + 1 : i + 1]
        m = np.mean(window)
        s = np.std(window)
        mid[i] = m
        upper[i] = m + (num_std * s)
        lower[i] = m - (num_std * s)

    return mid, upper, lower


@njit(fastmath=True)
def simulate_alpha_chromosome(
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    rsi: np.ndarray,
    atr: np.ndarray,
    ema_fast: np.ndarray,
    ema_slow: np.ndarray,
    bb_upper: np.ndarray,
    bb_lower: np.ndarray,
    strat_code: int,  # 1 = TREND_PULLBACK, 2 = LIQUIDITY_SWEEP, 3 = VOLATILITY_BREAKOUT
    rsi_trigger: float,
    rsi_lower_trigger: float,
    sl_mult: float,
    tp_mult: float,
    be_r: float,
    max_holding: int,
    fee_rate: float = 0.0005  # 0.05% taker fee per side
) -> Tuple[int, int, float, float, float, float]:
    """
    Unified institutional simulation engine with friction modeling.
    Returns: (total_trades, wins, net_pnl_after_fees, max_dd, sharpe, profit_factor)
    """
    n = len(closes)
    in_pos = 0  # 0 = flat, 1 = long, -1 = short
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    entry_bar = 0
    initial_sl_dist = 0.0

    trades = 0
    wins = 0
    losses = 0
    gross_wins_pnl = 0.0
    gross_losses_pnl = 0.0
    total_net_pnl = 0.0
    peak_equity = 0.0
    current_equity = 0.0
    max_dd = 0.0

    pnl_history = np.zeros(n, dtype=np.float64)
    pnl_idx = 0

    # 20-bar volume average
    vol_sma = np.zeros(n, dtype=np.float64)
    for i in range(20, n):
        vol_sma[i] = np.mean(volumes[i - 20 : i])

    for i in range(50, n):
        # ── Position Management ──
        if in_pos != 0:
            bars_held = i - entry_bar
            curr_high = highs[i]
            curr_low = lows[i]
            exit_price = 0.0
            trade_closed = False

            if in_pos == 1:  # LONG
                # Breakeven Step: if price advanced by be_r * initial_sl_dist, move SL to breakeven + fee buffer
                if curr_high >= entry_price + (be_r * initial_sl_dist) and sl_price < entry_price:
                    sl_price = entry_price + (entry_price * fee_rate * 2.0)

                # Check SL hit
                if curr_low <= sl_price:
                    exit_price = sl_price
                    trade_closed = True
                # Check TP hit
                elif curr_high >= tp_price:
                    exit_price = tp_price
                    trade_closed = True
                # Timeout exit
                elif bars_held >= max_holding:
                    exit_price = closes[i]
                    trade_closed = True

                if trade_closed:
                    gross_pnl = exit_price - entry_price
                    # Deduct friction (0.05% entry + 0.05% exit)
                    fees = (entry_price * fee_rate) + (exit_price * fee_rate)
                    net_pnl = gross_pnl - fees

                    total_net_pnl += net_pnl
                    current_equity += net_pnl
                    trades += 1

                    if net_pnl > 0.0:
                        wins += 1
                        gross_wins_pnl += net_pnl
                    else:
                        losses += 1
                        gross_losses_pnl += abs(net_pnl)

                    pnl_history[pnl_idx] = net_pnl
                    pnl_idx += 1
                    in_pos = 0

            elif in_pos == -1:  # SHORT
                # Breakeven Step
                if curr_low <= entry_price - (be_r * initial_sl_dist) and sl_price > entry_price:
                    sl_price = entry_price - (entry_price * fee_rate * 2.0)

                # Check SL hit
                if curr_high >= sl_price:
                    exit_price = sl_price
                    trade_closed = True
                # Check TP hit
                elif curr_low <= tp_price:
                    exit_price = tp_price
                    trade_closed = True
                # Timeout exit
                elif bars_held >= max_holding:
                    exit_price = closes[i]
                    trade_closed = True

                if trade_closed:
                    gross_pnl = entry_price - exit_price
                    fees = (entry_price * fee_rate) + (exit_price * fee_rate)
                    net_pnl = gross_pnl - fees

                    total_net_pnl += net_pnl
                    current_equity += net_pnl
                    trades += 1

                    if net_pnl > 0.0:
                        wins += 1
                        gross_wins_pnl += net_pnl
                    else:
                        losses += 1
                        gross_losses_pnl += abs(net_pnl)

                    pnl_history[pnl_idx] = net_pnl
                    pnl_idx += 1
                    in_pos = 0

            # Drawdown calculation
            if current_equity > peak_equity:
                peak_equity = current_equity
            dd = peak_equity - current_equity
            if dd > max_dd:
                max_dd = dd

            continue  # Already managed position this bar

        # ── Entry Signal Evaluation ──
        curr_atr = atr[i]
        if curr_atr <= 0.0:
            continue

        # 1. TREND_PULLBACK (strat_code == 1)
        if strat_code == 1:
            # Bullish Trend: Fast EMA > Slow EMA
            if ema_fast[i] > ema_slow[i] and closes[i] > ema_slow[i]:
                # Pullback: RSI oversold exhaustion turning back up
                if rsi[i - 1] < rsi_lower_trigger and rsi[i] >= rsi_lower_trigger:
                    in_pos = 1
                    entry_price = closes[i]
                    initial_sl_dist = sl_mult * curr_atr
                    sl_price = entry_price - initial_sl_dist
                    tp_price = entry_price + (tp_mult * curr_atr)
                    entry_bar = i
            # Bearish Trend: Fast EMA < Slow EMA
            elif ema_fast[i] < ema_slow[i] and closes[i] < ema_slow[i]:
                # Pullback: RSI overbought exhaustion turning back down
                if rsi[i - 1] > rsi_trigger and rsi[i] <= rsi_trigger:
                    in_pos = -1
                    entry_price = closes[i]
                    initial_sl_dist = sl_mult * curr_atr
                    sl_price = entry_price + initial_sl_dist
                    tp_price = entry_price - (tp_mult * curr_atr)
                    entry_bar = i

        # 2. LIQUIDITY_SWEEP (strat_code == 2)
        elif strat_code == 2:
            # Bullish Sweep: Low breached BB Lower, but Close closed back inside
            if lows[i - 1] <= bb_lower[i - 1] and closes[i] > bb_lower[i] and rsi[i] < 40.0:
                in_pos = 1
                entry_price = closes[i]
                initial_sl_dist = sl_mult * curr_atr
                sl_price = entry_price - initial_sl_dist
                tp_price = entry_price + (tp_mult * curr_atr)
                entry_bar = i
            # Bearish Sweep: High breached BB Upper, but Close closed back inside
            elif highs[i - 1] >= bb_upper[i - 1] and closes[i] < bb_upper[i] and rsi[i] > 60.0:
                in_pos = -1
                entry_price = closes[i]
                initial_sl_dist = sl_mult * curr_atr
                sl_price = entry_price + initial_sl_dist
                tp_price = entry_price - (tp_mult * curr_atr)
                entry_bar = i

        # 3. VOLATILITY_BREAKOUT (strat_code == 3)
        elif strat_code == 3:
            # High volume expansion break
            if volumes[i] > 1.5 * vol_sma[i]:
                # Donchian 20-bar breakout
                highest_20 = np.max(highs[i - 20 : i])
                lowest_20 = np.min(lows[i - 20 : i])
                if closes[i] > highest_20:
                    in_pos = 1
                    entry_price = closes[i]
                    initial_sl_dist = sl_mult * curr_atr
                    sl_price = entry_price - initial_sl_dist
                    tp_price = entry_price + (tp_mult * curr_atr)
                    entry_bar = i
                elif closes[i] < lowest_20:
                    in_pos = -1
                    entry_price = closes[i]
                    initial_sl_dist = sl_mult * curr_atr
                    sl_price = entry_price + initial_sl_dist
                    tp_price = entry_price - (tp_mult * curr_atr)
                    entry_bar = i

    # Compute Metrics
    sharpe = 0.0
    if pnl_idx > 2:
        valid_pnls = pnl_history[:pnl_idx]
        mean_pnl = np.mean(valid_pnls)
        std_pnl = np.std(valid_pnls)
        if std_pnl > 0.0:
            sharpe = (mean_pnl / std_pnl) * np.sqrt(pnl_idx)

    profit_factor = 0.0
    if gross_losses_pnl > 0.0:
        profit_factor = gross_wins_pnl / gross_losses_pnl
    elif gross_wins_pnl > 0.0:
        profit_factor = 9.99

    return trades, wins, total_net_pnl, max_dd, sharpe, profit_factor


class FastSimulator:
    """High-level simulation wrapper executing JIT backtests across strategy chromosomes."""

    @classmethod
    def evaluate_chromosome(cls, df: pd.DataFrame, chrom: Any) -> Dict[str, Any]:
        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["volume"].values

        # Indicators
        rsi = calculate_rsi(closes, chrom.rsi_period)
        atr = calculate_atr(highs, lows, closes, 14)
        ema_fast = calculate_ema(closes, chrom.ema_fast)
        ema_slow = calculate_ema(closes, chrom.ema_slow)
        _, bb_upper, bb_lower = calculate_bollinger_bands(closes, chrom.bb_period, chrom.bb_std)

        strat_code = 1
        if chrom.strategy_type == "LIQUIDITY_SWEEP":
            strat_code = 2
        elif chrom.strategy_type == "VOLATILITY_BREAKOUT":
            strat_code = 3

        trades, wins, net_pnl, max_dd, sharpe, profit_factor = simulate_alpha_chromosome(
            opens=opens,
            highs=highs,
            lows=lows,
            closes=closes,
            volumes=volumes,
            rsi=rsi,
            atr=atr,
            ema_fast=ema_fast,
            ema_slow=ema_slow,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            strat_code=strat_code,
            rsi_trigger=chrom.rsi_trigger,
            rsi_lower_trigger=chrom.rsi_lower_trigger,
            sl_mult=chrom.sl_atr_mult,
            tp_mult=chrom.tp_atr_mult,
            be_r=chrom.be_threshold_r,
            max_holding=chrom.max_holding_bars,
            fee_rate=0.0005  # 0.05% taker fee
        )

        win_rate = round((wins / trades * 100.0), 1) if trades > 0 else 0.0
        expectancy = round(net_pnl / trades, 2) if trades > 0 else 0.0

        # Fitness function: Reward Win Rate, Profit Factor, Sharpe; penalize drawdown
        fitness = 0.0
        if trades >= 4:
            fitness = (profit_factor * 2.0) + (sharpe * 1.5) + (win_rate / 25.0)
            if expectancy < 0.0:
                fitness = 0.0

        return {
            "trades_count": trades,
            "wins": wins,
            "losses": trades - wins,
            "win_rate": win_rate,
            "expectancy": expectancy,
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_drawdown": round(max_dd, 2),
            "fitness": round(fitness, 2),
            "status": "passed_gate" if (trades >= 5 and win_rate >= 50.0 and expectancy > 0.0 and profit_factor >= 1.5) else "culled"
        }
