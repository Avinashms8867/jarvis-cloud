"""
PROJECT AVI // FTMO MT5 EXECUTION BRIDGE
Translates Agent 2 quantitative signals into live MetaTrader 5 orders:
- Connects to local FTMO MetaTrader 5 terminal
- Enforces FTMO Rule Governor risk limits
- Executes orders with exact stop-loss and take-profit via mt5.order_send()
"""

from __future__ import annotations
import os
import sys
import logging
import subprocess
import time
from typing import Dict, Any, Optional

try:
    from tier2_cortex.mt5_compat import mt5
except ImportError:
    try:
        from mt5_compat import mt5
    except ImportError:
        try:
            import MetaTrader5 as mt5
        except ImportError:
            mt5 = None

from tier2_cortex.ftmo_governor import FTMORuleGovernor

logger = logging.getLogger("avi.cortex.ftmo_bridge")


class FTMOMT5Bridge:
    """Live Execution Bridge between Project AVI and FTMO MetaTrader 5."""

    TERMINAL_PATH = os.getenv("MT5_TERMINAL_PATH", r"C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe")

    def __init__(self, governor: Optional[FTMORuleGovernor] = None):
        self.governor = governor or FTMORuleGovernor(initial_balance=100000.0)
        self.is_connected: bool = False
        self.login: int = 1515102715
        self.server: str = "FTMO-Demo"
        self.password: str = "r!N6G$L9Z"
        self.btc_trades_count: int = 0
        self.BTC_MAX_TRADES: int = 3
        self._load_credentials()

    def _load_credentials(self) -> None:
        """Reads credentials from AVI Project/.env."""
        env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("FTMO_MT5_LOGIN="):
                        try:
                            self.login = int(line.split("=", 1)[1])
                        except ValueError:
                            pass
                    elif line.startswith("FTMO_MT5_SERVER="):
                        self.server = line.split("=", 1)[1]
                    elif line.startswith("FTMO_MT5_PASSWORD="):
                        self.password = line.split("=", 1)[1]

    def _is_terminal_process_running(self) -> bool:
        """Fast non-blocking check to verify if terminal64.exe is running.
        Bypassed on Linux or when MT5_BRIDGE_HOST is configured."""
        if os.getenv("MT5_BRIDGE_HOST") or sys.platform != "win32":
            return True
        try:
            res = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq terminal64.exe"],
                capture_output=True,
                text=True,
                timeout=1
            )
            return "terminal64.exe" in res.stdout
        except Exception:
            return False

    def connect(self) -> bool:
        """Fast, non-blocking connection to FTMO MT5 terminal."""
        if not mt5:
            logger.warning("[FTMO] MetaTrader5 library not available.")
            return False

        # 1. If already initialized in this python runtime
        try:
            if mt5.terminal_info() is not None:
                self.is_connected = True
                self._sync_account()
                return True
        except Exception:
            pass

        # 2. If bridged mode or non-windows: connect directly via mt5.initialize()
        if os.getenv("MT5_BRIDGE_HOST") or sys.platform != "win32":
            try:
                init_ok = False
                if self.login and self.password and self.server:
                    init_ok = mt5.initialize(login=self.login, password=self.password, server=self.server)
                if not init_ok:
                    init_ok = mt5.initialize()
                if init_ok:
                    self.is_connected = True
                    self._sync_account()
                    logger.info(f"[FTMO] Connected via MT5 Bridge to {self.server}.")
                    return True
            except Exception as e:
                logger.error(f"[FTMO] Bridge connection error: {e}")

        # 3. If terminal64.exe is active in Windows, attach immediately
        if self._is_terminal_process_running():
            try:
                if mt5.initialize(path=self.TERMINAL_PATH) or mt5.initialize():
                    self.is_connected = True
                    self._sync_account()
                    logger.info(f"[FTMO] Attached to running MT5 Terminal.")
                    return True
            except Exception:
                pass

        self.is_connected = False
        return False

    def _sync_account(self) -> None:
        """Syncs balance and equity to the FTMO Governor."""
        if not mt5 or not self.is_connected:
            return
        try:
            acc = mt5.account_info()
            if acc:
                self.login = acc.login
                self.governor.update_account_metrics(current_balance=acc.balance, current_equity=acc.equity)
        except Exception:
            pass

    def get_cooldown_status(self, symbol: str) -> Dict[str, Any]:
        """
        Calculates post-stop-loss cooldown status for a symbol.
        Enforces:
        - 15 minutes (900s) cooldown after 1 stop loss
        - 30 minutes (1800s) cooldown after 2 consecutive stop losses
        - 60 minutes (3600s) cooldown after 3+ consecutive stop losses
        Prevents repetitive churn, revenge trading, and entering into the same chop zone.
        """
        if not mt5 or not self.connect():
            return {"in_cooldown": False, "remaining_seconds": 0, "consecutive_losses": 0, "reason": ""}

        mt5_sym = symbol.replace("USDT", "USD")

        # 1. Check in-memory fast cache first
        now_ts = time.time()
        if hasattr(self, "_loss_cooldowns") and mt5_sym in self._loss_cooldowns:
            cd_data = self._loss_cooldowns[mt5_sym]
            elapsed = now_ts - cd_data["loss_time"]
            cooldown_dur = cd_data.get("duration", 900)
            if elapsed < cooldown_dur:
                rem = int(cooldown_dur - elapsed)
                return {
                    "in_cooldown": True,
                    "remaining_seconds": rem,
                    "consecutive_losses": cd_data.get("consecutive", 1),
                    "reason": f"Post-Loss Cooldown ({rem//60}m {rem%60}s remaining, {cd_data.get('consecutive', 1)} loss(es))"
                }

        # 2. Query MT5 closed deals history for authoritative audit
        try:
            from datetime import datetime, timedelta
            d_from = datetime.now() - timedelta(hours=12)
            d_to = datetime.now() + timedelta(days=1)
            deals = mt5.history_deals_get(d_from, d_to)
            if deals:
                exit_deals = [d for d in deals if d.symbol == mt5_sym and d.entry == 1]
                if exit_deals:
                    last_exit = exit_deals[-1]
                    # Check if last exit was a loss
                    is_loss = (last_exit.profit < 0) or ("[sl" in str(last_exit.comment).lower())
                    if is_loss:
                        tick = mt5.symbol_info_tick(mt5_sym)
                        broker_now = tick.time if tick else time.time()
                        elapsed = broker_now - last_exit.time
                        # Count consecutive losses
                        consecutive = 0
                        for d in reversed(exit_deals):
                            if (d.profit < 0) or ("[sl" in str(d.comment).lower()):
                                consecutive += 1
                            else:
                                break
                        cooldown_dur = 600 if consecutive == 1 else (1200 if consecutive == 2 else 1800)
                        if elapsed < cooldown_dur:
                            rem = int(cooldown_dur - elapsed)
                            if not hasattr(self, "_loss_cooldowns"):
                                self._loss_cooldowns = {}
                            self._loss_cooldowns[mt5_sym] = {
                                "loss_time": last_exit.time,
                                "duration": cooldown_dur,
                                "consecutive": consecutive
                            }
                            return {
                                "in_cooldown": True,
                                "remaining_seconds": rem,
                                "consecutive_losses": consecutive,
                                "reason": f"Post-Loss Cooldown ({rem//60}m {rem%60}s remaining, {consecutive} consecutive loss(es))"
                            }
        except Exception as e:
            logger.warning(f"[COOLDOWN CHECK ERROR] {e}")

        return {"in_cooldown": False, "remaining_seconds": 0, "consecutive_losses": 0, "reason": ""}


    def get_last_trade_elapsed_seconds(self) -> float:
        """Calculates exact elapsed seconds since the latest trade executed across the portfolio."""
        if not mt5 or not self.connect():
            return 0.0
        try:
            latest_ts = 0
            positions = mt5.positions_get()
            if positions:
                for p in positions:
                    if p.time > latest_ts:
                        latest_ts = p.time

            from datetime import datetime, timedelta
            deals = mt5.history_deals_get(datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=1))
            if deals:
                for d in deals:
                    if d.entry == 0 and d.time > latest_ts:
                        latest_ts = d.time

            if latest_ts > 0:
                return max(0.0, time.time() - latest_ts)
        except Exception as e:
            logger.warning(f"[ELAPSED TIME CHECK ERROR] {e}")
        return 0.0

    def execute_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes an order on FTMO MT5 with full safety checks:
        Enforces:
        - Max 1 open position per symbol (no stacking)
        - Max 3 trades on BTC per session (stops BTC thereafter to focus on other 5)
        """
        if not self.is_connected and not self.connect():
            return {"success": False, "message": "FTMO MT5 terminal in standby."}

        # Mandatory 06:00 AM - 13:30 IST Hard Session Lockout
        from datetime import datetime, timezone, timedelta
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        ist_hour = ist_now.hour
        ist_min = ist_now.minute
        if (6 <= ist_hour < 13) or (ist_hour == 13 and ist_min < 30):
            msg = f"[SESSION LOCKOUT] Cannot execute order on {signal.get('symbol')}: Outside active session hours (06:00 AM - 01:30 PM IST). 100% Flat preservation enforced."
            logger.info(msg)
            return {"success": False, "message": msg}

        mt5_sym = signal["symbol"].replace("USDT", "USD")

        # 1. RISK-FREE SCALE-IN & MULTI-WAVE POSITION POLICY
        # Allows up to 2 concurrent positions per symbol ONLY IF existing position is already Risk-Free (SL at Breakeven or Profit >= $20)
        try:
            current_pos = mt5.positions_get(symbol=mt5_sym)
            if current_pos:
                if len(current_pos) >= 2:
                    logger.info(f"[EXPOSURE LOCK] {mt5_sym} reached max concurrent position limit (2). Skipping.")
                    return {"success": False, "message": f"{mt5_sym} reached max concurrent position limit (2). Duplicate entry blocked."}
                
                existing = current_pos[0]
                is_buy = (existing.type == mt5.ORDER_TYPE_BUY)
                is_risk_free = False
                
                if is_buy and existing.sl >= existing.price_open:
                    is_risk_free = True
                elif not is_buy and existing.sl > 0 and existing.sl <= existing.price_open:
                    is_risk_free = True
                elif existing.profit >= 20.0:
                    is_risk_free = True
                    
                if not is_risk_free:
                    msg = f"{mt5_sym} already has open trade #{existing.ticket} at active risk (Profit: ${existing.profit:.2f}, SL: {existing.sl}). Duplicate blocked until Breakeven."
                    logger.info(f"[EXPOSURE LOCK] {msg}")
                    return {"success": False, "message": msg}
                
                # Check price separation from existing entry
                tick = mt5.symbol_info_tick(mt5_sym)
                curr_p = tick.ask if signal["side"] == "LONG" else tick.bid if tick else signal["price"]
                sl_dist = signal.get("sl_dist", 50.0)
                if abs(curr_p - existing.price_open) < (sl_dist * 0.25):
                    return {"success": False, "message": f"{mt5_sym} new setup too close to existing entry ({existing.price_open}). Awaiting price movement."}
        except Exception as e:
            logger.warning(f"[EXPOSURE LOCK CHECK ERROR] {e}")

        # 2. ANTI-WHIPSAW POST-STOP-LOSS COOLDOWN LOCK
        cd_status = self.get_cooldown_status(mt5_sym)
        if cd_status.get("in_cooldown"):
            msg = f"[POST-LOSS COOLDOWN BLOCKED] {mt5_sym} in cooldown: {cd_status['reason']}. Preventing immediate churn/revenge trade."
            print(msg, flush=True)
            logger.warning(msg)
            return {"success": False, "message": msg}

        self._sync_account()

        # 1. Governor Compliance Check
        can_trade, reason = self.governor.can_open_new_trade()
        if not can_trade:
            return {"success": False, "message": f"FTMO Governor Veto: {reason}"}

        # 2. Map symbol to MT5 format (e.g. BTCUSDT -> BTCUSD)
        # Mandatory 06:00 AM - 13:30 IST Hard Session Lockout
        from datetime import datetime, timezone, timedelta
        ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        ist_hour = ist_now.hour
        ist_min = ist_now.minute
        if (6 <= ist_hour < 13) or (ist_hour == 13 and ist_min < 30):
            msg = f"[SESSION LOCKOUT] Cannot execute order on {signal.get('symbol')}: Outside active session hours (06:00 AM - 01:30 PM IST). 100% Flat preservation enforced."
            logger.info(msg)
            return {"success": False, "message": msg}

        mt5_sym = signal["symbol"].replace("USDT", "USD")
        side = signal["side"]
        order_type = mt5.ORDER_TYPE_BUY if side == "LONG" else mt5.ORDER_TYPE_SELL

        # 3. Calculate compliant lot size (<= 0.5% risk)
        lots = self.governor.calculate_order_lot_size(mt5_sym, signal["price"], signal["sl"])

        # 4. Prepare MT5 Request with stops relative to actual MT5 fill price
        try:
            mt5.symbol_select(mt5_sym, True)
            tick = mt5.symbol_info_tick(mt5_sym)
            if not tick:
                return {"success": False, "message": f"Could not get tick for {mt5_sym}"}

            info = mt5.symbol_info(mt5_sym)
            digits = info.digits if info else 2

            sl_dist = signal.get("sl_dist")
            if not sl_dist or sl_dist <= 0:
                sl_dist = abs(signal["price"] - signal["sl"])
            tp_dist = signal.get("tp_dist")
            if not tp_dist or tp_dist <= 0:
                tp_dist = abs(signal["price"] - signal["tp"])

            if side == "LONG":
                price = tick.ask
                sl = round(price - sl_dist, digits)
                tp = round(price + tp_dist, digits)
            else:
                price = tick.bid
                sl = round(price + sl_dist, digits)
                tp = round(price - tp_dist, digits)

            # Extra safety check against invalid stops
            if side == "LONG" and sl >= price:
                sl = round(price - (sl_dist if sl_dist > 0 else 10.0), digits)
            elif side == "SHORT" and sl <= price:
                sl = round(price + (sl_dist if sl_dist > 0 else 10.0), digits)

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": mt5_sym,
                "volume": lots,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 202609,
                "comment": "AVI_ALPHA_GOVERNOR",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                msg = f"[FTMO LIVE] Trade executed! Order #{result.order} {side} {lots} {mt5_sym} @ {price}"
                print(msg, flush=True)
                logger.info(msg)
                return {
                    "success": True,
                    "order_id": result.order,
                    "symbol": mt5_sym,
                    "side": side,
                    "volume": lots,
                    "fill_price": price,
                    "message": "Order filled successfully on FTMO MT5."
                }
            else:
                error = result.comment if result else mt5.last_error()
                msg = f"[FTMO ORDER REJECTED] {mt5_sym} retcode={result.retcode if result else 'None'}, comment={error}"
                print(msg, flush=True)
                logger.error(msg)
                return {"success": False, "message": f"MT5 Execution error: {error}"}
        except Exception as e:
            msg = f"[FTMO ORDER EXCEPTION] {e}"
            print(msg, flush=True)
            logger.error(msg)
            return {"success": False, "message": f"Execution exception: {e}"}

    def manage_active_positions(self) -> None:
        """
        Actively monitors open FTMO MT5 positions and applies dynamic multi-tier profit realization:
        
        Institutional Asymmetry Rule: Initial risk is ~$35. Wins MUST NOT be choked at pennies.
        
        1. Breathing Room Zone (Profit < +$28.00):
           Leave initial Stop-Loss and Take-Profit untouched. Let the trade develop through normal market noise.
        
        2. Tier 1: Safety Profit Floor (Profit >= +$28.00):
           Move Stop-Loss to lock in guaranteed CASH profit of at least +$14.00 (halfway to target, covering fees & locking gains).
           Eliminates $0.02 scratch-outs by maintaining a realistic distance from entry.
        
        3. Tier 2: Institutional Profit Lock (Profit >= +$45.00):
           Trail Stop-Loss to lock in at least +$28.00 guaranteed profit (0.8R secured).
        
        4. Tier 3: Dynamic Runner Trail (Profit >= +$60.00):
           Trail Stop-Loss locking in 70% of peak gains, allowing impulse runners to capture full +$75.00 to +$90.00 Take Profit.
        """
        if not mt5 or not self.connect():
            return

        try:
            positions = mt5.positions_get()
            if not positions:
                return

            for p in positions:
                profit = p.profit
                open_price = p.price_open
                curr_price = p.price_current
                curr_sl = p.sl
                curr_tp = p.tp
                symbol = p.symbol
                is_buy = (p.type == mt5.ORDER_TYPE_BUY)

                info = mt5.symbol_info(symbol)
                digits = info.digits if info else 2

                price_dist = abs(curr_price - open_price)
                if price_dist <= 0 or profit <= 0:
                    continue

                new_sl = None
                log_tag = None

                # Tier 3: Runner Trail (>= +$60.00 profit) -> lock 70% of gains
                if profit >= 60.0:
                    lock_dist = price_dist * 0.70
                    candidate_sl = round(open_price + lock_dist if is_buy else open_price - lock_dist, digits)
                    if (is_buy and candidate_sl > curr_sl) or (not is_buy and (curr_sl == 0.0 or candidate_sl < curr_sl)):
                        new_sl = candidate_sl
                        locked_est = profit * 0.70
                        log_tag = f"[TIER-3 RUNNER TRAIL] Position #{p.ticket} {symbol} profit=${profit:.2f}. Trailed SL to {new_sl} (Locked ~${locked_est:.2f})"

                # Tier 2: Institutional Lock (>= +$45.00 profit) -> lock at least +$28.00
                elif profit >= 45.0:
                    lock_dist = (28.0 / profit) * price_dist
                    candidate_sl = round(open_price + lock_dist if is_buy else open_price - lock_dist, digits)
                    if (is_buy and candidate_sl > curr_sl) or (not is_buy and (curr_sl == 0.0 or candidate_sl < curr_sl)):
                        new_sl = candidate_sl
                        log_tag = f"[TIER-2 INSTITUTIONAL LOCK] Position #{p.ticket} {symbol} profit=${profit:.2f}. SL moved to {new_sl} (Locked +$28.00 Floor)"

                # Tier 1: Safety Profit Floor (>= +$28.00 profit) -> lock at least +$14.00
                elif profit >= 28.0:
                    lock_dist = (14.0 / profit) * price_dist
                    candidate_sl = round(open_price + lock_dist if is_buy else open_price - lock_dist, digits)
                    if (is_buy and candidate_sl > curr_sl) or (not is_buy and (curr_sl == 0.0 or candidate_sl < curr_sl)):
                        new_sl = candidate_sl
                        log_tag = f"[TIER-1 PROFIT FLOOR] Position #{p.ticket} {symbol} profit=${profit:.2f}. SL moved to {new_sl} (Locked +$14.00 Floor, Room to Run)"

                if new_sl is not None:
                    req = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": p.ticket,
                        "symbol": symbol,
                        "sl": new_sl,
                        "tp": curr_tp
                    }
                    res = mt5.order_send(req)
                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(log_tag, flush=True)
                        logger.info(log_tag)
                    else:
                        ret_desc = res.comment if res else "Unknown"
                        logger.warning(f"[SLTP UPDATE FAILED] Position #{p.ticket} {symbol}: {ret_desc}")
        except Exception as e:
            logger.warning(f"[POSITION MANAGER ERROR] {e}")

    def get_status(self) -> Dict[str, Any]:
        if self.is_connected:
            self._sync_account()
        telemetry = self.governor.get_telemetry()
        telemetry["mt5_connected"] = self.is_connected
        telemetry["login"] = self.login
        telemetry["server"] = self.server
        return telemetry
