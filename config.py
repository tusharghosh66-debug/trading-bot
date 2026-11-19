"""
Antigravity Alpha Trader - Configuration Module (INR Global Mode)
Total Portfolio Capital: ₹30,000 INR
Equal Allocation: ₹10,000 per position (Max 3 positions)
Markets Covered: Indian Stocks (NSE), US Tech Stocks (NYSE/Nasdaq), 24/7 Crypto
"""

import os
from datetime import datetime, timezone, timedelta, time as dtime

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")
TRADES_FILE = os.path.join(DATA_DIR, "trades.csv")
INTELLIGENCE_FILE = os.path.join(DATA_DIR, "market_intelligence.json")
SIGNALS_FILE = os.path.join(DATA_DIR, "latest_signals.json")
DASHBOARD_FILE = os.path.join(BASE_DIR, "dashboard.html")

# Currency Configuration
CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"
USD_INR_RATE = 88.50  # USD to INR conversion rate for US Stocks

# Global Watchlist: Indian Bluechips (NSE), US Tech Stocks, 24/7 Crypto
WATCHLIST = [
    # 🪙 24/7 Live Crypto (INR)
    {"symbol": "BTC-INR", "name": "Bitcoin INR", "type": "crypto"},
    {"symbol": "ETH-INR", "name": "Ethereum INR", "type": "crypto"},
    {"symbol": "SOL-INR", "name": "Solana INR", "type": "crypto"},

    # 🇺🇸 US Tech Leaders (Active 08:00 PM - 02:30 AM IST)
    {"symbol": "NVDA", "name": "Nvidia Corporation (US)", "type": "us_equity"},
    {"symbol": "TSLA", "name": "Tesla Inc (US)", "type": "us_equity"},
    {"symbol": "AAPL", "name": "Apple Inc (US)", "type": "us_equity"},
    {"symbol": "MSFT", "name": "Microsoft Corporation (US)", "type": "us_equity"},

    # 🇮🇳 Indian Bluechips (Active 09:15 AM - 03:30 PM IST)
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries (NSE)", "type": "indian_equity"},
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services (NSE)", "type": "indian_equity"},
    {"symbol": "INFY.NS", "name": "Infosys Ltd (NSE)", "type": "indian_equity"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank (NSE)", "type": "indian_equity"},
    {"symbol": "SBIN.NS", "name": "State Bank of India (NSE)", "type": "indian_equity"},
    {"symbol": "ITC.NS", "name": "ITC Ltd (NSE)", "type": "indian_equity"},
]

# Timeframes
MACRO_TIMEFRAME = "1d"        # For Macro Trend
EXECUTION_TIMEFRAME = "1h"    # For Candle Patterns & Entry/Exit
DATA_PERIOD = "60d"           # Lookback

# Portfolio & Allocation Rules (Strict ₹30,000 Total, ₹10,000 Equal per Position)
INITIAL_BALANCE = 30000.00          # Total Capital in ₹ (INR)
ALLOCATION_PER_POSITION = 10000.00  # Exact ₹10,000 allocated per trade
MAX_OPEN_POSITIONS = 3              # Max 3 positions (3 x ₹10,000 = ₹30,000)
MAX_RISK_PER_TRADE = 0.02           # Max 2% capital risk per trade
DAILY_LOSS_LIMIT_PCT = 0.04         # 4.0% daily circuit breaker (₹1,200 max loss)
MIN_RISK_REWARD_RATIO = 2.0         # Minimum 1:2 R:R
MIN_SIGNAL_CONFIDENCE = 55.0        # Confluence threshold

# Execution Mode & Brokerage
EXECUTION_MODE = "PAPER"
SLIPPAGE_PCT = 0.0005               # 0.05% slippage
COMMISSION_PER_TRADE = 20.0         # ₹20.00 standard brokerage per order

# Automated Loop Intervals
AUTO_SCAN_INTERVAL_SECONDS = 300    # 5 minutes
PORTFOLIO_CHECK_SECONDS = 30        # 30 seconds

# Web Dashboard
WEB_SERVER_PORT = int(os.environ.get("PORT", 5000))
WEB_SERVER_HOST = os.environ.get("HOST", "0.0.0.0")


def get_market_session_info(asset_type="indian_equity"):
    """
    Checks real-time market session:
    - Crypto: Always 24/7/365 Open.
    - Indian Market (NSE): Mon-Fri 09:15 AM to 03:30 PM IST.
    - US Market (NYSE/Nasdaq): Mon-Fri 08:00 PM to 02:30 AM IST (Pre-market: 06:00 PM).
    """
    if asset_type == "crypto":
        return {
            "is_open": True,
            "status": "LIVE 24/7 OPEN",
            "desc": "Crypto trades 24/7 continuously in INR"
        }

    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    weekday = now_ist.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

    # US Equity Market Check
    if asset_type == "us_equity":
        if weekday >= 5:
            return {
                "is_open": False,
                "status": "WEEKEND CLOSED",
                "desc": "US Market closed for weekend (Opens Monday 08:00 PM IST)"
            }
        now_time = now_ist.time()
        # US regular session: 08:00 PM to 02:30 AM IST
        is_us_open = (now_time >= dtime(20, 0)) or (now_time < dtime(2, 30))
        is_pre_market = dtime(18, 0) <= now_time < dtime(20, 0)

        if is_us_open:
            return {
                "is_open": True,
                "status": "LIVE OPEN (Wall Street)",
                "desc": f"NYSE/Nasdaq Regular Trading Session ({now_ist.strftime('%I:%M %p IST')})"
            }
        elif is_pre_market:
            return {
                "is_open": True,  # Allow pre-market signal generation and AMO execution
                "status": "PRE-MARKET (Bell at 08:00 PM IST)",
                "desc": f"Pre-market active. Regular opening bell at 08:00 PM IST ({now_ist.strftime('%I:%M %p IST')})"
            }
        else:
            return {
                "is_open": False,
                "status": "US CLOSED",
                "desc": f"US Market closed. Opens at 08:00 PM IST."
            }

    # Indian Equity Market Check
    if weekday >= 5:
        return {
            "is_open": False,
            "status": "WEEKEND CLOSED",
            "desc": "NSE/BSE closed for weekend (Opens Monday 09:15 AM IST)"
        }

    now_time = now_ist.time()
    market_open = dtime(9, 15)
    market_close = dtime(15, 30)

    if market_open <= now_time <= market_close:
        return {
            "is_open": True,
            "status": "NSE LIVE SESSION OPEN",
            "desc": f"Indian Stock Market Open ({now_ist.strftime('%I:%M %p IST')})"
        }
    else:
        return {
            "is_open": False,
            "status": "NSE CLOSED (After-Market)",
            "desc": f"NSE Market Closed ({now_ist.strftime('%I:%M %p IST')}). Opens tomorrow at 09:15 AM IST."
        }
