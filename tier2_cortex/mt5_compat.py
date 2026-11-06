"""
PROJECT AVI // CROSS-PLATFORM METATRADER 5 COMPATIBILITY LAYER
Transparent drop-in bridge supporting:
1. Native Windows MetaTrader5 C-extension (local execution).
2. Linux / Docker mt5linux RPyC client (connects to Wine MT5 container).
"""

from __future__ import annotations

import os
import sys
import logging

logger = logging.getLogger("avi.mt5_compat")

bridge_host = os.getenv("MT5_BRIDGE_HOST")
bridge_port = int(os.getenv("MT5_BRIDGE_PORT", "8001"))

mt5 = None

# If MT5_BRIDGE_HOST is provided or running on non-Windows Linux/macOS
if bridge_host or sys.platform != "win32":
    target_host = bridge_host or "mt5-wine"
    try:
        from mt5linux import MetaTrader5  # type: ignore
        mt5 = MetaTrader5(host=target_host, port=bridge_port)
        logger.info(f"[MT5_COMPAT] Initialized mt5linux RPyC bridge to {target_host}:{bridge_port}")
    except ImportError:
        logger.warning("[MT5_COMPAT] 'mt5linux' not installed. Attempting standard MetaTrader5 import...")
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError:
            logger.error("[MT5_COMPAT] Neither 'mt5linux' nor 'MetaTrader5' is available.")
            mt5 = None
    except Exception as e:
        logger.error(f"[MT5_COMPAT] Failed to initialize mt5linux bridge: {e}")
        try:
            import MetaTrader5 as mt5  # type: ignore
        except ImportError:
            mt5 = None
else:
    # Standard native Windows local execution
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError:
        try:
            from mt5linux import MetaTrader5  # type: ignore
            mt5 = MetaTrader5(host="localhost", port=bridge_port)
        except ImportError:
            logger.warning("[MT5_COMPAT] MetaTrader5 not installed on Windows system.")
            mt5 = None

__all__ = ["mt5"]

