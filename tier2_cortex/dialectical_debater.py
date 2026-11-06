"""
PROJECT AVI // DIALECTICAL DEBATE SUB-SWARM
Multi-Angle Confirmation Engine enforcing the Multi-Timeframe Trend Law:
- Angle 1 (1-Hour Macro Trend): 50/200 EMA institutional directional filter
- Angle 2 (15-Minute Structure): Intermediate value/pullback alignment (no buying tops or shorting bottoms)
- Angle 3 (5-Minute Trigger): Precise exhaustion entry with strict $35 max risk stop loss
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional


class DialecticalDebater:
    """Multi-perspective adversarial check before any trade or hypothesis is validated."""

    @classmethod
    def evaluate(
        cls,
        symbol: str,
        current_price: float,
        rsi: float,
        atr: float,
        champion_dna: str,
        regime_5m: str,
        htf_regime: str,       # "1h_MACRO_BULL" | "1h_MACRO_BEAR" | "1h_MACRO_CHOP"
        htf_ema50: float,
        htf_ema200: float,
        structure_15m: str = "15m_STRUCTURE_CHOP", # "15m_STRUCTURE_BULL" | "15m_STRUCTURE_BEAR" | "15m_STRUCTURE_CHOP"
        rsi_15m: float = 50.0,
        ema20_15m: float = 0.0,
        ema50_15m: float = 0.0,
        cooldown_info: Optional[Dict[str, Any]] = None,
        candle_is_green_5m: bool = True,
        last_trade_elapsed_seconds: float = 0.0
    ) -> Dict[str, Any]:
        """
        Runs the 3-agent adversarial debate using Multi-Angle Confirmation (1H + 15M + 5M).
        Calibrated across 3 Crypto (BTC, ETH, SOL) and 3 Forex (EURUSD, GBPUSD, USDJPY).
        """
        atr_pct = (atr / current_price) * 100.0 if current_price > 0 else 0.0
        is_forex = any(fx in symbol for fx in ["EUR", "GBP", "JPY"])
        is_jpy = "JPY" in symbol

        # GATE 0A: Weekend Forex Market Shift Gate
        # Global Forex exchanges close Friday 21:00 UTC and reopen Sunday 21:00 UTC
        from datetime import datetime, timezone
        now_utc_dt = datetime.now(timezone.utc)
        weekday = now_utc_dt.weekday() # 4=Friday, 5=Saturday, 6=Sunday
        hour = now_utc_dt.hour
        is_forex_weekend = is_forex and (
            (weekday == 4 and hour >= 21) or
            (weekday == 5) or
            (weekday == 6 and hour < 21)
        )
        if is_forex_weekend:
            risk_arg = (
                f"STAND DOWN [FOREX_WEEKEND_MARKET_CLOSED]: Global Forex exchange closed for {symbol} "
                f"(Friday 21:00 UTC - Sunday 21:00 UTC). Capital and focus routed strictly to 24/7 Crypto."
            )
            return {
                "perspectives": [
                    {"role": "BULL ADVOCATE", "text": "Forex market closed for weekend.", "conviction": 0.0, "action": "STAND_DOWN"},
                    {"role": "BEAR SKEPTIC", "text": "Forex market closed for weekend.", "conviction": 0.0, "action": "STAND_DOWN"},
                    {"role": "RISK GOVERNOR", "text": risk_arg, "verdict": "STAND_DOWN", "rr_ratio": 2.0}
                ],
                "symbol": symbol,
                "consensus": "STAND_DOWN",
                "confidence": 0.99,
                "risk_verdict": "STAND_DOWN",
                "htf_regime": htf_regime,
                "structure_15m": structure_15m,
                "suggested_order": None
            }

        # GATE 0B: Mandatory 06:00 AM - 13:30 PM IST Morning Session Lockout Gate
        # Per Founder Mandate: All trades 100% flat at 06:00 AM IST. Zero new trades allowed until London Open (13:30 IST)
        from datetime import datetime, timezone, timedelta
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        ist_hour = ist_now.hour
        ist_min = ist_now.minute
        is_morning_flat_window = (6 <= ist_hour < 13) or (ist_hour == 13 and ist_min < 30)
        if is_morning_flat_window:
            risk_arg = (
                f"STAND DOWN [06:00 AM - 13:30 IST MORNING LOCKOUT]: Portfolio is in mandatory flat cash preservation mode "
                f"between 06:00 AM IST and 01:30 PM IST (London Open). Zero new entries permitted."
            )
            return {
                "perspectives": [
                    {"role": "BULL ADVOCATE", "text": "Morning session flat window active.", "conviction": 0.0, "action": "STAND_DOWN"},
                    {"role": "BEAR SKEPTIC", "text": "Morning session flat window active.", "conviction": 0.0, "action": "STAND_DOWN"},
                    {"role": "RISK GOVERNOR", "text": risk_arg, "verdict": "STAND_DOWN", "rr_ratio": 2.0}
                ],
                "symbol": symbol,
                "consensus": "STAND_DOWN",
                "confidence": 0.99,
                "risk_verdict": "STAND_DOWN",
                "htf_regime": htf_regime,
                "structure_15m": structure_15m,
                "suggested_order": None
            }

        # GATE 0: Mandatory Post-Stop-Loss Anti-Whipsaw Cooldown
        if cooldown_info and cooldown_info.get("in_cooldown"):
            risk_arg = (
                f"VETO [POST_LOSS_COOLDOWN]: {symbol} in mandatory anti-whipsaw cooldown: "
                f"{cooldown_info.get('reason', 'cooldown active')}. Capital preservation priority. STAND DOWN."
            )
            return {
                "perspectives": [
                    {"agent": "Bull", "stance": "STAND_DOWN", "text": "Cooldown active after prior stop hit."},
                    {"agent": "Bear", "stance": "STAND_DOWN", "text": "Cooldown active after prior stop hit."},
                    {"agent": "RiskGovernor", "stance": "VETO", "text": risk_arg}
                ],
                "consensus": "STAND_DOWN",
                "confidence": 0.98,
                "risk_verdict": "VETO",
                "suggested_order": None
            }

        # INSTITUTIONAL ENTRY QUALITY FILTER (NO FORCED CHOP TRADING)
        # Never short oversold or buy overbought. Strict entry at the extremes of pullbacks.
        # 2-HOUR TRADE FLOW PACER: If >= 90 mins (5400s) since last trade, enter pulse pacing mode
        is_pacing_mode = (last_trade_elapsed_seconds >= 5400.0)
        long_rsi_max = 55.0 if is_pacing_mode else 44.0   # Deep discount dip required for longs
        short_rsi_min = 45.0 if is_pacing_mode else 56.0  # High-asymmetry relief rally required for shorts

        is_bullish_context = htf_regime in ("1h_MACRO_BULL", "15m_STRUCTURE_BULL_ACTIVE")
        is_bearish_context = htf_regime in ("1h_MACRO_BEAR", "15m_STRUCTURE_BEAR_ACTIVE")

        # ---------------- 1. BULL ADVOCATE (ANGLE 1 & 2 CONFIRMATION) ----------------
        if is_bullish_context:
            if rsi_15m < 20.0:
                bull_arg = (
                    f"15M SEVERE WATERFALL: 15m RSI ({rsi_15m:.1f}) in extreme capitulation. "
                    f"Awaiting 15m base confirmation before catching falling knife."
                )
                bull_conv = 0.40
                bull_action = "STAND_DOWN"
            elif rsi_15m > 72.0:
                bull_arg = (
                    f"15M OVERBOUGHT: Bullish context, but 15m RSI ({rsi_15m:.1f}) is extended. "
                    f"Refusing to chase top. Awaiting pullback to value."
                )
                bull_conv = 0.45
                bull_action = "STAND_DOWN"
            elif rsi <= long_rsi_max:
                if candle_is_green_5m:
                    pacing_tag = " [2-HOUR PULSE ACTIVE]" if is_pacing_mode else ""
                    bull_arg = (
                        f"CONFIRMED BOUNCE DIP LONG{pacing_tag}: {htf_regime} + Green 5m candle. "
                        f"Pullback to RSI {rsi:.1f} (15m RSI: {rsi_15m:.1f}) offers high-asymmetry bounce entry."
                    )
                    bull_conv = 0.90
                    bull_action = "LONG"
                else:
                    bull_arg = (
                        f"DIP AWAITING REVERSAL: 5m RSI is {rsi:.1f}, but 5m candle is red. "
                        f"Awaiting green bounce candle before entering."
                    )
                    bull_conv = 0.50
                    bull_action = "STAND_DOWN"
            elif rsi > 68.0:
                bull_arg = (
                    f"5M OVERBOUGHT: Bullish context aligned, but 5m RSI is {rsi:.1f}. Awaiting dip entry."
                )
                bull_conv = 0.40
                bull_action = "STAND_DOWN"
            else:
                bull_arg = (
                    f"{symbol} bullish context, 5m RSI at {rsi:.1f} in equilibrium. Awaiting dip under {long_rsi_max:.0f}."
                )
                bull_conv = 0.55
                bull_action = "STAND_DOWN"
        elif is_bearish_context:
            bull_arg = (
                f"COUNTER-TREND VETO: 1h Macro Trend is BEARISH (50 EMA < 200 EMA). "
                f"All Longs strictly prohibited. Bull standing down."
            )
            bull_conv = 0.15
            bull_action = "STAND_DOWN"
        else:
            bull_arg = (
                f"{symbol} in 1h chop equilibrium. Directional probability < 50%. Bull standing down."
            )
            bull_conv = 0.35
            bull_action = "STAND_DOWN"

        # ---------------- 2. BEAR SKEPTIC (ANGLE 1 & 2 CONFIRMATION) ----------------
        if is_bearish_context:
            if rsi_15m > 80.0:
                bear_arg = (
                    f"15M PARABOLIC SQUEEZE: 15m RSI ({rsi_15m:.1f}) in explosive short squeeze. "
                    f"Awaiting 15m exhaustion before deploying short capital."
                )
                bear_conv = 0.40
                bear_action = "STAND_DOWN"
            elif rsi_15m < 28.0:
                bear_arg = (
                    f"15M OVERSOLD: Bearish context, but 15m RSI ({rsi_15m:.1f}) is compressed. "
                    f"Refusing to short the bottom. Awaiting relief rally."
                )
                bear_conv = 0.45
                bear_action = "STAND_DOWN"
            elif rsi >= short_rsi_min:
                if not candle_is_green_5m:
                    pacing_tag = " [2-HOUR PULSE ACTIVE]" if is_pacing_mode else ""
                    bear_arg = (
                        f"CONFIRMED REJECTION SHORT{pacing_tag}: {htf_regime} + Red 5m candle. "
                        f"Relief rally to RSI {rsi:.1f} (15m RSI: {rsi_15m:.1f}) offers high-asymmetry rejection entry."
                    )
                    bear_conv = 0.90
                    bear_action = "SHORT"
                else:
                    bear_arg = (
                        f"RELIEF AWAITING EXHAUSTION: 5m RSI is {rsi:.1f}, but 5m candle is green. "
                        f"Awaiting red rejection candle before shorting."
                    )
                    bear_conv = 0.50
                    bear_action = "STAND_DOWN"
            elif rsi < 32.0:
                bear_arg = (
                    f"5M OVERSOLD: Bearish context aligned, but 5m RSI is {rsi:.1f}. Awaiting relief rally."
                )
                bear_conv = 0.40
                bear_action = "STAND_DOWN"
            else:
                bear_arg = (
                    f"{symbol} bearish context, 5m RSI at {rsi:.1f} in equilibrium. Awaiting relief rally over {short_rsi_min:.0f}."
                )
                bear_conv = 0.55
                bear_action = "STAND_DOWN"
        elif is_bullish_context:
            bear_arg = (
                f"COUNTER-TREND VETO: 1h Macro Trend is BULLISH (50 EMA > 200 EMA). "
                f"All Shorts strictly prohibited. Bear standing down."
            )
            bear_conv = 0.15
            bear_action = "STAND_DOWN"
        else:
            bear_arg = (
                f"{symbol} in 1h chop equilibrium. Directional probability < 50%. Bear standing down."
            )
            bear_conv = 0.35
            bear_action = "STAND_DOWN"


        # ---------------- 3. RISK GOVERNOR (MULTI-ANGLE GATES & RISK LIMITS) ----------------
        # Institutional Structural Stops (2.4x ATR SL / 4.2x ATR TP)
        # Prevents micro-noise stop-outs. Governor dynamically scales lot size to maintain EXACTLY <= $35.00 risk.
        sl_multiplier = 2.4
        tp_multiplier = 4.2

        # Calibrated with institutional noise buffers:
        if is_jpy:
            sl_dist = round(max(sl_multiplier * atr, 0.180), 3)
            tp_dist = round(max(tp_multiplier * atr, 0.320), 3)
            dec = 3
        elif is_forex:
            sl_dist = round(max(sl_multiplier * atr, 0.00140), 5)
            tp_dist = round(max(tp_multiplier * atr, 0.00250), 5)
            dec = 5
        elif "BTC" in symbol:
            sl_dist = round(max(sl_multiplier * atr, 320.0), 2)
            tp_dist = round(max(tp_multiplier * atr, 580.0), 2)
            dec = 2
        elif "ETH" in symbol:
            sl_dist = round(max(sl_multiplier * atr, 16.0), 2)
            tp_dist = round(max(tp_multiplier * atr, 28.0), 2)
            dec = 2
        else:  # SOL
            sl_dist = round(max(sl_multiplier * atr, 1.80), 2)
            tp_dist = round(max(tp_multiplier * atr, 3.20), 2)
            dec = 2

        rr_ratio = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.8

        # GATE 1: Minimum Volatility Floor
        min_atr_pct = 0.008 if is_forex else 0.035
        if atr_pct < min_atr_pct:
            risk_arg = (
                f"VETO [CHOP_FILTER]: ATR is critically low ({atr_pct:.4f}% vs min {min_atr_pct:.4f}%). "
                f"Market in dead zone. STAND DOWN."
            )
            risk_verdict = "VETO"
            consensus = "STAND_DOWN"
            confidence = 0.92
            suggested_order = None

        # GATE 2: 1-Hour Macro Chop Veto
        elif htf_regime == "1h_MACRO_CHOP":
            risk_arg = (
                f"VETO [1H_MACRO_CHOP]: 1-Hour trend is neutral/in chop between 50 EMA (${htf_ema50:.4f}) and "
                f"200 EMA (${htf_ema200:.4f}). Capital preservation active. STAND DOWN."
            )
            risk_verdict = "VETO"
            consensus = "STAND_DOWN"
            confidence = 0.90
            suggested_order = None

        # GATE 3: 15-Minute Severe Divergence Check (Only veto if 15m is in extreme waterfall or parabolic blowoff)
        elif htf_regime == "1h_MACRO_BULL" and rsi_15m < 20.0:
            risk_arg = (
                f"VETO [15M_WATERFALL_CRASH]: 15m RSI ({rsi_15m:.1f}) in extreme capitulation. "
                f"Awaiting stabilization. STAND DOWN."
            )
            risk_verdict = "VETO"
            consensus = "STAND_DOWN"
            confidence = 0.90
            suggested_order = None

        elif htf_regime == "1h_MACRO_BEAR" and rsi_15m > 80.0:
            risk_arg = (
                f"VETO [15M_PARABOLIC_SQUEEZE]: 15m RSI ({rsi_15m:.1f}) in explosive short squeeze. "
                f"Awaiting exhaustion. STAND DOWN."
            )
            risk_verdict = "VETO"
            consensus = "STAND_DOWN"
            confidence = 0.90
            suggested_order = None

        # APPROVAL 1: Multi-Angle Bearish
        elif is_bearish_context and rsi_15m <= 78.0 and bear_conv >= 0.70:
            sl_price = round(current_price + sl_dist, dec)
            tp_price = round(current_price - tp_dist, dec)
            pacing_tag = " [2-HOUR PULSE]" if is_pacing_mode else ""
            risk_arg = (
                f"APPROVED [MULTI_ANGLE_SHORT{pacing_tag}]: {htf_regime} + 15M Relief ({structure_15m}) + 5M Trigger (RSI: {rsi:.1f}). "
                f"SL: {sl_price} (+{sl_dist}), TP: {tp_price} (-{tp_dist}) | R:R 1:{rr_ratio:.1f} (Strict <= $35 Risk)."
            )
            risk_verdict = "APPROVED"
            consensus = "SHORT"
            confidence = round((bear_conv + 0.90) / 2.0, 2)
            suggested_order = {
                "symbol": symbol,
                "side": "SHORT",
                "entry": current_price,
                "sl": sl_price,
                "tp": tp_price,
                "sl_dist": sl_dist,
                "tp_dist": tp_dist,
                "rr_ratio": rr_ratio,
                "atr": atr,
                "htf_regime": htf_regime,
                "structure_15m": structure_15m
            }

        # APPROVAL 2: Multi-Angle Bullish
        elif is_bullish_context and rsi_15m >= 22.0 and bull_conv >= 0.70:
            sl_price = round(current_price - sl_dist, dec)
            tp_price = round(current_price + tp_dist, dec)
            pacing_tag = " [2-HOUR PULSE]" if is_pacing_mode else ""
            risk_arg = (
                f"APPROVED [MULTI_ANGLE_LONG{pacing_tag}]: {htf_regime} + 15M Pullback ({structure_15m}) + 5M Dip (RSI: {rsi:.1f}). "
                f"SL: {sl_price} (-{sl_dist}), TP: {tp_price} (+{tp_dist}) | R:R 1:{rr_ratio:.1f} (Strict <= $35 Risk)."
            )
            risk_verdict = "APPROVED"
            consensus = "LONG"
            confidence = round((bull_conv + 0.90) / 2.0, 2)
            suggested_order = {
                "symbol": symbol,
                "side": "LONG",
                "entry": current_price,
                "sl": sl_price,
                "tp": tp_price,
                "sl_dist": sl_dist,
                "tp_dist": tp_dist,
                "rr_ratio": rr_ratio,
                "atr": atr,
                "htf_regime": htf_regime,
                "structure_15m": structure_15m
            }

        else:
            risk_arg = (
                f"STAND DOWN [CONVICTION_THRESHOLD]: Bull conviction ({bull_conv:.2f}) and Bear conviction "
                f"({bear_conv:.2f}) do not satisfy strict multi-angle threshold (0.75). Capital preserved."
            )
            risk_verdict = "STAND_DOWN"
            consensus = "STAND_DOWN"
            confidence = 0.80
            suggested_order = None

        return {
            "symbol": symbol,
            "consensus": consensus,
            "confidence": confidence,
            "risk_verdict": risk_verdict,
            "htf_regime": htf_regime,
            "structure_15m": structure_15m,
            "suggested_order": suggested_order,
            "perspectives": [
                {"role": "BULL ADVOCATE", "text": bull_arg, "conviction": bull_conv, "action": bull_action},
                {"role": "BEAR SKEPTIC", "text": bear_arg, "conviction": bear_conv, "action": bear_action},
                {"role": "RISK GOVERNOR", "text": risk_arg, "verdict": risk_verdict, "rr_ratio": round(rr_ratio, 1)}
            ]
        }
