"""
Generates modern visual dashboard for the 3 Master Bots Suite
"""

import json
import os
from datetime import datetime


def generate_suite_dashboard_html(all_signals, output_path):
    now_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    cards_html = ""
    for s in all_signals:
        action = s.get("action", "HOLD")
        conf = s.get("confidence", 50)
        badge_style = "background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981;" if "BUY" in action else (
            "background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444;" if "SELL" in action else
            "background: rgba(156, 163, 175, 0.2); color: #9ca3af; border: 1px solid #9ca3af;"
        )

        cards_html += f"""
        <div style="background: #131a26; border: 1px solid #1f293d; border-radius: 10px; padding: 16px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-size: 11px; text-transform: uppercase; color: #3b82f6; font-weight: 600;">{s.get('market')}</span>
                <span style="padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 700; {badge_style}">{action}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                <h3 style="margin: 0; font-size: 17px; color: #f3f4f6;">{s.get('symbol')}</h3>
                <span style="font-family: monospace; font-size: 16px; font-weight: 700; color: #10b981;">{s.get('current_price')}</span>
            </div>
            <p style="margin: 0 0 8px 0; font-size: 12px; color: #9ca3af;">{s.get('strategy')}</p>
            <div style="background: #0b0f17; padding: 8px; border-radius: 6px; font-size: 12px; color: #d1d5db; line-height: 1.4;">
                • {s.get('reason')}
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 11px; color: #6b7280; margin-top: 8px;">
                <span>SL: {s.get('suggested_sl', 'N/A')}</span>
                <span>TP: {s.get('suggested_tp', 'N/A')}</span>
                <span>Cap: ₹{s.get('allocated_capital', 10000):,.0f}</span>
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>3 Master Bots Quantitative Suite Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
    body {{ background: #0b0f17; color: #f3f4f6; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 24px; }}
    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1f293d; padding-bottom: 16px; margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .bot-section {{ background: #0f1520; border: 1px solid #1f293d; border-radius: 12px; padding: 20px; }}
    .bot-title {{ font-size: 16px; font-weight: 700; margin: 0 0 16px 0; display: flex; align-items: center; gap: 8px; }}
</style>
</head>
<body>
    <div class="header">
        <div>
            <h1 style="margin: 0; font-size: 24px; background: linear-gradient(90deg, #60a5fa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                ⚡ QUANT MULTI-ASSET TRADING SUITE
            </h1>
            <p style="margin: 4px 0 0; font-size: 13px; color: #9ca3af;">3 Master Bots · 9 Research-Backed Strategies (Nifty, Crypto, Forex)</p>
        </div>
        <div style="text-align: right; font-size: 12px; color: #6b7280;">
            Auto-Updated: <strong style="color: #9ca3af;">{now_str}</strong>
        </div>
    </div>

    <div class="grid">
        <!-- BOT 1 -->
        <div class="bot-section">
            <h2 class="bot-title" style="color: #60a5fa;">🪐 MASTER BOT 1: Macro Anomalies & Trend</h2>
            <p style="font-size: 12px; color: #9ca3af; margin-top: -8px; margin-bottom: 16px;">Option 1: Nifty TOTM + BTC 100/250 SMA + Forex Z-Score</p>
            {cards_html.split("</div>")[0] if len(cards_html) > 0 else ""}
        </div>
    </div>
</body>
</html>
"""
    return html
