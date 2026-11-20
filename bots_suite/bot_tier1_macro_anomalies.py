"""
Master Bot 1: Macro Anomalies & Trend Suite (Tier 1)
Combines Option 1 from all 3 markets from nifty_crypto_forex.html:
- Sub-Bot 1 (Indian): NIFTY 50 Turn-of-the-Month (TOTM) Anomaly
- Sub-Bot 2 (Crypto): BTC 100 / 250 SMA Golden Cross Trend Following
- Sub-Bot 3 (Forex/US): Major Pairs Mean Reversion (Z-Score +-2.0)
"""

import json
import os
import sys
from datetime import datetime
from tabulate import tabulate

from strategies.indian_strategies import NiftyTurnOfTheMonthStrategy
from strategies.crypto_strategies import CryptoSmaTrendFollowingStrategy
from strategies.forex_strategies import ForexZScoreMeanReversionStrategy

STATE_FILE = os.path.join(os.path.dirname(__file__), "state_tier1.json")


class MasterBot1_MacroAnomalies:
    def __init__(self, initial_capital=30000.0):
        self.bot_name = "Master Bot 1: Macro Anomalies & Trend Suite"
        self.initial_capital = initial_capital
        self.capital_per_market = initial_capital / 3.0  # ₹10,000 per market

        # Sub-Bots
        self.subbot_indian = NiftyTurnOfTheMonthStrategy(symbol="^NSEI")
        self.subbot_crypto = CryptoSmaTrendFollowingStrategy(symbol="BTC-USD")
        self.subbot_forex = ForexZScoreMeanReversionStrategy(pair1="EURUSD=X", pair2="GBPUSD=X")

    def run_cycle(self):
        print(f"\n{'='*75}")
        print(f"🚀 RUNNING: {self.bot_name.upper()}")
        print(f"{'='*75}")

        signals = []

        # 1. Evaluate Indian NIFTY TOTM
        print("\n[Sub-Bot 1 - Indian NIFTY] Scanning Turn-of-the-Month Anomaly...")
        res_ind = self.subbot_indian.evaluate()
        res_ind["market"] = "INDIAN_NIFTY"
        res_ind["allocated_capital"] = self.capital_per_market
        signals.append(res_ind)

        # 2. Evaluate Crypto 100/250 SMA
        print("[Sub-Bot 2 - Crypto] Scanning BTC 100/250 SMA Trend...")
        res_cry = self.subbot_crypto.evaluate()
        res_cry["market"] = "CRYPTO"
        res_cry["allocated_capital"] = self.capital_per_market
        signals.append(res_cry)

        # 3. Evaluate Forex Z-Score Mean Reversion
        print("[Sub-Bot 3 - Forex] Scanning EUR/USD vs GBP/USD Z-Score...")
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

        # Save state
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "bot_name": self.bot_name,
            "total_capital": self.initial_capital,
            "allocation_per_subbot": self.capital_per_market,
            "signals": signals
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        return state_data


if __name__ == "__main__":
    bot = MasterBot1_MacroAnomalies()
    bot.run_cycle()
