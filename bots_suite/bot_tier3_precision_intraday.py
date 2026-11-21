"""
Master Bot 3: Precision Intraday & Structural Trend Suite (Tier 3)
Combines Option 3 from all 3 markets from nifty_crypto_forex.html:
- Sub-Bot 1 (Indian): NIFTY Previous Day High/Low (PDH/PDL) Break & Retest
- Sub-Bot 2 (Crypto): BTC Peak-Hour Intraday Seasonality (21:00-23:00 UTC)
- Sub-Bot 3 (Forex/US): Multi-Asset 200-Day Donchian + 6-ATR Chandelier Trend
"""

import json
import os
import sys
from datetime import datetime
from tabulate import tabulate

from strategies.indian_strategies import NiftyPdhPdlBreakRetestStrategy
from strategies.crypto_strategies import CryptoPeakHourSeasonalityStrategy
from strategies.forex_strategies import MultiAssetDonchianTrendStrategy
from execution import MasterBotPortfolio


class MasterBot3_PrecisionIntraday:
    def __init__(self, bot_id=3, is_smart=False, initial_capital=30000.0):
        self.bot_id = bot_id
        self.is_smart = is_smart
        smart_tag = " (Smart v2 - Breakeven & Trailing)" if is_smart else ""
        self.bot_name = f"Master Bot 3: Precision Intraday & Structural Trend Suite{smart_tag}"
        self.portfolio_mgr = MasterBotPortfolio(bot_id=bot_id, initial_capital=initial_capital, is_smart=is_smart)
        self.capital_per_market = initial_capital / 3.0

        # Sub-Bots
        self.subbot_indian = NiftyPdhPdlBreakRetestStrategy(symbol="^NSEI")
        self.subbot_crypto = CryptoPeakHourSeasonalityStrategy(symbol="BTC-USD")
        self.subbot_forex = MultiAssetDonchianTrendStrategy(symbol="GC=F")

    def run_cycle(self, signals=None):
        print(f"\n{'='*75}")
        print(f"🚀 RUNNING: {self.bot_name.upper()}")
        print(f"{'='*75}")

        if signals is None:
            signals = []

            # 1. Evaluate Indian NIFTY PDH/PDL Retest
            print("\n[Sub-Bot 1 - Indian NIFTY] Scanning PDH/PDL Break & Retest...")
            res_ind = self.subbot_indian.evaluate()
            res_ind["market"] = "INDIAN_NIFTY"
            res_ind["allocated_capital"] = self.capital_per_market
            signals.append(res_ind)

            # 2. Evaluate Crypto Peak Seasonality
            print("[Sub-Bot 2 - Crypto] Scanning BTC Peak Seasonality Window...")
            res_cry = self.subbot_crypto.evaluate()
            res_cry["market"] = "CRYPTO"
            res_cry["allocated_capital"] = self.capital_per_market
            signals.append(res_cry)

            # 3. Evaluate Multi-Asset Donchian 200 + Chandelier
            print("[Sub-Bot 3 - Multi-Asset / Commodity] Scanning Gold 200-Day Donchian Trend...")
            res_fx = self.subbot_forex.evaluate()
            res_fx["market"] = "MULTI_ASSET_GOLD"
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
        print(f"💰 Bot {self.bot_id} Equity: ₹{p['equity']:,.2f} | Cash: ₹{p['cash']:,.2f} | Open Positions: {len(p['open_positions'])}")

        return state_data


if __name__ == "__main__":
    bot = MasterBot3_PrecisionIntraday()
    bot.run_cycle()
