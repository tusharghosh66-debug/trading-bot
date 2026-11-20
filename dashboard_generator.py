"""
Antigravity Alpha Trader - Interactive Web Dashboard Generator (INR Mode)
Builds a modern, responsive single-page visual dashboard with live metrics in INR (₹).
"""

import json
import os
from datetime import datetime, timezone, timedelta
from config import (
    ALLOCATION_PER_POSITION,
    CURRENCY_SYMBOL,
    DASHBOARD_FILE,
    INITIAL_BALANCE,
    INTELLIGENCE_FILE,
    PORTFOLIO_FILE,
    SIGNALS_FILE,
    get_market_session_info,
)


def generate_dashboard():
    # Load portfolio
    portfolio = {}
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                portfolio = json.load(f)
        except Exception:
            pass

    # Load intelligence
    intelligence = {}
    if os.path.exists(INTELLIGENCE_FILE):
        try:
            with open(INTELLIGENCE_FILE, "r", encoding="utf-8") as f:
                intelligence = json.load(f)
        except Exception:
            pass

    # Load signals
    signals = []
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
                signals = json.load(f)
        except Exception:
            pass

    # Extract metrics
    equity = portfolio.get("equity", INITIAL_BALANCE)
    cash = portfolio.get("cash", INITIAL_BALANCE)
    realized_pnl = portfolio.get("realized_pnl", 0.0)
    unrealized_pnl = portfolio.get("unrealized_pnl", 0.0)
    total_pnl = round(realized_pnl + unrealized_pnl, 2)
    win_rate = portfolio.get("win_rate_pct", 0.0)
    wins = portfolio.get("wins", 0)
    losses = portfolio.get("losses", 0)
    total_trades = portfolio.get("total_trades", 0)
    positions = portfolio.get("positions", {})
    history = portfolio.get("history", [])

    fng = intelligence.get("fear_and_greed", {"value": 50, "classification": "Neutral"})
    market_regime = intelligence.get("market_regime", "NEUTRAL / BALANCED")
    composite_score = intelligence.get("composite_score", 0.0)
    macro_news = intelligence.get("macro_news", [])

    sym_curr = CURRENCY_SYMBOL
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist_str = datetime.now(ist).strftime('%I:%M:%S %p IST')

    # Dynamic Indian Market Session Check
    nse_session = get_market_session_info("indian_equity")
    if nse_session.get("is_open", False):
        nse_badge = '<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4);">LIVE OPEN</span>'
        nse_desc = 'NSE/BSE Regular Session (09:15 AM - 03:30 PM IST). Actively scanning Indian equities.'
    else:
        nse_badge = '<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4);">CLOSED</span>'
        nse_desc = 'Market closed (09:15 AM - 03:30 PM IST). Opens next trading session at 09:15 AM IST.'

    # Dynamic US Market Session Check
    us_session = get_market_session_info("us_equity")
    if "LIVE OPEN" in us_session.get("status", ""):
        us_badge = '<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4);">LIVE OPEN (Wall Street)</span>'
        us_desc = 'NYSE & Nasdaq Active (08:00 PM - 02:30 AM IST). Real-time US execution (Priced in INR ₹).'
    elif "PRE-MARKET" in us_session.get("status", ""):
        us_badge = '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4);">PRE-MARKET (Opens 08:00 PM)</span>'
        us_desc = 'Pre-market active. Regular opening bell at 08:00 PM IST (Wall Street).'
    else:
        us_badge = '<span class="badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4);">CLOSED</span>'
        us_desc = 'US Market closed (Regular: 08:00 PM - 02:30 AM IST). Opens tonight at 08:00 PM IST.'

    # Format positions HTML
    positions_html = ""
    if positions:
        for sym, pos in positions.items():
            pnl = pos.get("unrealized_pnl", 0.0)
            pnl_pct = pos.get("unrealized_pnl_pct", 0.0)
            pnl_class = "text-green" if pnl >= 0 else "text-red"
            badge_class = "badge-buy" if pos["action"] == "BUY" else "badge-sell"
            positions_html += f"""
            <tr>
                <td><strong>{sym}</strong></td>
                <td><span class="badge {badge_class}">{pos['action']}</span></td>
                <td>{sym_curr}{pos['entry_price']:,.2f}</td>
                <td>{sym_curr}{pos['current_price']:,.2f}</td>
                <td><span class="text-orange">{sym_curr}{pos['stop_loss']:,.2f}</span></td>
                <td><span class="text-green">{sym_curr}{pos['take_profit_2']:,.2f}</span></td>
                <td class="{pnl_class}"><strong>{'+' if pnl>=0 else ''}{sym_curr}{pnl:,.2f} ({'+' if pnl_pct>=0 else ''}{pnl_pct}%)</strong></td>
                <td>{sym_curr}{pos.get('capital_committed', 0):,.2f}</td>
                <td>{pos.get('entry_time', '')}</td>
            </tr>
            """
    else:
        positions_html = '<tr><td colspan="9" class="text-center text-muted" style="text-align: center; padding: 20px;">No open positions currently held. Bot evaluates signals and allocates ₹10,000 per valid setup.</td></tr>'

    # Format history HTML
    history_html = ""
    if history:
        for t in reversed(history[-10:]):
            pnl = t.get("pnl", 0.0)
            pnl_pct = t.get("pnl_pct", 0.0)
            pnl_class = "text-green" if pnl >= 0 else "text-red"
            badge_class = "badge-buy" if t["action"] == "BUY" else "badge-sell"
            history_html += f"""
            <tr>
                <td>{t.get('exit_time', '')}</td>
                <td><strong>{t.get('symbol')}</strong></td>
                <td><span class="badge {badge_class}">{t.get('action')}</span></td>
                <td>{sym_curr}{t.get('entry_price', 0):,.2f}</td>
                <td>{sym_curr}{t.get('exit_price', 0):,.2f}</td>
                <td class="{pnl_class}"><strong>{'+' if pnl>=0 else ''}{sym_curr}{pnl:,.2f} ({'+' if pnl_pct>=0 else ''}{pnl_pct}%)</strong></td>
                <td><small>{t.get('exit_reason', '')}</small></td>
            </tr>
            """
    else:
        history_html = '<tr><td colspan="7" class="text-center text-muted" style="text-align: center; padding: 20px;">No closed trades recorded yet.</td></tr>'

    # Format signals HTML
    signals_html = ""
    if signals:
        for s in signals:
            act = s.get("action", "HOLD")
            conf = s.get("confidence", 0)
            if "BUY" in act:
                badge_class = "badge-buy"
            elif "SELL" in act:
                badge_class = "badge-sell"
            else:
                badge_class = "badge-neutral"

            conf_color = "#10b981" if conf >= 65 else ("#f59e0b" if conf >= 40 else "#6b7280")
            reasons_str = "<br>• ".join(s.get("reasons", [])[:3])

            signals_html += f"""
            <div class="signal-card">
                <div class="signal-header">
                    <div>
                        <span class="signal-symbol">{s.get('symbol')}</span>
                        <span class="badge {badge_class}">{act}</span>
                    </div>
                    <div class="confidence-box" style="color: {conf_color}">
                        {conf}% Confidence
                    </div>
                </div>
                <div class="signal-body">
                    <div class="metric-row">
                        <span>Current Price:</span> <strong>{sym_curr}{s.get('current_price', 0):,.2f}</strong>
                    </div>
                    <div class="metric-row">
                        <span>Pattern:</span> <em>{s.get('pattern_name', 'N/A')}</em>
                    </div>
                    <div class="metric-row">
                        <span>Stop Loss (SL):</span> <strong class="text-orange">{sym_curr}{s.get('stop_loss', 0):,.2f}</strong>
                    </div>
                    <div class="metric-row">
                        <span>Take Profit 1 (TP1):</span> <strong class="text-green">{sym_curr}{s.get('take_profit_1', 0):,.2f}</strong>
                    </div>
                    <div class="metric-row">
                        <span>Take Profit 2 (TP2):</span> <strong class="text-green">{sym_curr}{s.get('take_profit_2', 0):,.2f}</strong> (R:R {s.get('risk_reward_ratio')}:1)
                    </div>
                    <div class="reasons-box">
                        <small>• {reasons_str}</small>
                    </div>
                </div>
            </div>
            """
    else:
        signals_html = '<div class="text-muted p-4">No recent signals scanned. Run bot scanner to generate live setups.</div>'

    # Format news HTML
    news_html = ""
    if macro_news:
        for n in macro_news[:8]:
            tag = n.get("sentiment_tag", "NEUTRAL")
            score = n.get("sentiment_score", 0.0)
            badge_class = "badge-buy" if tag == "BULLISH" else ("badge-sell" if tag == "BEARISH" else "badge-neutral")
            news_html += f"""
            <div class="news-item">
                <span class="badge {badge_class}">{tag} ({score:+.2f})</span>
                <span class="news-title">{n.get('title')}</span>
            </div>
            """
    else:
        news_html = '<div class="text-muted">No macro news headlines gathered yet.</div>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Antigravity Alpha Trader - AI Command Center (INR ₹)</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #0b0f17;
            --bg-card: #131a26;
            --border-card: #1f293d;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-orange: #f59e0b;
            --text-main: #f3f4f6;
            --text-muted: #9ca3af;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-main);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            padding: 24px;
            font-size: 14px;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .brand h1 {{
            font-size: 22px;
            font-weight: 700;
            background: linear-gradient(90deg, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .status-pill {{
            background: rgba(16, 185, 129, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 6px 14px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .status-pill::before {{
            content: "";
            width: 8px;
            height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent-green);
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .metric-card {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 18px;
        }}
        .metric-label {{
            color: var(--text-muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}
        .metric-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 700;
        }}
        .text-green {{ color: var(--accent-green); }}
        .text-red {{ color: var(--accent-red); }}
        .text-orange {{ color: var(--accent-orange); }}
        .text-muted {{ color: var(--text-muted); }}

        .layout-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
            margin-bottom: 24px;
        }}
        @media (max-width: 1024px) {{
            .layout-grid {{ grid-template-columns: 1fr; }}
        }}
        .panel {{
            background: var(--bg-card);
            border: 1px solid var(--border-card);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 24px;
        }}
        .panel h2 {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-card);
        }}
        th {{
            color: var(--text-muted);
            font-size: 11px;
            text-transform: uppercase;
        }}
        .badge {{
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            display: inline-block;
        }}
        .badge-buy {{ background: rgba(16, 185, 129, 0.2); color: var(--accent-green); border: 1px solid rgba(16, 185, 129, 0.4); }}
        .badge-sell {{ background: rgba(239, 68, 68, 0.2); color: var(--accent-red); border: 1px solid rgba(239, 68, 68, 0.4); }}
        .badge-neutral {{ background: rgba(156, 163, 175, 0.2); color: var(--text-muted); border: 1px solid rgba(156, 163, 175, 0.4); }}

        .signals-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}
        .signal-card {{
            background: #0f1520;
            border: 1px solid var(--border-card);
            border-radius: 10px;
            padding: 16px;
        }}
        .signal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .signal-symbol {{
            font-weight: 700;
            font-size: 16px;
            margin-right: 8px;
        }}
        .confidence-box {{
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 6px;
            font-size: 13px;
        }}
        .reasons-box {{
            margin-top: 10px;
            background: rgba(0, 0, 0, 0.2);
            padding: 8px;
            border-radius: 6px;
            color: var(--text-muted);
            line-height: 1.4;
        }}
        .news-item {{
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }}
        .news-title {{
            font-size: 13px;
            line-height: 1.4;
        }}
        .sentiment-gauge {{
            background: #0f1520;
            border-radius: 10px;
            padding: 16px;
            text-align: center;
            margin-bottom: 16px;
        }}
        .sentiment-score {{
            font-size: 32px;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            margin: 8px 0;
        }}
    </style>
</head>
<body>
    <header>
        <div class="brand">
            <h1>⚡ ANTIGRAVITY ALPHA TRADER</h1>
            <span style="color: var(--text-muted); font-size: 12px;">Indian & Global AI Quant Bot (INR ₹)</span>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
            <a href="/suite" target="_blank" style="text-decoration: none; background: rgba(56, 189, 248, 0.15); border: 1px solid #38bdf8; color: #38bdf8; font-size: 11px; font-weight: 700; padding: 6px 12px; border-radius: 6px; display: inline-flex; align-items: center; gap: 6px;">
                🪐 3 MASTER BOTS SUITE (9 STRATEGIES) ↗
            </a>
            <div class="status-pill">EQUAL ALLOCATION ENGINE (₹10,000 EACH)</div>
            <span class="text-muted" style="font-size: 12px;">Auto-refresh: 30s | {now_ist_str}</span>
        </div>
    </header>

    <!-- METRICS -->
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Total Portfolio Capital</div>
            <div class="metric-value">{sym_curr}{equity:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Available Free Cash</div>
            <div class="metric-value">{sym_curr}{cash:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Total Net P&L</div>
            <div class="metric-value {'text-green' if total_pnl >= 0 else 'text-red'}">
                {'+' if total_pnl >= 0 else ''}{sym_curr}{total_pnl:,.2f}
            </div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Win Rate / Trades</div>
            <div class="metric-value">{win_rate:.1f}% <span style="font-size: 14px; color: var(--text-muted);">({wins}W / {losses}L)</span></div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Allocation Per Position</div>
            <div class="metric-value text-green">{sym_curr}{ALLOCATION_PER_POSITION:,.2f}</div>
        </div>
    </div>

    <!-- MAIN PANELS -->
    <div class="layout-grid">
        <div>
            <!-- OPEN POSITIONS -->
            <div class="panel">
                <h2>📈 Active Open Positions ({len(positions)} / 3)</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Symbol</th>
                                <th>Type</th>
                                <th>Entry</th>
                                <th>Current</th>
                                <th>Stop Loss (SL)</th>
                                <th>Target (TP2)</th>
                                <th>Unrealized P&L</th>
                                <th>Allocated</th>
                                <th>Entered At</th>
                            </tr>
                        </thead>
                        <tbody>
                            {positions_html}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- LIVE SIGNALS -->
            <div class="panel">
                <h2>🎯 High-Probability Candlestick Signals ({len(signals)})</h2>
                <div class="signals-grid">
                    {signals_html}
                </div>
            </div>

            <!-- TRADE HISTORY -->
            <div class="panel">
                <h2>📜 Closed Trades Ledger</h2>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Exit Time</th>
                                <th>Symbol</th>
                                <th>Type</th>
                                <th>Entry</th>
                                <th>Exit</th>
                                <th>Realized P&L</th>
                                <th>Exit Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- SIDEBAR: MARKET INTELLIGENCE -->
        <div>
            <!-- GLOBAL MARKET SESSIONS -->
            <div class="panel">
                <h2>🕒 Global Markets Status (Live Clock)</h2>
                <div style="background: #0f1520; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span>🪙 <strong>Crypto (BTC / ETH / SOL)</strong></span>
                        <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.4);">24/7 LIVE OPEN</span>
                    </div>
                    <small class="text-muted">Trades 24 hours a day, 365 days a year without closing (Priced in INR ₹).</small>
                </div>

                <div style="background: #0f1520; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span>🇮🇳 <strong>Indian Market (NSE / BSE)</strong></span>
                        {nse_badge}
                    </div>
                    <small class="text-muted">{nse_desc}</small>
                </div>

                <div style="background: #0f1520; padding: 12px; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span>🇺🇸 <strong>US Market (NYSE / Nasdaq)</strong></span>
                        {us_badge}
                    </div>
                    <small class="text-muted">{us_desc}</small>
                </div>
            </div>

            <div class="panel">
                <h2>🌐 Daily Internet Market Intelligence</h2>
                <div class="sentiment-gauge">
                    <div class="metric-label">Macro Regime</div>
                    <div style="font-weight: 700; font-size: 16px; color: {'var(--accent-green)' if 'BULLISH' in market_regime else ('var(--accent-red)' if 'BEARISH' in market_regime else 'var(--accent-orange)')};">
                        {market_regime}
                    </div>
                    <div class="sentiment-score {'text-green' if composite_score > 0 else ('text-red' if composite_score < 0 else 'text-muted')}">
                        {composite_score:+.1f}
                    </div>
                    <small class="text-muted">Scale: -100 (Extreme Panic) to +100 (Extreme Euphoria)</small>
                </div>

                <h3 style="font-size: 13px; color: var(--text-muted); margin: 16px 0 8px 0; text-transform: uppercase;">
                    Top Macro Driving News
                </h3>
                <div class="news-list">
                    {news_html}
                </div>
            </div>

            <div class="panel">
                <h2>🛡️ Equal Allocation Risk Rules</h2>
                <div class="metric-row" style="margin-bottom: 10px;">
                    <span>Total Portfolio:</span> <strong>₹30,000.00</strong>
                </div>
                <div class="metric-row" style="margin-bottom: 10px;">
                    <span>Equal Share Per Trade:</span> <strong class="text-green">₹10,000.00 each</strong>
                </div>
                <div class="metric-row" style="margin-bottom: 10px;">
                    <span>Max Open Positions:</span> <strong>3 (3 x ₹10k = ₹30k)</strong>
                </div>
                <div class="metric-row" style="margin-bottom: 10px;">
                    <span>Risk-to-Reward Target:</span> <strong>Minimum 1:2.0</strong>
                </div>
                <div class="metric-row" style="margin-bottom: 10px;">
                    <span>Daily Circuit Breaker:</span> <strong>4.0% (₹1,200 max loss)</strong>
                </div>
                <div class="metric-row">
                    <span>Brokerage Modeling:</span> <strong>₹20 / order flat</strong>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
    try:
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"Error saving dashboard: {e}")
    return DASHBOARD_FILE


if __name__ == "__main__":
    path = generate_dashboard()
    print(f"Dashboard generated at: {path}")
