"""
Trading Suite Orchestrator & Multi-Bot Commander (With Auto-Execution & Portfolio Tracking)
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


def render_html_dashboard(b1_res, b2_res, b3_res):
    def make_section(res, bot_color, icon, bot_title, desc):
        p = res.get("portfolio", {})
        signals = res.get("signals", [])
        open_pos = p.get("open_positions", {})
        closed_trades = p.get("closed_trades", [])

        # Positions HTML
        pos_rows = ""
        if open_pos:
            for sym, pos in open_pos.items():
                pnl = pos.get("unrealized_pnl", 0.0)
                pnl_pct = pos.get("pnl_pct", 0.0)
                pnl_color = "#10b981" if pnl >= 0 else "#ef4444"
                badge_cls = "badge-buy" if pos["side"] == "BUY" else "badge-sell"
                pos_rows += f"""
                <tr>
                    <td><strong>{sym}</strong> <br><small style="color: #64748b;">{pos.get('market')}</small></td>
                    <td><span class="badge {badge_cls}">{pos['side']}</span></td>
                    <td>{pos['entry_price']}</td>
                    <td>{pos['current_price']}</td>
                    <td style="color: {pnl_color}; font-weight: 700;">{'+' if pnl>=0 else ''}₹{pnl:,.2f} ({pnl_pct:+.2f}%)</td>
                </tr>
                """
        else:
            pos_rows = '<tr><td colspan="5" style="text-align: center; color: #64748b; padding: 12px;">No open positions. Capital safely preserved in cash.</td></tr>'

        # Signals Cards
        cards_html = ""
        for s in signals:
            act = s.get("action", "HOLD")
            conf = s.get("confidence", 50)
            badge_cls = "badge-buy" if "BUY" in act else ("badge-sell" if "SELL" in act else "badge-hold")
            cards_html += f"""
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
            </div>
            """

        tot_pnl = p.get('realized_pnl', 0) + p.get('unrealized_pnl', 0)
        pnl_color = "#10b981" if tot_pnl >= 0 else "#ef4444"

        return f"""
        <div class="column">
            <div class="col-title" style="color: {bot_color};">
                <span>{icon} {bot_title}</span>
                <span class="equity-badge">₹{p.get('equity', 30000):,.2f}</span>
            </div>
            <div class="col-desc">{desc}</div>

            <!-- Stats Bar -->
            <div class="stats-bar">
                <div>Cash: <strong>₹{p.get('cash', 30000):,.2f}</strong></div>
                <div>Net P&L: <strong style="color: {pnl_color};">{'+' if tot_pnl>=0 else ''}₹{tot_pnl:,.2f}</strong></div>
                <div>Positions: <strong>{len(open_pos)} Active</strong></div>
            </div>

            <!-- Open Trades Table -->
            <h4 style="font-size: 13px; color: #94a3b8; margin: 16px 0 8px 0; text-transform: uppercase;">Active Executed Trades ({len(open_pos)})</h4>
            <div style="overflow-x: auto; margin-bottom: 16px;">
                <table class="pos-table">
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Side</th>
                            <th>Entry</th>
                            <th>Current</th>
                            <th>PnL</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pos_rows}
                    </tbody>
                </table>
            </div>

            <!-- Strategy Signals -->
            <h4 style="font-size: 13px; color: #94a3b8; margin: 16px 0 8px 0; text-transform: uppercase;">Sub-Bot Signals Radar</h4>
            {cards_html}
        </div>
        """

    s1 = make_section(b1_res, "#60a5fa", "🪐", "MASTER BOT 1", "<strong>Macro Anomalies & Trend Suite</strong><br>TOTM (Indian) + 100/250 SMA (Crypto) + Z-Score Mean Rev (Forex)")
    s2 = make_section(b2_res, "#c084fc", "⚡", "MASTER BOT 2", "<strong>Momentum & Breakout Suite</strong><br>Dual RSI 4/7 (Indian) + Donchian 200EMA (Crypto) + London Breakout (Forex)")
    s3 = make_section(b3_res, "#34d399", "🎯", "MASTER BOT 3", "<strong>Precision Intraday & Trend</strong><br>PDH/PDL Retest (Indian) + Peak Seasonality (Crypto) + 200-Donchian Chandelier (Gold)")

    now_str = datetime.now().strftime("%d %b %Y | %I:%M:%S %p IST")

    html = f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>3 Master Bots Quantitative Suite (Auto-Execution)</title>
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
    .equity-badge {{ font-size: 13px; font-family: 'JetBrains Mono', monospace; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 3px 10px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.3); }}
    .col-desc {{ font-size: 12px; color: var(--text-muted); margin-bottom: 16px; line-height: 1.4; }}
    .stats-bar {{ display: flex; justify-content: space-between; background: #0c121d; padding: 10px 14px; border-radius: 8px; font-size: 12px; color: var(--text-muted); margin-bottom: 14px; border: 1px solid rgba(255, 255, 255, 0.05); }}
    .stats-bar strong {{ color: #f8fafc; font-family: 'JetBrains Mono', monospace; }}
    .pos-table {{ width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }}
    .pos-table th {{ color: #64748b; font-size: 10px; text-transform: uppercase; padding: 6px 4px; border-bottom: 1px solid var(--border); }}
    .pos-table td {{ padding: 8px 4px; border-bottom: 1px solid rgba(255, 255, 255, 0.04); font-family: 'JetBrains Mono', monospace; font-size: 12px; }}
    .card {{ background: #0c121d; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; padding: 14px; margin-bottom: 14px; }}
    .card-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .mkt-tag {{ font-size: 10px; font-weight: 700; color: var(--accent-blue); background: rgba(56, 189, 248, 0.1); padding: 2px 6px; border-radius: 4px; letter-spacing: 0.5px; }}
    .badge {{ font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 4px; }}
    .badge-buy {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-sell {{ background: rgba(239, 68, 68, 0.15); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.3); }}
    .badge-hold {{ background: rgba(148, 163, 184, 0.1); color: var(--text-muted); border: 1px solid rgba(148, 163, 184, 0.2); }}
    .price-row {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }}
    .sym {{ font-size: 15px; font-weight: 700; color: #fff; }}
    .price {{ font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: #e2e8f0; }}
    .strat-name {{ font-size: 11px; font-weight: 600; color: var(--accent-orange); margin-bottom: 8px; }}
    .reason {{ background: rgba(0, 0, 0, 0.3); padding: 8px 10px; border-radius: 6px; font-size: 11px; color: #cbd5e1; line-height: 1.45; border-left: 2px solid var(--accent-blue); }}
</style>
</head>
<body>
    <header>
        <div>
            <h1>⚡ QUANT MULTI-ASSET TRADING SUITE</h1>
            <p class="subtitle">3 Master Bots · Real-Time Auto-Execution & Portfolio Tracking (₹90,000 Total Capital Allocation)</p>
        </div>
        <div style="text-align: right; font-size: 12px; color: var(--text-muted);">
            Last Live Scan: <strong style="color: var(--accent-green);">{now_str}</strong>
        </div>
    </header>

    <div class="cols">
        {s1}
        {s2}
        {s3}
    </div>
</body>
</html>
"""
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n📊 Master Visual Dashboard saved to: {DASHBOARD_FILE}")


def run_suite(bot_choice="all"):
    print("\n" + "="*85)
    print("        🌐 QUANT MULTI-ASSET TRADING SUITE (AUTO-EXECUTION ENABLED)")
    print("="*85)

    bot1 = MasterBot1_MacroAnomalies()
    bot2 = MasterBot2_MomentumBreakout()
    bot3 = MasterBot3_PrecisionIntraday()

    b1_res, b2_res, b3_res = {}, {}, {}

    if bot_choice in ["1", "all"]:
        b1_res = bot1.run_cycle()

    if bot_choice in ["2", "all"]:
        b2_res = bot2.run_cycle()

    if bot_choice in ["3", "all"]:
        b3_res = bot3.run_cycle()

    if bot_choice == "all":
        render_html_dashboard(b1_res, b2_res, b3_res)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Bot Trading Suite")
    parser.add_argument("--bot", choices=["1", "2", "3", "all"], default="all", help="Choose which Master Bot to execute")
    args = parser.parse_args()

    run_suite(args.bot)
