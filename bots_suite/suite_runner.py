"""
Trading Suite Orchestrator & Multi-Bot Commander (With Auto-Execution & Portfolio Tracking)
Runs both Original Master Bots (Tier 1-3) and Smart v2 Master Bots (Smart Tier 1-3 with Breakeven Locker & Trailing Stop).
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


def render_html_dashboard(b1_res, b2_res, b3_res, sb1_res=None, sb2_res=None, sb3_res=None):
    def make_section(res, bot_color, icon, bot_title, desc, is_smart=False):
        if not res:
            res = {}
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

                smart_badges = ""
                if is_smart:
                    if pos.get("breakeven_locked"):
                        smart_badges += ' <span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; font-size: 10px; padding: 2px 5px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.4);" title="Stop loss moved to entry price">🛡️ B/E</span>'
                    if pos.get("trailing_active"):
                        smart_badges += ' <span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-size: 10px; padding: 2px 5px; border-radius: 4px; border: 1px solid rgba(245, 158, 11, 0.4);" title="Trailing stop locking 70% peak gain">🔒 Trail</span>'

                pos_rows += f"""
                <tr>
                    <td><strong>{sym}</strong>{smart_badges} <br><small style="color: #64748b;">{pos.get('market')}</small></td>
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
        smart_label = '<span class="smart-badge">SMART v2</span>' if is_smart else '<span class="orig-badge">ORIGINAL</span>'

        return f"""
        <div class="column {'column-smart' if is_smart else ''}">
            <div class="col-title" style="color: {bot_color};">
                <span>{icon} {bot_title} {smart_label}</span>
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

    # Compute Summary Totals
    def get_eq(r):
        return r.get("portfolio", {}).get("equity", 30000.0) if r else 30000.0

    def get_pnl(r):
        if not r: return 0.0
        p = r.get("portfolio", {})
        return p.get("realized_pnl", 0.0) + p.get("unrealized_pnl", 0.0)

    orig_eq = get_eq(b1_res) + get_eq(b2_res) + get_eq(b3_res)
    orig_pnl = get_pnl(b1_res) + get_pnl(b2_res) + get_pnl(b3_res)

    smart_eq = get_eq(sb1_res) + get_eq(sb2_res) + get_eq(sb3_res)
    smart_pnl = get_pnl(sb1_res) + get_pnl(sb2_res) + get_pnl(sb3_res)

    tot_suite_equity = orig_eq + smart_eq
    tot_suite_capital = 180000.0

    # Section HTML
    s1 = make_section(b1_res, "#60a5fa", "🪐", "MASTER BOT 1", "<strong>Macro Anomalies & Trend</strong><br>TOTM (Indian) + 100/250 SMA (Crypto) + Z-Score Mean Rev (Forex)", is_smart=False)
    s2 = make_section(b2_res, "#c084fc", "⚡", "MASTER BOT 2", "<strong>Momentum & Breakout</strong><br>Dual RSI 4/7 (Indian) + Donchian 200EMA (Crypto) + London Breakout (Forex)", is_smart=False)
    s3 = make_section(b3_res, "#34d399", "🎯", "MASTER BOT 3", "<strong>Precision Intraday</strong><br>PDH/PDL Retest (Indian) + Peak Seasonality (Crypto) + 200-Donchian (Gold)", is_smart=False)

    sb1 = make_section(sb1_res, "#38bdf8", "🪐", "SMART BOT 1", "<strong>Smart v2: Breakeven & Trailing Stop</strong><br>TOTM (Indian) + 100/250 SMA (Crypto) + Z-Score Mean Rev (Forex)", is_smart=True)
    sb2 = make_section(sb2_res, "#e879f9", "⚡", "SMART BOT 2", "<strong>Smart v2: Breakeven & Trailing Stop</strong><br>Dual RSI 4/7 (Indian) + Donchian 200EMA (Crypto) + London Breakout (Forex)", is_smart=True)
    sb3 = make_section(sb3_res, "#2dd4bf", "🎯", "SMART BOT 3", "<strong>Smart v2: Breakeven & Trailing Stop</strong><br>PDH/PDL Retest (Indian) + Peak Seasonality (Crypto) + 200-Donchian (Gold)", is_smart=True)

    now_str = datetime.now().strftime("%d %b %Y | %I:%M:%S %p IST")

    html = f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>6 Master Bots Quantitative Suite (A/B Test Arena)</title>
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
    header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 24px; }}
    h1 {{ font-size: 24px; font-weight: 700; background: linear-gradient(90deg, #38bdf8, #818cf8, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    .subtitle {{ font-size: 13px; color: var(--text-muted); margin-top: 4px; }}
    
    /* Comparison Bar */
    .compare-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 28px; }}
    .compare-card {{ background: rgba(16, 23, 38, 0.8); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }}
    .compare-card.smart-card {{ border-color: rgba(56, 189, 248, 0.4); background: linear-gradient(180deg, rgba(56, 189, 248, 0.08) 0%, rgba(16, 23, 38, 0.8) 100%); }}
    .compare-title {{ font-size: 13px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 8px; display: flex; justify-content: space-between; }}
    .compare-val {{ font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #fff; }}
    .compare-sub {{ font-size: 12px; margin-top: 4px; }}

    .section-head {{ font-size: 16px; font-weight: 700; color: var(--text); margin: 28px 0 16px 0; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
    .cols {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 24px; }}
    .column {{ background: rgba(16, 23, 38, 0.6); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }}
    .column-smart {{ border-color: rgba(56, 189, 248, 0.3); background: rgba(16, 23, 38, 0.75); }}
    .col-title {{ font-size: 16px; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; justify-content: space-between; }}
    .equity-badge {{ font-size: 13px; font-family: 'JetBrains Mono', monospace; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 3px 10px; border-radius: 12px; border: 1px solid rgba(56, 189, 248, 0.3); }}
    .smart-badge {{ font-size: 10px; background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid rgba(56, 189, 248, 0.4); margin-left: 6px; }}
    .orig-badge {{ font-size: 10px; background: rgba(148, 163, 184, 0.15); color: #94a3b8; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-left: 6px; }}
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
            <p class="subtitle">6 Master Bots · A/B Testing Arena (3 Original + 3 Smart v2) · ₹1,80,000 Allocation</p>
        </div>
        <div style="text-align: right; font-size: 12px; color: var(--text-muted);">
            Last Live Scan: <strong style="color: var(--accent-green);">{now_str}</strong>
        </div>
    </header>

    <!-- Executive Comparison Bar -->
    <div class="compare-grid">
        <div class="compare-card smart-card">
            <div class="compare-title">
                <span>🛡️ Smart v2 Bots (3 Bots)</span>
                <span style="color: var(--accent-blue);">Breakeven + Trailing</span>
            </div>
            <div class="compare-val">₹{smart_eq:,.2f}</div>
            <div class="compare-sub" style="color: {'#10b981' if smart_pnl>=0 else '#ef4444'};">
                Net P&L: {'+' if smart_pnl>=0 else ''}₹{smart_pnl:,.2f} ({((smart_eq - 90000)/90000*100):+.2f}%)
            </div>
        </div>
        <div class="compare-card">
            <div class="compare-title">
                <span>📊 Original Bots (3 Bots)</span>
                <span style="color: var(--text-muted);">Standard SL/TP</span>
            </div>
            <div class="compare-val">₹{orig_eq:,.2f}</div>
            <div class="compare-sub" style="color: {'#10b981' if orig_pnl>=0 else '#ef4444'};">
                Net P&L: {'+' if orig_pnl>=0 else ''}₹{orig_pnl:,.2f} ({((orig_eq - 90000)/90000*100):+.2f}%)
            </div>
        </div>
        <div class="compare-card">
            <div class="compare-title">
                <span>🌐 Combined Suite Equity</span>
                <span style="color: var(--accent-purple);">6 Bots Live</span>
            </div>
            <div class="compare-val">₹{tot_suite_equity:,.2f}</div>
            <div class="compare-sub" style="color: #94a3b8;">
                Allocated Capital: ₹{tot_suite_capital:,.2f}
            </div>
        </div>
    </div>

    <!-- ROW 1: SMART V2 MASTER BOTS -->
    <div class="section-head">
        <span>🛡️ SMART V2 MASTER BOTS (Breakeven Locker & Chandelier Trailing Stop)</span>
    </div>
    <div class="cols">
        {sb1}
        {sb2}
        {sb3}
    </div>

    <!-- ROW 2: ORIGINAL MASTER BOTS -->
    <div class="section-head">
        <span>📊 ORIGINAL MASTER BOTS (Standard Fixed SL / TP Benchmarks)</span>
    </div>
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
    print("   🌐 QUANT MULTI-ASSET TRADING SUITE: 6 MASTER BOTS A/B ARENA")
    print("="*85)

    # 3 Original Master Bots
    bot1 = MasterBot1_MacroAnomalies(bot_id=1, is_smart=False)
    bot2 = MasterBot2_MomentumBreakout(bot_id=2, is_smart=False)
    bot3 = MasterBot3_PrecisionIntraday(bot_id=3, is_smart=False)

    # 3 Smart v2 Master Bots
    smart_bot1 = MasterBot1_MacroAnomalies(bot_id="_smart_1", is_smart=True)
    smart_bot2 = MasterBot2_MomentumBreakout(bot_id="_smart_2", is_smart=True)
    smart_bot3 = MasterBot3_PrecisionIntraday(bot_id="_smart_3", is_smart=True)

    b1_res, b2_res, b3_res = {}, {}, {}
    sb1_res, sb2_res, sb3_res = {}, {}, {}

    if bot_choice in ["1", "all"]:
        b1_res = bot1.run_cycle()
        sb1_res = smart_bot1.run_cycle(signals=b1_res.get("signals"))

    if bot_choice in ["2", "all"]:
        b2_res = bot2.run_cycle()
        sb2_res = smart_bot2.run_cycle(signals=b2_res.get("signals"))

    if bot_choice in ["3", "all"]:
        b3_res = bot3.run_cycle()
        sb3_res = smart_bot3.run_cycle(signals=b3_res.get("signals"))

    if bot_choice == "all":
        render_html_dashboard(b1_res, b2_res, b3_res, sb1_res, sb2_res, sb3_res)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-Bot Trading Suite")
    parser.add_argument("--bot", choices=["1", "2", "3", "all"], default="all", help="Choose which Master Bot to execute")
    args = parser.parse_args()

    run_suite(args.bot)
