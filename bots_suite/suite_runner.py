"""
Trading Suite Orchestrator & Multi-Bot Commander
Orchestrates:
- Master Bot 1: Macro Anomalies & Trend Suite (TOTM + 100/250 SMA + Z-Score Mean Reversion)
- Master Bot 2: Momentum & Breakout Suite (Dual RSI + Donchian 200EMA + London Breakout)
- Master Bot 3: Precision Intraday & Structural Trend (PDH/PDL Retest + Peak Seasonality + 200-Donchian Chandelier)
"""

import argparse
import sys
import os
from datetime import datetime

# Ensure bots_suite is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from tabulate import tabulate
from bot_tier1_macro_anomalies import MasterBot1_MacroAnomalies
from bot_tier2_momentum_breakout import MasterBot2_MomentumBreakout
from bot_tier3_precision_intraday import MasterBot3_PrecisionIntraday

DASHBOARD_FILE = os.path.join(BASE_DIR, "suite_dashboard.html")


def render_html_dashboard(b1_signals, b2_signals, b3_signals):
    def make_cards(signals):
        h = ""
        for s in signals:
            act = s.get("action", "HOLD")
            conf = s.get("confidence", 50)
            badge_cls = "badge-buy" if "BUY" in act else ("badge-sell" if "SELL" in act else "badge-hold")
            h += f"""
            <div class="card">
                <div class="card-head">
                    <span class="mkt-tag">{s.get('market')}</span>
                    <span class="badge {badge_cls}">{act} ({conf:.0f}%)</span>
                </div>
                <div class="price-row">
                    <span class="sym">{s.get('symbol')}</span>
                    <span class="price">{s.get('current_price')}</span>
                </div>
                <div class="strat-name">{s.get('strategy')}</div>
                <div class="reason">• {s.get('reason')}</div>
                <div class="footer-meta">
                    <span>SL: <strong>{s.get('suggested_sl', 'N/A')}</strong></span>
                    <span>TP: <strong>{s.get('suggested_tp', 'N/A')}</strong></span>
                    <span>Alloc: <strong>₹{s.get('allocated_capital', 10000):,.0f}</strong></span>
                </div>
            </div>
            """
        return h

    c1 = make_cards(b1_signals)
    c2 = make_cards(b2_signals)
    c3 = make_cards(b3_signals)
    now_str = datetime.now().strftime("%d %b %Y | %I:%M:%S %p IST")

    html = f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>3 Master Bots Quantitative Suite</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
    :root {{
        --bg-dark: #080c14;
        --card-bg: #101726;
        --border: #1e293b;
        --accent-blue: #38bdf8;
        --accent-green: #10b981;
        --accent-red: #ef4444;
        --accent-purple: #c084fc;
        --accent-orange: #fb923c;
        --text: #f8fafc;
        --text-muted: #94a3b8;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg-dark); color: var(--text); font-family: 'Plus Jakarta Sans', sans-serif; padding: 24px; }}
    header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 28px; }}
    h1 {{ font-size: 24px; font-weight: 700; background: linear-gradient(90deg, #38bdf8, #818cf8, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .subtitle {{ font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
    .cols {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; }}
    .column {{ background: rgba(16, 23, 38, 0.6); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }}
    .col-title {{ font-size: 16px; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between; }}
    .col-desc {{ font-size: 12px; color: var(--text-muted); margin-bottom: 16px; line-height: 1.4; }}
    .card {{ background: #0c121d; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; padding: 14px; margin-bottom: 14px; }}
    .card-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .mkt-tag {{ font-size: 10px; font-weight: 700; color: var(--accent-blue); background: rgba(56, 189, 248, 0.1); padding: 2px 6px; border-radius: 4px; letter-spacing: 0.5px; }}
    .badge {{ font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; }}
    .badge-buy {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-sell {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); }}
    .badge-hold {{ background: rgba(148, 163, 184, 0.1); color: var(--text-muted); border: 1px solid rgba(148, 163, 184, 0.2); }}
    .price-row {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }}
    .sym {{ font-size: 16px; font-weight: 700; color: #fff; }}
    .price {{ font-family: 'JetBrains Mono', monospace; font-size: 16px; font-weight: 700; color: #e2e8f0; }}
    .strat-name {{ font-size: 12px; font-weight: 600; color: var(--accent-orange); margin-bottom: 8px; }}
    .reason {{ background: rgba(0, 0, 0, 0.3); padding: 8px 10px; border-radius: 6px; font-size: 12px; color: #cbd5e1; line-height: 1.45; margin-bottom: 10px; border-left: 2px solid var(--accent-blue); }}
    .footer-meta {{ display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 8px; }}
    .footer-meta strong {{ color: #cbd5e1; }}
</style>
</head>
<body>
    <header>
        <div>
            <h1>⚡ QUANT MULTI-ASSET TRADING SUITE</h1>
            <p class="subtitle">3 Master Bots · 9 Systematic Trading Strategies (Nifty 50, Bitcoin, Forex Pairs & Commodities)</p>
        </div>
        <div style="text-align: right; font-size: 12px; color: var(--text-muted);">
            Last Live Scan: <strong style="color: var(--accent-green);">{now_str}</strong>
        </div>
    </header>

    <div class="cols">
        <!-- BOT 1 -->
        <div class="column">
            <div class="col-title" style="color: #60a5fa;">
                <span>🪐 MASTER BOT 1</span>
                <span style="font-size: 12px; background: rgba(96, 165, 250, 0.15); padding: 2px 8px; border-radius: 12px;">₹30,000</span>
            </div>
            <div class="col-desc"><strong>Macro Anomalies & Trend Suite</strong><br>Option 1: Nifty Turn-of-Month + BTC 100/250 SMA + Forex Z-Score Mean Reversion</div>
            {c1}
        </div>

        <!-- BOT 2 -->
        <div class="column">
            <div class="col-title" style="color: #c084fc;">
                <span>⚡ MASTER BOT 2</span>
                <span style="font-size: 12px; background: rgba(192, 132, 252, 0.15); padding: 2px 8px; border-radius: 12px;">₹30,000</span>
            </div>
            <div class="col-desc"><strong>Momentum & Breakout Suite</strong><br>Option 2: Nifty 4/7-Day RSI + BTC Donchian 200-EMA + London Open Breakout & Retest</div>
            {c2}
        </div>

        <!-- BOT 3 -->
        <div class="column">
            <div class="col-title" style="color: #34d399;">
                <span>🎯 MASTER BOT 3</span>
                <span style="font-size: 12px; background: rgba(52, 211, 153, 0.15); padding: 2px 8px; border-radius: 12px;">₹30,000</span>
            </div>
            <div class="col-desc"><strong>Precision Intraday & Structural Trend</strong><br>Option 3: Nifty PDH/PDL Retest + BTC Peak Seasonality + Multi-Asset 200-Day Donchian</div>
            {c3}
        </div>
    </div>
</body>
</html>
"""
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📊 Master Visual Dashboard saved to: {DASHBOARD_FILE}")


def run_suite(bot_choice="all"):
    print("\n" + "="*85)
    print("        🌐 QUANT MULTI-ASSET TRADING SUITE (3 MASTER BOTS x 9 STRATEGIES)")
    print("="*85)

    bot1 = MasterBot1_MacroAnomalies()
    bot2 = MasterBot2_MomentumBreakout()
    bot3 = MasterBot3_PrecisionIntraday()

    b1_signals, b2_signals, b3_signals = [], [], []

    if bot_choice in ["1", "all"]:
        r1 = bot1.run_cycle()
        b1_signals = r1.get("signals", [])

    if bot_choice in ["2", "all"]:
        r2 = bot2.run_cycle()
        b2_signals = r2.get("signals", [])

    if bot_choice in ["3", "all"]:
        r3 = bot3.run_cycle()
        b3_signals = r3.get("signals", [])

    all_signals = b1_signals + b2_signals + b3_signals

    if bot_choice == "all":
        print("\n\n" + "#"*85)
        print("          🏆 CONSOLIDATED 9-STRATEGY MASTER RADAR DASHBOARD")
        print("#"*85)

        master_table = []
        for s in all_signals:
            action = s.get("action", "")
            action_badge = f"🟢 {action}" if "BUY" in action else (f"🔴 {action}" if "SELL" in action else f"⚪ {action}")
            master_table.append([
                s.get("market"),
                s.get("strategy"),
                s.get("symbol"),
                action_badge,
                f"{s.get('confidence', 0):.0f}%",
                s.get("current_price"),
                f"₹{s.get('allocated_capital', 10000):,.0f}"
            ])

        print(tabulate(master_table, headers=["Market", "Strategy", "Asset", "Signal", "Conf", "Price", "Capital"], tablefmt="fancy_grid"))
        render_html_dashboard(b1_signals, b2_signals, b3_signals)
        print("\n💡 Tip: To run a specific bot alone, use: python suite_runner.py --bot 1 (or 2 or 3)\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Bot Trading Suite")
    parser.add_argument("--bot", choices=["1", "2", "3", "all"], default="all", help="Choose which Master Bot to execute")
    args = parser.parse_args()

    run_suite(args.bot)
