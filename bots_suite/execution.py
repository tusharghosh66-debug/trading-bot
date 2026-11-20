"""
Execution & Portfolio Management Engine for 3 Master Bots Suite
Handles automated paper order placement, live P&L tracking, Stop Loss/Take Profit auto-exits,
and persistent ledger for each Master Bot.
"""

import os
import json
from datetime import datetime
import pandas as pd
import yfinance as yf
from strategies.common import clean_ohlcv, to_float


class MasterBotPortfolio:
    def __init__(self, bot_id, initial_capital=30000.0, state_file=None):
        self.bot_id = bot_id
        self.state_file = state_file or os.path.join(os.path.dirname(__file__), f"state_tier{bot_id}.json")
        self.initial_capital = initial_capital
        self.data = self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if "portfolio" in d:
                        return d
            except Exception:
                pass

        # Default portfolio state
        return {
            "bot_id": self.bot_id,
            "created_at": datetime.now().isoformat(),
            "initial_capital": self.initial_capital,
            "portfolio": {
                "equity": self.initial_capital,
                "cash": self.initial_capital,
                "realized_pnl": 0.0,
                "unrealized_pnl": 0.0,
                "open_positions": {},
                "closed_trades": []
            },
            "signals": []
        }

    def save(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving state for Bot {self.bot_id}: {e}")

    def process_signals(self, signals, min_confidence=65.0):
        """
        Evaluates signals, executes new trades if qualified,
        and updates open positions against current market prices.
        """
        p = self.data["portfolio"]
        self.data["signals"] = signals

        # 1. Update existing open positions first
        for sym, pos in list(p["open_positions"].items()):
            try:
                # Find current price from new signals if available
                matched_sig = next((s for s in signals if s.get("symbol") == sym), None)
                if matched_sig and matched_sig.get("current_price"):
                    curr_price = float(matched_sig["current_price"])
                else:
                    df = clean_ohlcv(yf.download(sym, period="1d", interval="5m", progress=False))
                    curr_price = to_float(df['close'].iloc[-1]) if not df.empty else pos["entry_price"]

                pos["current_price"] = curr_price
                side = pos["side"]
                entry = pos["entry_price"]
                qty = pos["quantity"]
                sl = pos["stop_loss"]
                tp = pos["take_profit"]

                # Calculate unrealized P&L
                if side == "BUY":
                    unrealized = (curr_price - entry) * qty
                else:
                    unrealized = (entry - curr_price) * qty
                pos["unrealized_pnl"] = round(unrealized, 2)
                pos["pnl_pct"] = round((unrealized / pos["capital_allocated"]) * 100, 2)

                # Check SL / TP
                closed = False
                exit_reason = ""
                if side == "BUY":
                    if sl > 0 and curr_price <= sl:
                        closed = True
                        exit_reason = f"STOP LOSS HIT ({curr_price} <= {sl})"
                    elif tp > 0 and curr_price >= tp:
                        closed = True
                        exit_reason = f"TAKE PROFIT HIT ({curr_price} >= {tp})"
                elif side == "SELL":
                    if sl > 0 and curr_price >= sl:
                        closed = True
                        exit_reason = f"STOP LOSS HIT ({curr_price} >= {sl})"
                    elif tp > 0 and curr_price <= tp:
                        closed = True
                        exit_reason = f"TAKE PROFIT HIT ({curr_price} <= {tp})"

                if closed:
                    # Close position
                    p["open_positions"].pop(sym)
                    p["cash"] += pos["capital_allocated"] + unrealized
                    p["realized_pnl"] += unrealized
                    p["closed_trades"].append({
                        "symbol": sym,
                        "market": pos["market"],
                        "strategy": pos["strategy"],
                        "side": side,
                        "quantity": qty,
                        "entry_price": entry,
                        "exit_price": curr_price,
                        "pnl": round(unrealized, 2),
                        "pnl_pct": pos["pnl_pct"],
                        "exit_reason": exit_reason,
                        "entry_time": pos["entry_time"],
                        "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    print(f"[{sym}] CLOSED trade: {exit_reason} | PnL: ₹{unrealized:,.2f}")
            except Exception as e:
                print(f"Error updating position {sym}: {e}")

        # 2. Open new trades for qualified signals
        for sig in signals:
            action = sig.get("action", "")
            conf = sig.get("confidence", 0)
            sym = sig.get("symbol")
            price = sig.get("current_price", 0)
            alloc = sig.get("allocated_capital", 10000.0)

            # Check if actionable BUY or SELL
            if ("BUY" in action or "SELL" in action) and conf >= min_confidence and price > 0:
                side = "BUY" if "BUY" in action else "SELL"
                # Check if position already open
                if sym not in p["open_positions"]:
                    invest_cap = min(alloc, p["cash"])
                    if invest_cap >= 1000.0:  # Minimum allocation
                        qty = invest_cap / price
                        p["cash"] -= invest_cap
                        p["open_positions"][sym] = {
                            "symbol": sym,
                            "market": sig.get("market"),
                            "strategy": sig.get("strategy"),
                            "side": side,
                            "quantity": round(qty, 4),
                            "entry_price": price,
                            "current_price": price,
                            "stop_loss": sig.get("suggested_sl", 0),
                            "take_profit": sig.get("suggested_tp", 0),
                            "capital_allocated": round(invest_cap, 2),
                            "unrealized_pnl": 0.0,
                            "pnl_pct": 0.0,
                            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        print(f"✅ EXECUTED {side} {sym} @ {price} | Capital: ₹{invest_cap:,.2f} (Conf: {conf}%)")

        # 3. Recompute Total Equity
        tot_unrealized = sum(pos["unrealized_pnl"] for pos in p["open_positions"].values())
        tot_invested = sum(pos["capital_allocated"] for pos in p["open_positions"].values())
        p["unrealized_pnl"] = round(tot_unrealized, 2)
        p["equity"] = round(p["cash"] + tot_invested + tot_unrealized, 2)

        self.save()
        return self.data
