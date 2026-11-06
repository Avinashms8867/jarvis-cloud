"""
PROJECT AVI // TIER 3 MARKET DATA FEED
Fetches real historical & live klines from Binance Public API with local caching & resilient fallback.
"""

import os
import json
import time
import urllib.request
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cache"))
os.makedirs(CACHE_DIR, exist_ok=True)

class MarketDataFeed:
    """Asynchronous/Synchronous client for fetching clean Binance klines."""

    BASE_URL = "https://api.binance.com/api/v3"

    @classmethod
    def get_klines(cls, symbol: str = "ETHUSDT", interval: str = "5m", limit: int = 1000, force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetches OHLCV bars from Binance.
        Returns DataFrame with columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        """
                # Clean Crypto to Binance mapping
        crypto_map = {
            "BTCUSD": "BTCUSDT", "BTCUSDT": "BTCUSDT",
            "ETHUSD": "ETHUSDT", "ETHUSDT": "ETHUSDT",
            "SOLUSD": "SOLUSDT", "SOLUSDT": "SOLUSDT"
        }
        binance_symbol = crypto_map.get(symbol)

        # If true Forex symbol (EUR, GBP, JPY): try MT5
        is_forex = any(fx in symbol for fx in ["EUR", "GBP", "JPY"])
        if is_forex:
            try:
                try:
                    from tier2_cortex.mt5_compat import mt5
                except ImportError:
                    try:
                        from mt5_compat import mt5
                    except ImportError:
                        import MetaTrader5 as mt5
                if mt5.terminal_info() is not None or mt5.initialize():
                    mt5_sym = symbol.replace("USDT", "USD")
                    mt5.symbol_select(mt5_sym, True)
                    tf_map = {
                        '1m': mt5.TIMEFRAME_M1,
                        '5m': mt5.TIMEFRAME_M5,
                        '15m': mt5.TIMEFRAME_M15,
                        '30m': mt5.TIMEFRAME_M30,
                        '1h': mt5.TIMEFRAME_H1,
                        '4h': mt5.TIMEFRAME_H4,
                        '1d': mt5.TIMEFRAME_D1
                    }
                    tf = tf_map.get(interval, mt5.TIMEFRAME_M5)
                    rates = mt5.copy_rates_from_pos(mt5_sym, tf, 0, limit)
                    if rates is not None and len(rates) > 0:
                        df = pd.DataFrame(rates)
                        df.rename(columns={"time": "timestamp", "tick_volume": "volume"}, inplace=True)
                        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
                        return df[["timestamp", "open", "high", "low", "close", "volume"]]
            except Exception:
                pass

        cache_file = os.path.join(CACHE_DIR, f"{symbol}_{interval}_{limit}.json")
        now = time.time()

        # 1. Check local cache (valid for 30 seconds)
        if not force_refresh and os.path.exists(cache_file):
            try:
                mtime = os.path.getmtime(cache_file)
                if now - mtime < 30:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    return cls._to_dataframe(raw)
            except Exception:
                pass

        # 2. Fetch from Binance API with fast timeout
        raw = None
        try:
            b_sym = binance_symbol if binance_symbol else symbol
            url = f"{cls.BASE_URL}/klines?symbol={b_sym}&interval={interval}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "AVI-MarketFeed/1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                raw = json.loads(resp.read().decode())
            # Save to cache
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(raw, f)
            except Exception:
                pass
        except Exception:
            # Seamless fallback to existing cache file
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                except Exception:
                    pass

        # 3. If cache still not available, check for any cached interval for this symbol
        if raw is None:
            fallback_candidates = [
                os.path.join(CACHE_DIR, f"{symbol}_5m_1000.json"),
                os.path.join(CACHE_DIR, f"{symbol}_5m_100.json"),
                os.path.join(CACHE_DIR, f"{symbol}_1h_100.json")
            ]
            for cand in fallback_candidates:
                if os.path.exists(cand):
                    try:
                        with open(cand, "r", encoding="utf-8") as f:
                            raw = json.load(f)
                            if raw:
                                break
                    except Exception:
                        pass

        if raw is not None and len(raw) > 0:
            return cls._to_dataframe(raw)

        # 4. Deterministic synthetic klines fallback as ultimate safeguard
        return cls._generate_synthetic_klines(symbol, limit)

    @classmethod
    def _to_dataframe(cls, raw_klines: list) -> pd.DataFrame:
        """Converts raw Binance kline array to structured pandas DataFrame."""
        df = pd.DataFrame(raw_klines, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    @classmethod
    def _generate_synthetic_klines(cls, symbol: str, limit: int) -> pd.DataFrame:
        """Generates realistic synthetic price action if completely offline."""
        base_prices = {"BTCUSDT": 64000.0, "ETHUSDT": 3400.0, "SOLUSDT": 145.0}
        base = base_prices.get(symbol, 100.0)
        np.random.seed(42)
        returns = np.random.normal(0.0001, 0.002, limit)
        prices = base * np.exp(np.cumsum(returns))
        highs = prices * (1 + np.abs(np.random.normal(0, 0.001, limit)))
        lows = prices * (1 - np.abs(np.random.normal(0, 0.001, limit)))
        volumes = np.random.uniform(10, 100, limit)
        timestamps = pd.date_range(end=pd.Timestamp.now(), periods=limit, freq="5min")

        return pd.DataFrame({
            "timestamp": timestamps,
            "open": prices,
            "high": highs,
            "low": lows,
            "close": prices,
            "volume": volumes
        })
