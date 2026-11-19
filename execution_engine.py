"""
Antigravity Alpha Trader - Execution Engine & Portfolio Manager
Handles paper trading simulation, live order management, real-time position tracking,
and pluggable broker adapters (Kite, Alpaca, Binance, Interactive Brokers).
"""

import csv
import json
import logging
import os
import time
from datetime import datetime
import yfinance as yf

from config import (
    COMMISSION_PER_TRADE,
    INITIAL_BALANCE,
    PORTFOLIO_FILE,
    SLIPPAGE_PCT,
    TRADES_FILE,
    USD_INR_RATE,
    WATCHLIST,
)
from risk_manager import RiskManager

logger = logging.getLogger("AlphaTrader.Execution")


class PortfolioManager:
    def __init__(self):
        self.risk_manager = RiskManager()
        self.portfolio = self.load_portfolio()
        self.ensure_trades_csv()

    def load_portfolio(self):
        """Loads persistent portfolio from JSON or creates default initial state."""
        if os.path.exists(PORTFOLIO_FILE):
            try:
                with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                logger.error(f"Error loading portfolio JSON: {e}")

        # Default initial portfolio
        default_state = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "initial_balance": INITIAL_BALANCE,
            "cash": INITIAL_BALANCE,
            "equity": INITIAL_BALANCE,
            "starting_day_equity": INITIAL_BALANCE,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "positions": {},
            "history": []
        }
        self.save_portfolio(default_state)
        return default_state

    def save_portfolio(self, state=None):
        """Saves current portfolio state to disk."""
        if state is None:
            state = self.portfolio
        try:
            with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save portfolio state: {e}")

    def ensure_trades_csv(self):
        """Ensures the trade history CSV file exists with proper headers."""
        if not os.path.exists(TRADES_FILE):
            try:
                with open(TRADES_FILE, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "timestamp", "symbol", "action", "status",
                        "quantity", "entry_price", "exit_price",
                        "pnl", "pnl_pct", "exit_reason", "pattern"
                    ])
            except Exception as e:
                logger.error(f"Error initializing trades CSV: {e}")

    def log_trade_csv(self, trade_record):
        """Appends closed trade record to CSV."""
        try:
            with open(TRADES_FILE, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    trade_record.get("exit_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    trade_record.get("symbol"),
                    trade_record.get("action"),
                    "CLOSED",
                    trade_record.get("quantity"),
                    trade_record.get("entry_price"),
                    trade_record.get("exit_price"),
                    trade_record.get("pnl"),
                    trade_record.get("pnl_pct"),
                    trade_record.get("exit_reason"),
                    trade_record.get("pattern", "N/A")
                ])
        except Exception as e:
            logger.error(f"Failed to append to trades.csv: {e}")

    def execute_signal(self, signal):
        """
        Processes a qualified signal, validates risk rules, computes sizing,
        and opens a simulated trade.
        """
        symbol = signal["symbol"]
        action = signal["action"]

        # Validate with risk manager
        is_valid, reason = self.risk_manager.validate_new_trade(signal, self.portfolio)
        if not is_valid:
            logger.info(f"[{symbol}] Trade skipped by Risk Manager: {reason}")
            return False, reason

        raw_price = signal["current_price"]
        stop_loss = signal["stop_loss"]

        # Apply realistic simulated slippage
        if action == "BUY":
            fill_price = round(raw_price * (1 + SLIPPAGE_PCT), 4)
        else:
            fill_price = round(raw_price * (1 - SLIPPAGE_PCT), 4)

        # Sizing calculation
        qty, sizing_info = self.risk_manager.calculate_position_size(
            self.portfolio["equity"],
            self.portfolio["cash"],
            fill_price,
            stop_loss,
            symbol=symbol
        )

        if qty <= 0:
            logger.warning(f"[{symbol}] Position sizing resulted in 0 shares ({sizing_info})")
            return False, str(sizing_info)

        capital_required = round(qty * fill_price, 2)
        total_cost = capital_required + COMMISSION_PER_TRADE

        if total_cost > self.portfolio["cash"]:
            return False, "Not enough cash for position + commission"

        # Deduct cash
        self.portfolio["cash"] = round(self.portfolio["cash"] - total_cost, 2)

        # Record position
        position_record = {
            "symbol": symbol,
            "action": action,
            "quantity": qty,
            "entry_price": fill_price,
            "current_price": fill_price,
            "stop_loss": stop_loss,
            "take_profit_1": signal["take_profit_1"],
            "take_profit_2": signal["take_profit_2"],
            "risk_reward_ratio": signal["risk_reward_ratio"],
            "atr": signal.get("atr", fill_price * 0.015),
            "capital_committed": capital_required,
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pattern": signal.get("pattern_name", "N/A"),
            "confidence": signal.get("confidence", 0),
            "reasons": signal.get("reasons", [])
        }

        self.portfolio["positions"][symbol] = position_record
        self.portfolio["total_trades"] += 1
        self.save_portfolio()

        logger.info(
            f"EXECUTED {action} {symbol}: {qty} units @ ${fill_price} | SL: ${stop_loss} | "
            f"TP1: ${signal['take_profit_1']} | TP2: ${signal['take_profit_2']} (Committed: ${capital_required})"
        )
        return True, position_record

    def close_position(self, symbol, current_price, exit_reason="MANUAL"):
        """Closes an open position, realizes P&L, and updates stats."""
        if symbol not in self.portfolio["positions"]:
            return None

        pos = self.portfolio["positions"].pop(symbol)
        action = pos["action"]
        qty = pos["quantity"]
        entry_price = pos["entry_price"]

        # Apply slippage on exit
        if action == "BUY":
            fill_exit_price = round(current_price * (1 - SLIPPAGE_PCT), 4)
            gross_pnl = (fill_exit_price - entry_price) * qty
        else:
            fill_exit_price = round(current_price * (1 + SLIPPAGE_PCT), 4)
            gross_pnl = (entry_price - fill_exit_price) * qty

        net_pnl = round(gross_pnl - COMMISSION_PER_TRADE, 2)
        pnl_pct = round((net_pnl / pos["capital_committed"]) * 100, 2)

        # Return capital + net PnL to cash
        returned_cash = pos["capital_committed"] + net_pnl
        self.portfolio["cash"] = round(self.portfolio["cash"] + returned_cash, 2)
        self.portfolio["realized_pnl"] = round(self.portfolio["realized_pnl"] + net_pnl, 2)

        if net_pnl > 0:
            self.portfolio["wins"] += 1
        else:
            self.portfolio["losses"] += 1

        total_closed = self.portfolio["wins"] + self.portfolio["losses"]
        self.portfolio["win_rate_pct"] = round((self.portfolio["wins"] / total_closed) * 100, 1) if total_closed > 0 else 0.0

        closed_trade = {
            **pos,
            "exit_price": fill_exit_price,
            "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exit_reason": exit_reason,
            "pnl": net_pnl,
            "pnl_pct": pnl_pct
        }

        self.portfolio["history"].append(closed_trade)
        self.log_trade_csv(closed_trade)
        self.save_portfolio()

        logger.info(f"CLOSED {symbol} ({action}): Exit ${fill_exit_price} | PnL: ${net_pnl} ({pnl_pct}%) | Reason: {exit_reason}")
        return closed_trade

    def update_open_positions(self, current_prices=None):
        """
        Polls live prices for all open positions, checks if Stop Loss or Take Profit
        were hit, moves trailing stops, and recalculates total portfolio equity.
        """
        positions = list(self.portfolio["positions"].items())
        if not positions:
            self.portfolio["equity"] = self.portfolio["cash"]
            self.portfolio["unrealized_pnl"] = 0.0
            self.save_portfolio()
            return []

        events = []
        total_market_value = 0.0
        total_unrealized_pnl = 0.0

        for symbol, pos in positions:
            curr_price = None
            if current_prices and symbol in current_prices:
                curr_price = current_prices[symbol]
            else:
                try:
                    t = yf.Ticker(symbol)
                    hist = t.history(period="1d", interval="1m")
                    if not hist.empty:
                        curr_price = float(hist["Close"].iloc[-1])
                        # If US equity, multiply by USD_INR_RATE
                        for w in WATCHLIST:
                            if w["symbol"] == symbol and w.get("type") == "us_equity":
                                curr_price = curr_price * USD_INR_RATE
                                break
                except Exception as e:
                    logger.warning(f"Could not fetch live tick for {symbol}: {e}")

            if curr_price is None:
                curr_price = pos["current_price"]

            pos["current_price"] = round(curr_price, 4)
            action = pos["action"]
            qty = pos["quantity"]
            entry_price = pos["entry_price"]
            sl = pos["stop_loss"]
            tp1 = pos["take_profit_1"]
            tp2 = pos["take_profit_2"]
            atr = pos.get("atr", curr_price * 0.015)

            # Check Auto Exits
            exit_needed = False
            exit_reason = ""

            if action == "BUY":
                if curr_price <= sl:
                    exit_needed = True
                    exit_reason = f"STOP LOSS HIT (${curr_price} <= ${sl})"
                elif curr_price >= tp2:
                    exit_needed = True
                    exit_reason = f"TAKE PROFIT 2 HIT (${curr_price} >= ${tp2})"
            elif action == "SELL":
                if curr_price >= sl:
                    exit_needed = True
                    exit_reason = f"STOP LOSS HIT (${curr_price} >= ${sl})"
                elif curr_price <= tp2:
                    exit_needed = True
                    exit_reason = f"TAKE PROFIT 2 HIT (${curr_price} <= ${tp2})"

            if exit_needed:
                closed = self.close_position(symbol, curr_price, exit_reason)
                events.append({"type": "POSITION_CLOSED", "record": closed})
                continue

            # Check Trailing Stop updates
            new_sl, sl_reason = self.risk_manager.manage_trailing_stops(pos, curr_price, atr)
            if new_sl:
                pos["stop_loss"] = new_sl
                events.append({"type": "TRAILING_STOP_UPDATED", "symbol": symbol, "new_sl": new_sl, "reason": sl_reason})
                logger.info(f"[{symbol}] {sl_reason}")

            # Calculate open position value and unrealized PnL
            if action == "BUY":
                unrealized = (curr_price - entry_price) * qty
            else:
                unrealized = (entry_price - curr_price) * qty

            pos["unrealized_pnl"] = round(unrealized, 2)
            pos["unrealized_pnl_pct"] = round((unrealized / pos["capital_committed"]) * 100, 2)

            total_market_value += pos["capital_committed"] + unrealized
            total_unrealized_pnl += unrealized

        self.portfolio["unrealized_pnl"] = round(total_unrealized_pnl, 2)
        self.portfolio["equity"] = round(self.portfolio["cash"] + total_market_value, 2)
        self.save_portfolio()

        return events


class BrokerAdapterBase:
    """Base interface for plugging in real-world broker APIs (Zerodha Kite, Alpaca, Binance)."""
    def place_order(self, symbol, side, quantity, order_type="MARKET", stop_loss=None, take_profit=None):
        raise NotImplementedError
    def get_positions(self):
        raise NotImplementedError
    def get_account_balance(self):
        raise NotImplementedError
