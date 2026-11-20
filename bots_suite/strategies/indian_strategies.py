"""
Indian Market (NIFTY 50) Strategies Suite
Based on quantified research rules from nifty_crypto_forex.html:
1. Turn-of-the-Month (TOTM) Anomaly (Daily/Monthly)
2. 4-Day / 7-Day Dual RSI Momentum (Daily)
3. Previous Day High/Low (PDH/PDL) Break & Retest (Intraday 5m/15m)
"""

from datetime import datetime, time as dtime, timedelta, timezone
import numpy as np
import pandas as pd
import yfinance as yf

from strategies.common import clean_ohlcv, to_float

IST = timezone(timedelta(hours=5, minutes=30))


class NiftyTurnOfTheMonthStrategy:
    """
    Strategy 01: NIFTY 50 Turn-of-the-Month (TOTM) Anomaly
    Entry: Buy on the 5th or 6th last trading day of the month at closing (3:15-3:25 PM IST).
    Exit: Sell on the 2nd trading day of the new month at closing.
    """
    def __init__(self, symbol="^NSEI"):
        self.symbol = symbol

    def _get_month_trading_days(self, year, month):
        days = []
        cur = datetime(year, month, 1)
        while cur.month == month:
            if cur.weekday() < 5:  # Mon-Fri
                days.append(cur.date())
            cur += timedelta(days=1)
        return days

    def evaluate(self):
        now_ist = datetime.now(IST)
        today = now_ist.date()
        year = today.year
        month = today.month

        current_trading_days = self._get_month_trading_days(year, month)
        total_trading_days = len(current_trading_days)

        entry_window_start = total_trading_days - 6
        entry_window_end = total_trading_days - 5
        entry_days = current_trading_days[entry_window_start:entry_window_end + 1] if entry_window_start >= 0 else []
        exit_day = current_trading_days[1] if len(current_trading_days) >= 2 else None

        df = clean_ohlcv(yf.download(self.symbol, period="5d", interval="1d", progress=False))
        current_price = to_float(df['close'].iloc[-1]) if not df.empty else 0.0

        if today in entry_days:
            return {
                "strategy": "NIFTY_TOTM_ANOMALY",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 85.0,
                "current_price": round(current_price, 2),
                "reason": f"TOTM Entry Window active ({today} is within last 5-6 trading days of month)",
                "suggested_sl": round(current_price * 0.98, 2),
                "suggested_tp": round(current_price * 1.03, 2)
            }
        elif today == exit_day:
            return {
                "strategy": "NIFTY_TOTM_ANOMALY",
                "symbol": self.symbol,
                "action": "SELL / EXIT",
                "confidence": 90.0,
                "current_price": round(current_price, 2),
                "reason": f"TOTM Exit day reached (2nd trading day of month {today})",
                "suggested_sl": 0,
                "suggested_tp": 0
            }
        else:
            return {
                "strategy": "NIFTY_TOTM_ANOMALY",
                "symbol": self.symbol,
                "action": "HOLD / INACTIVE",
                "confidence": 50.0,
                "current_price": round(current_price, 2),
                "reason": f"Outside TOTM window. Next entry window around month-end (trading days {total_trading_days-5} to {total_trading_days}).",
                "suggested_sl": 0,
                "suggested_tp": 0
            }


