"""
Master Bot 2: Momentum & Breakout Suite (Tier 2)
Combines Option 2 from all 3 markets from nifty_crypto_forex.html:
- Sub-Bot 1 (Indian): NIFTY 4-Day / 7-Day Dual RSI Momentum
- Sub-Bot 2 (Crypto): Bitcoin Donchian 20-Day & 200-EMA Momentum
- Sub-Bot 3 (Forex/US): London Open Breakout & Retest with Fakeout Filter
"""

import json
import os
import sys
from datetime import datetime
from tabulate import tabulate

from strategies.indian_strategies import NiftyDualRsiStrategy
from strategies.crypto_strategies import CryptoDonchianMomentumStrategy
from strategies.forex_strategies import ForexLondonBreakoutStrategy
from execution import MasterBotPortfolio


class MasterBot2_MomentumBreakout:
    def __init__(self, initial_capital=30000.0):
        self.bot_name = "Master Bot 2: Momentum & Breakout Suite"
        self.portfolio_mgr = MasterBotPortfolio(bot_id=2, initial_capital=initial_capital)
        self.capital_per_market = initial_capital / 3.0

        # Sub-Bots
        self.subbot_indian = NiftyDualRsiStrategy(symbol="^NSEI")
        self.subbot_crypto = CryptoDonchianMomentumStrategy(symbol="BTC-USD")
        self.subbot_forex = ForexLondonBreakoutStrategy(symbol="GBPUSD=X")

    def run_cycle(self):
        print(f"\n{'='*75}")
        print(f"🚀 RUNNING: {self.bot_name.upper()}")
        print(f"{'='*75}")

        signals = []

        # 1. Evaluate Indian NIFTY Dual RSI
        print("\n[Sub-Bot 1 - Indian NIFTY] Scanning 4-Day/7-Day RSI Momentum...")
        res_ind = self.subbot_indian.evaluate()
        res_ind["market"] = "INDIAN_NIFTY"
        res_ind["allocated_capital"] = self.capital_per_market
        signals.append(res_ind)

        # 2. Evaluate Crypto Donchian 200EMA
        print("[Sub-Bot 2 - Crypto] Scanning BTC Donchian & 200-EMA Breakout...")
        res_cry = self.subbot_crypto.evaluate()
        res_cry["market"] = "CRYPTO"
        res_cry["allocated_capital"] = self.capital_per_market
        signals.append(res_cry)

        # 3. Evaluate Forex London Breakout
        print("[Sub-Bot 3 - Forex] Scanning London Open Breakout & Retest...")
        res_fx = self.subbot_forex.evaluate()
        res_fx["market"] = "FOREX"
        res_fx["allocated_capital"] = self.capital_per_market
        signals.append(res_fx)

        # Display summary table
        rows = []
        for s in signals:
            rows.append([
                s.get("market"),
                s.get("strategy"),
                s.get("symbol"),
                s.get("action"),
                f"{s.get('confidence', 0):.0f}%",
                s.get("current_price"),
                f"SL: {s.get('suggested_sl', 0)} | TP: {s.get('suggested_tp', 0)}"
            ])

        print("\n" + tabulate(rows, headers=["Market", "Strategy", "Asset", "Action", "Confidence", "Price", "Targets"], tablefmt="fancy_grid"))

        # Process automated execution
        state_data = self.portfolio_mgr.process_signals(signals, min_confidence=65.0)
        p = state_data["portfolio"]
        print(f"💰 Bot 2 Equity: ₹{p['equity']:,.2f} | Cash: ₹{p['cash']:,.2f} | Open Positions: {len(p['open_positions'])}")

        return state_data


if __name__ == "__main__":
    bot = MasterBot2_MomentumBreakout()
    bot.run_cycle()
