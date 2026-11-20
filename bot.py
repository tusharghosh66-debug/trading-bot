"""
Antigravity Alpha Trader - Master Orchestrator
Automates the full professional trading cycle:
1. Internet news & macroeconomic sentiment gathering
2. Candlestick pattern recognition & multi-factor technical analysis
3. Dynamic position sizing & risk validation
4. Paper trade execution & trailing stop management
5. Live dashboard generation
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from tabulate import tabulate

from candle_engine import CandleEngine
from config import (
    AUTO_SCAN_INTERVAL_SECONDS,
    CURRENCY_SYMBOL,
    DATA_DIR,
    INITIAL_BALANCE,
    MIN_SIGNAL_CONFIDENCE,
    PORTFOLIO_CHECK_SECONDS,
    SIGNALS_FILE,
    WATCHLIST,
    WEB_SERVER_HOST,
    WEB_SERVER_PORT,
)
from dashboard_generator import generate_dashboard
from execution_engine import PortfolioManager
from market_intelligence import MarketIntelligenceCollector
from web_server import start_server_daemon

try:
    import sys
    suite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bots_suite")
    if suite_path not in sys.path:
        sys.path.insert(0, suite_path)
    from suite_runner import run_suite
except Exception as e:
    run_suite = None

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(DATA_DIR, "trading_bot.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("AlphaTrader.Master")


class AlphaTraderBot:
    def __init__(self):
        self.intelligence = MarketIntelligenceCollector()
        self.candle_engine = CandleEngine()
        self.portfolio_mgr = PortfolioManager()
        self.last_scan_time = 0
        self.current_dossier = None
        self.current_signals = []

    def run_market_intelligence(self, force=False):
        """Step 1: Collect internet news and market sentiment before trading."""
        logger.info("==================================================")
        logger.info("STEP 1: COLLECTING INTERNET MARKET INTELLIGENCE...")
        logger.info("==================================================")
        dossier = self.intelligence.collect_full_intelligence(force_refresh=force)
        self.current_dossier = dossier
        logger.info(f"Market Sentiment Regime: {dossier['market_regime']} (Score: {dossier['composite_score']}/100)")
        logger.info(f"Crypto / Market Fear & Greed: {dossier['fear_and_greed']['value']} ({dossier['fear_and_greed']['classification']})")
        return dossier

    def scan_candlesticks_and_generate_signals(self):
        """Step 2: Technical analysis and candlestick pattern recognition on watchlist."""
        if not self.current_dossier:
            self.run_market_intelligence()

        macro_regime = self.current_dossier.get("market_regime", "NEUTRAL")
        symbol_intel = self.current_dossier.get("symbol_intelligence", {})

        logger.info("==================================================")
        logger.info("STEP 2: SCANNING CANDLESTICKS & PRICE ACTION...")
        logger.info("==================================================")

        signals = []
        for item in WATCHLIST:
            sym = item["symbol"]
            sym_bias = symbol_intel.get(sym, {}).get("sentiment_tag", "NEUTRAL")
            try:
                sig = self.candle_engine.analyze_symbol(sym, sentiment_bias=sym_bias, macro_regime=macro_regime)
                if sig:
                    signals.append(sig)
                    logger.info(
                        f"[{sym}] Price: ${sig['current_price']} | Signal: {sig['action']} ({sig['confidence']}%) | "
                        f"Pattern: {sig['pattern_name']} | SL: ${sig['stop_loss']} | TP2: ${sig['take_profit_2']}"
                    )
            except Exception as e:
                logger.error(f"Error scanning {sym}: {e}")

        # Sort signals by confidence descending
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        self.current_signals = signals

        # Save to file
        try:
            with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
                json.dump(signals, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving signals file: {e}")

        generate_dashboard()
        return signals

    def execute_qualified_signals(self):
        """Step 3: Execute trades for setups meeting professional confluence standards."""
        if not self.current_signals:
            self.scan_candlesticks_and_generate_signals()

        logger.info("==================================================")
        logger.info("STEP 3: EVALUATING TRADES FOR EXECUTION...")
        logger.info("==================================================")

        executed_count = 0
        for sig in self.current_signals:
            action = sig.get("action")
            confidence = sig.get("confidence", 0)

            # We execute only BUY or SELL with confidence >= threshold
            if action in ["BUY", "SELL"] and confidence >= MIN_SIGNAL_CONFIDENCE:
                success, info = self.portfolio_mgr.execute_signal(sig)
                if success:
                    executed_count += 1
            else:
                if action in ["BUY", "SELL"]:
                    logger.info(f"[{sig['symbol']}] Signal confidence {confidence}% below execution threshold {MIN_SIGNAL_CONFIDENCE}%.")

        logger.info(f"Execution cycle complete. Newly opened positions: {executed_count}")
        generate_dashboard()
        return executed_count

    def monitor_positions(self):
        """Step 4: Check Stop-Loss, Take-Profit targets and manage trailing stops."""
        events = self.portfolio_mgr.update_open_positions()
        if events:
            generate_dashboard()
        return events

    def print_terminal_report(self):
        """Displays formatted tables in terminal."""
        portfolio = self.portfolio_mgr.portfolio

        print("\n" + "="*80)
        print("          ANTIGRAVITY ALPHA TRADER - EXECUTIVE DASHBOARD")
        print("="*80)

        cs = CURRENCY_SYMBOL
        # Overview Stats
        stats = [
            ["Equity", f"{cs}{portfolio.get('equity', 0):,.2f}", "Cash Available", f"{cs}{portfolio.get('cash', 0):,.2f}"],
            ["Realized P&L", f"{cs}{portfolio.get('realized_pnl', 0):,.2f}", "Unrealized P&L", f"{cs}{portfolio.get('unrealized_pnl', 0):,.2f}"],
            ["Win Rate", f"{portfolio.get('win_rate_pct', 0)}%", "Total Trades", f"{portfolio.get('total_trades', 0)}"],
            ["Wins / Losses", f"{portfolio.get('wins', 0)}W / {portfolio.get('losses', 0)}L", "Open Positions", f"{len(portfolio.get('positions', {}))} / 3"]
        ]
        print(tabulate(stats, tablefmt="fancy_grid"))

        # Market Intelligence
        if self.current_dossier:
            print("\n--- TODAY'S MARKET INTELLIGENCE & SENTIMENT ---")
            fng = self.current_dossier.get("fear_and_greed", {})
            print(f"Market Regime   : {self.current_dossier.get('market_regime')}")
            print(f"Sentiment Score : {self.current_dossier.get('composite_score')}/100")
            print(f"Fear & Greed    : {fng.get('value')} ({fng.get('classification')})")

        # Open Positions
        positions = portfolio.get("positions", {})
        if positions:
            print("\n--- ACTIVE OPEN POSITIONS ---")
            pos_table = []
            for sym, p in positions.items():
                pos_table.append([
                    sym, p["action"], p["quantity"], f"{cs}{p['entry_price']:,.2f}",
                    f"{cs}{p['current_price']:,.2f}", f"{cs}{p['stop_loss']:,.2f}", f"{cs}{p['take_profit_2']:,.2f}",
                    f"{cs}{p.get('unrealized_pnl', 0):,.2f} ({p.get('unrealized_pnl_pct', 0)}%)",
                    f"{cs}{p.get('capital_committed', 0):,.2f}"
                ])
            print(tabulate(pos_table, headers=["Symbol", "Type", "Qty", "Entry", "Current", "Stop Loss", "Target", "PnL", "Allocated"], tablefmt="grid"))
        else:
            print("\n[INFO] No open positions currently active.")

        # Latest Signals
        if self.current_signals:
            print("\n--- LATEST SCANNED SIGNALS ---")
            sig_table = []
            for s in self.current_signals[:6]:
                sig_table.append([
                    s["symbol"], s["action"], f"{s['confidence']}%", s["pattern_name"],
                    f"{cs}{s['current_price']:,.2f}", f"{cs}{s['stop_loss']:,.2f}", f"{cs}{s['take_profit_2']:,.2f}", f"{s['risk_reward_ratio']}:1"
                ])
            print(tabulate(sig_table, headers=["Symbol", "Signal", "Confidence", "Candle Pattern", "Price", "SL", "TP2", "R:R"], tablefmt="grid"))

        print("="*80 + "\n")

    def run_auto_loop(self):
        """
        Continuous 24/7 Automated Trading Engine.
        Scans internet intelligence, examines candles, executes high-confidence setups,
        monitors stop losses & take profits in real time, and serves live dashboard.
        """
        logger.info("Starting Antigravity Alpha Trader 24/7 Automated Loop...")
        server = start_server_daemon()
        if server:
            logger.info(f"Dashboard accessible at: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/")

        # Initial full startup cycle
        self.run_market_intelligence(force=True)
        self.scan_candlesticks_and_generate_signals()
        self.execute_qualified_signals()

        # Run 3 Master Bots Suite (9 Quant Strategies)
        if run_suite:
            try:
                logger.info("Executing 3 Master Bots Suite (9 Quant Strategies)...")
                run_suite("all")
            except Exception as e:
                logger.error(f"Error running 3 Master Bots Suite: {e}")

        self.print_terminal_report()
        self.last_scan_time = time.time()

        try:
            while True:
                time.sleep(PORTFOLIO_CHECK_SECONDS)

                # Step A: High-frequency position monitoring & Trailing Stop check
                self.monitor_positions()

                # Step B: Periodic full internet & candlestick scan (every 5 mins)
                now = time.time()
                if now - self.last_scan_time >= AUTO_SCAN_INTERVAL_SECONDS:
                    logger.info("Triggering scheduled market scan & intelligence refresh...")
                    self.run_market_intelligence(force=True)
                    self.scan_candlesticks_and_generate_signals()
                    self.execute_qualified_signals()

                    # Periodic execution of 3 Master Bots Suite
                    if run_suite:
                        try:
                            logger.info("Running periodic 3 Master Bots Suite cycle...")
                            run_suite("all")
                        except Exception as e:
                            logger.error(f"Error in 3 Master Bots Suite cycle: {e}")

                    self.print_terminal_report()
                    self.last_scan_time = now

        except KeyboardInterrupt:
            logger.info("Automated loop stopped by user.")


def main():
    parser = argparse.ArgumentParser(description="Antigravity Alpha Trader - Institutional AI Trading Bot")
    parser.add_argument("--scan", action="store_true", help="Run one full market scan, intelligence gather, and signal generation")
    parser.add_argument("--trade", action="store_true", help="Run scan and execute qualified paper trades")
    parser.add_argument("--report", action="store_true", help="Print account and portfolio summary report")
    parser.add_argument("--dashboard", action="store_true", help="Start only the web dashboard server")
    parser.add_argument("--auto", action="store_true", help="Run 24/7 automated trading loop")

    args = parser.parse_args()
    bot = AlphaTraderBot()

    if args.dashboard:
        start_server_daemon()
        print(f"Dashboard running at http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    elif args.scan:
        bot.run_market_intelligence(force=True)
        bot.scan_candlesticks_and_generate_signals()
        bot.print_terminal_report()
    elif args.trade:
        bot.run_market_intelligence(force=True)
        bot.scan_candlesticks_and_generate_signals()
        bot.execute_qualified_signals()
        bot.print_terminal_report()
    elif args.report:
        bot.monitor_positions()
        bot.print_terminal_report()
    else:
        # Default behavior: run automated loop
        bot.run_auto_loop()


if __name__ == "__main__":
    main()