class NiftyDualRsiStrategy:
    """
    Strategy 02: NIFTY 50 4-Day / 7-Day RSI System
    Rules:
    - Compute RSI(4) and RSI(7) on Daily candles.
    - Entry: When RSI(4) crosses above 80 from below (Prev <= 80, Today > 80), Buy at open.
    - Exit: When RSI(7) closes > 70, Sell/Exit at next open.
    - Time Stop: Exit if in trade for 47 trading days.
    """
    def __init__(self, symbol="^NSEI"):
        self.symbol = symbol

    def _calc_rsi(self, series, period):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss.replace(0, np.nan))
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    def evaluate(self):
        df = clean_ohlcv(yf.download(self.symbol, period="6mo", interval="1d", progress=False))
        if df.empty or len(df) < 20:
            return {"strategy": "NIFTY_DUAL_RSI", "symbol": self.symbol, "action": "NO_DATA", "confidence": 0}

        df['rsi_4'] = self._calc_rsi(df['close'], 4)
        df['rsi_7'] = self._calc_rsi(df['close'], 7)

        curr_close = to_float(df['close'].iloc[-1])
        curr_rsi4 = to_float(df['rsi_4'].iloc[-1])
        prev_rsi4 = to_float(df['rsi_4'].iloc[-2])
        curr_rsi7 = to_float(df['rsi_7'].iloc[-1])

        # Cross above 80 rule
        if prev_rsi4 <= 80.0 and curr_rsi4 > 80.0:
            return {
                "strategy": "NIFTY_DUAL_RSI",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 80.0,
                "current_price": round(curr_close, 2),
                "rsi_4": round(curr_rsi4, 2),
                "rsi_7": round(curr_rsi7, 2),
                "reason": f"RSI(4) crossed above 80 (Prev: {prev_rsi4:.1f} -> Curr: {curr_rsi4:.1f}). Strong momentum breakout.",
                "suggested_sl": round(curr_close * 0.97, 2),
                "suggested_tp": round(curr_close * 1.05, 2)
            }
        elif curr_rsi7 > 70.0:
            return {
                "strategy": "NIFTY_DUAL_RSI",
                "symbol": self.symbol,
                "action": "SELL / TAKE_PROFIT",
                "confidence": 85.0,
                "current_price": round(curr_close, 2),
                "rsi_4": round(curr_rsi4, 2),
                "rsi_7": round(curr_rsi7, 2),
                "reason": f"RSI(7) closed above 70 ({curr_rsi7:.1f}). Target reached, exit position.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }
        else:
            return {
                "strategy": "NIFTY_DUAL_RSI",
                "symbol": self.symbol,
                "action": "HOLD / NEUTRAL",
                "confidence": 45.0,
                "current_price": round(curr_close, 2),
                "rsi_4": round(curr_rsi4, 2),
                "rsi_7": round(curr_rsi7, 2),
                "reason": f"RSI(4)={curr_rsi4:.1f}, RSI(7)={curr_rsi7:.1f}. Waiting for RSI(4) cross above 80.",
                "suggested_sl": round(curr_close * 0.97, 2),
                "suggested_tp": round(curr_close * 1.05, 2)
            }


class NiftyPdhPdlBreakRetestStrategy:
    """
    Strategy 03: NIFTY Previous Day High/Low (PDH/PDL) Break & Retest
    Rules:
    - Mark Previous Day High (PDH) and Low (PDL).
    - On 15m intraday candle, check if price broke PDH/PDL and retests it.
    - Retest rejection confirmation -> 1:2 RR trade.
    """
    def __init__(self, symbol="^NSEI"):
        self.symbol = symbol

    def evaluate(self):
        daily_df = clean_ohlcv(yf.download(self.symbol, period="5d", interval="1d", progress=False))
        intra_df = clean_ohlcv(yf.download(self.symbol, period="2d", interval="15m", progress=False))

        if daily_df.empty or intra_df.empty or len(daily_df) < 2:
            return {"strategy": "NIFTY_PDH_PDL_RETEST", "symbol": self.symbol, "action": "NO_DATA", "confidence": 0}

        prev_day = daily_df.iloc[-2]
        pdh = to_float(prev_day['high'])
        pdl = to_float(prev_day['low'])

        curr_candle = intra_df.iloc[-1]
        curr_price = to_float(curr_candle['close'])
        curr_low = to_float(curr_candle['low'])
        curr_high = to_float(curr_candle['high'])

        # Bullish Break & Retest of PDH
        if abs(curr_low - pdh) / pdh <= 0.003 and curr_price > pdh:
            risk = max(curr_price - curr_low, curr_price * 0.004)
            return {
                "strategy": "NIFTY_PDH_PDL_RETEST",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 78.0,
                "current_price": round(curr_price, 2),
                "pdh": round(pdh, 2),
                "pdl": round(pdl, 2),
                "reason": f"Bullish Retest of Previous Day High ({pdh:.2f}). Support confirmed.",
                "suggested_sl": round(curr_price - risk, 2),
                "suggested_tp": round(curr_price + (2 * risk), 2)
            }
        # Bearish Break & Retest of PDL
        elif abs(curr_high - pdl) / pdl <= 0.003 and curr_price < pdl:
            risk = max(curr_high - curr_price, curr_price * 0.004)
            return {
                "strategy": "NIFTY_PDH_PDL_RETEST",
                "symbol": self.symbol,
                "action": "SELL",
                "confidence": 78.0,
                "current_price": round(curr_price, 2),
                "pdh": round(pdh, 2),
                "pdl": round(pdl, 2),
                "reason": f"Bearish Retest of Previous Day Low ({pdl:.2f}). Resistance confirmed.",
                "suggested_sl": round(curr_price + risk, 2),
                "suggested_tp": round(curr_price - (2 * risk), 2)
            }
        else:
            return {
                "strategy": "NIFTY_PDH_PDL_RETEST",
                "symbol": self.symbol,
                "action": "HOLD / RANGE",
                "confidence": 40.0,
                "current_price": round(curr_price, 2),
                "pdh": round(pdh, 2),
                "pdl": round(pdl, 2),
                "reason": f"Price inside or far from PDH ({pdh:.2f}) / PDL ({pdl:.2f}) levels. No retest setup.",
                "suggested_sl": round(pdl, 2),
                "suggested_tp": round(pdh, 2)
            }
