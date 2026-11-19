"""
Antigravity Alpha Trader - Professional Risk Management & Position Sizing Engine
Enforces strict institutional capital preservation rules:
- ATR-based dynamic trade sizing
- Maximum capital risk per trade
- Trailing stop-loss & breakeven ratchet
- Daily drawdown circuit breaker
"""

import logging
from config import (
    ALLOCATION_PER_POSITION,
    COMMISSION_PER_TRADE,
    DAILY_LOSS_LIMIT_PCT,
    MAX_OPEN_POSITIONS,
    MAX_RISK_PER_TRADE,
    MIN_RISK_REWARD_RATIO,
    WATCHLIST,
    get_market_session_info,
)

logger = logging.getLogger("AlphaTrader.RiskManager")


class RiskManager:
    def __init__(self, initial_balance=30000.0):
        self.max_risk_pct = MAX_RISK_PER_TRADE
        self.allocation_per_trade = ALLOCATION_PER_POSITION
        self.max_positions = MAX_OPEN_POSITIONS
        self.daily_loss_limit_pct = DAILY_LOSS_LIMIT_PCT
        self.min_rr = MIN_RISK_REWARD_RATIO

    def calculate_position_size(self, portfolio_equity, cash_available, entry_price, stop_loss, symbol=""):
        """
        Calculates position size: exactly allocates ₹10,000 per position (capped by available cash).
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0, "Invalid price or stop loss"

        stop_distance = abs(entry_price - stop_loss)
        if stop_distance == 0:
            return 0, "Stop loss equals entry price"

        # Equal allocation: ₹10,000 per position
        capital_to_invest = min(self.allocation_per_trade, max(cash_available - COMMISSION_PER_TRADE, 0))
        if capital_to_invest <= 0:
            return 0, "Insufficient cash available for ₹10,000 allocation"

        raw_quantity = capital_to_invest / entry_price

        # Sizing decimals:
        # Indian equities (.NS): integer shares only (NSE doesn't support fractional shares)
        if str(symbol).endswith(".NS"):
            final_quantity = int(raw_quantity)
            if final_quantity == 0 and capital_to_invest >= (entry_price * 0.9):
                final_quantity = 1
        elif "crypto" in str(symbol).lower() or "-INR" in str(symbol) or "BTC" in str(symbol) or "ETH" in str(symbol):
            final_quantity = round(raw_quantity, 6)
        else:  # US stocks allow fractional shares
            final_quantity = round(raw_quantity, 4)

        if final_quantity <= 0:
            return 0, "Position size calculated to zero"

        capital_committed = round(final_quantity * entry_price, 2)
        actual_risk = round(final_quantity * stop_distance, 2)

        return final_quantity, {
            "quantity": final_quantity,
            "capital_committed": capital_committed,
            "actual_dollar_risk": actual_risk,
            "risk_pct_of_equity": round((actual_risk / portfolio_equity) * 100, 2),
            "stop_distance": round(stop_distance, 4)
        }

    def validate_new_trade(self, signal, portfolio):
        """
        Validates whether a new trade signal conforms to all professional safety guidelines.
        """
        symbol = signal["symbol"]
        action = signal["action"]
        confidence = signal.get("confidence", 0)
        rr_ratio = signal.get("risk_reward_ratio", 0)

        # 1. Action check
        if action not in ["BUY", "SELL"]:
            return False, f"Signal action is '{action}', not executable"

        # 2. Strict Market Session Check: Never trade closed stock markets!
        asset_type = "equity"
        for item in WATCHLIST:
            if item["symbol"] == symbol:
                asset_type = item.get("type", "equity")
                break

        session_info = get_market_session_info(asset_type)
        if not session_info.get("is_open", False):
            return False, f"MARKET CLOSED: {symbol} is closed ({session_info.get('status')}). Trading halted until bell."

        # 2. Daily circuit breaker check
        starting_day_equity = portfolio.get("starting_day_equity", portfolio.get("equity", 10000.0))
        current_equity = portfolio.get("equity", 10000.0)
        daily_pnl = current_equity - starting_day_equity
        daily_loss_pct = abs(min(daily_pnl, 0)) / starting_day_equity

        if daily_loss_pct >= self.daily_loss_limit_pct:
            return False, f"CIRCUIT BREAKER ACTIVE: Daily loss ({daily_loss_pct*100:.2f}%) hit limit ({self.daily_loss_limit_pct*100:.1f}%)"

        # 3. Maximum simultaneous positions check
        open_positions = portfolio.get("positions", {})
        if len(open_positions) >= self.max_positions:
            return False, f"MAX POSITIONS REACHED: Currently holding {len(open_positions)}/{self.max_positions} positions"

        # 4. Symbol already held check
        if symbol in open_positions:
            return False, f"Already holding open position in {symbol}"

        # 5. Risk-Reward Ratio check
        if rr_ratio < self.min_rr:
            return False, f"Risk:Reward ratio {rr_ratio:.1f} is below minimum {self.min_rr:.1f}"

        # 6. Stop loss direction check
        entry_price = signal["current_price"]
        stop_loss = signal["stop_loss"]
        if action == "BUY" and stop_loss >= entry_price:
            return False, f"Invalid BUY stop loss (${stop_loss}) must be below entry (${entry_price})"
        if action == "SELL" and stop_loss <= entry_price:
            return False, f"Invalid SELL stop loss (${stop_loss}) must be above entry (${entry_price})"

        return True, "Trade passed all risk validation rules"

    def manage_trailing_stops(self, position, current_price, atr):
        """
        Updates dynamic stop-loss levels for open positions:
        - If TP1 hit: move stop-loss to Breakeven (entry price) to ensure zero risk!
        - If price pushes further: trail stop with 1.2x ATR.
        Returns: updated_stop_loss, update_reason (or None if no change).
        """
        action = position["action"]
        entry_price = position["entry_price"]
        current_sl = position["stop_loss"]
        tp1 = position["take_profit_1"]
        tp2 = position["take_profit_2"]

        if action == "BUY":
            # Condition 1: Price has hit or exceeded TP1 -> Move to Breakeven
            if current_price >= tp1 and current_sl < entry_price:
                return round(entry_price, 4), "TP1 reached: Moved Stop Loss to Break-Even (Risk-Free Trade)"

            # Condition 2: Price is significantly above TP1 -> Trail stop
            if current_price > tp1:
                trail_candidate = round(current_price - (1.2 * atr), 4)
                if trail_candidate > current_sl:
                    return trail_candidate, f"Trailing Stop Loss ratcheted up to ${trail_candidate}"

        elif action == "SELL":
            # Condition 1: Price reached TP1 -> Move to Breakeven
            if current_price <= tp1 and current_sl > entry_price:
                return round(entry_price, 4), "TP1 reached: Moved Stop Loss to Break-Even (Risk-Free Trade)"

            # Condition 2: Price is significantly below TP1 -> Trail stop
            if current_price < tp1:
                trail_candidate = round(current_price + (1.2 * atr), 4)
                if trail_candidate < current_sl:
                    return trail_candidate, f"Trailing Stop Loss ratcheted down to ${trail_candidate}"

        return None, None
