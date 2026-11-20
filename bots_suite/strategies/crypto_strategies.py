"""
Cryptocurrency (Bitcoin / Ethereum) Strategies Suite
Based on quantified research rules from nifty_crypto_forex.html:
1. BTC 100 / 250 SMA Crossover Trend Following (Daily)
2. Bitcoin Donchian Channel & 200-EMA Price Momentum (Daily/Hourly)
3. BTC Peak-Hour Intraday Seasonality (21:00-23:00 UTC / 02:30-04:30 AM IST)
"""

from datetime import datetime, time as dtime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

from strategies.common import clean_ohlcv, to_float


class CryptoSmaTrendFollowingStrategy:
    """
    Strategy 04: BTC 100 / 250 SMA Trend Following
    Rules:
    - 100 SMA and 250 SMA on Daily BTC-USD / ETH-USD.
    - Long entry when 100 SMA crosses above 250 SMA (Golden Cross).
    - Exit completely to cash/stablecoins when 100 SMA crosses below 250 SMA.
    """
    def __init__(self, symbol="BTC-USD"):
        self.symbol = symbol

    def evaluate(self):
        df = clean_ohlcv(yf.download(self.symbol, period="2y", interval="1d", progress=False))
        if df.empty or len(df) < 260:
            return {"strategy": "CRYPTO_SMA_TREND", "symbol": self.symbol, "action": "NO_DATA", "confidence": 0}

        df['sma_100'] = df['close'].rolling(window=100).mean()
        df['sma_250'] = df['close'].rolling(window=250).mean()

        curr_close = to_float(df['close'].iloc[-1])
        curr_100 = to_float(df['sma_100'].iloc[-1])
        curr_250 = to_float(df['sma_250'].iloc[-1])
        prev_100 = to_float(df['sma_100'].iloc[-2])
        prev_250 = to_float(df['sma_250'].iloc[-2])

        is_golden_cross = (curr_100 > curr_250) and (prev_100 <= prev_250)
        is_bullish_regime = curr_100 > curr_250
        is_death_cross = (curr_100 < curr_250) and (prev_100 >= prev_250)

        if is_golden_cross:
            return {
                "strategy": "CRYPTO_SMA_TREND",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 90.0,
                "current_price": round(curr_close, 2),
                "sma_100": round(curr_100, 2),
                "sma_250": round(curr_250, 2),
                "reason": f"Fresh Golden Cross: 100 SMA ({curr_100:.0f}) crossed above 250 SMA ({curr_250:.0f}). Bull market confirmed.",
                "suggested_sl": round(curr_250, 2),
                "suggested_tp": round(curr_close * 1.5, 2)
            }
        elif is_death_cross:
            return {
                "strategy": "CRYPTO_SMA_TREND",
                "symbol": self.symbol,
                "action": "SELL / EXIT_TO_CASH",
                "confidence": 95.0,
                "current_price": round(curr_close, 2),
                "sma_100": round(curr_100, 2),
                "sma_250": round(curr_250, 2),
                "reason": f"Fresh Death Cross: 100 SMA ({curr_100:.0f}) crossed below 250 SMA ({curr_250:.0f}). Bear market risk, move to cash.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }
        elif is_bullish_regime:
            return {
                "strategy": "CRYPTO_SMA_TREND",
                "symbol": self.symbol,
                "action": "HOLD_LONG",
                "confidence": 75.0,
                "current_price": round(curr_close, 2),
                "sma_100": round(curr_100, 2),
                "sma_250": round(curr_250, 2),
                "reason": f"Bullish Trend Active: 100 SMA ({curr_100:.0f}) > 250 SMA ({curr_250:.0f}). Ride the major trend.",
                "suggested_sl": round(curr_250, 2),
                "suggested_tp": round(curr_close * 1.25, 2)
            }
        else:
            return {
                "strategy": "CRYPTO_SMA_TREND",
                "symbol": self.symbol,
                "action": "CASH_PRESERVATION",
                "confidence": 70.0,
                "current_price": round(curr_close, 2),
                "sma_100": round(curr_100, 2),
                "sma_250": round(curr_250, 2),
                "reason": f"Bearish Trend: 100 SMA ({curr_100:.0f}) < 250 SMA ({curr_250:.0f}). Capital stays in cash/stablecoin.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }


class CryptoDonchianMomentumStrategy:
    """
    Strategy 05: Bitcoin Donchian Channel & 200-EMA Momentum
    Rules:
    - Filter: Price > 200 EMA (Long-term uptrend).
    - Entry: Daily candle closes above the 20-candle high.
    - Stop-loss: 2 x ATR(14) below entry.
    - Exit: When price breaks below the 20-candle low.
    """
    def __init__(self, symbol="BTC-USD"):
        self.symbol = symbol

    def evaluate(self):
        df = clean_ohlcv(yf.download(self.symbol, period="1y", interval="1d", progress=False))
        if df.empty or len(df) < 210:
            return {"strategy": "CRYPTO_DONCHIAN_MOMENTUM", "symbol": self.symbol, "action": "NO_DATA", "confidence": 0}

        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['donchian_high_20'] = df['high'].shift(1).rolling(window=20).max()
        df['donchian_low_20'] = df['low'].shift(1).rolling(window=20).min()

        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14).mean()

        curr_close = to_float(df['close'].iloc[-1])
        curr_ema200 = to_float(df['ema_200'].iloc[-1])
        don_high = to_float(df['donchian_high_20'].iloc[-1])
        don_low = to_float(df['donchian_low_20'].iloc[-1])
        atr = to_float(df['atr_14'].iloc[-1])

        # Long Entry: Above 200 EMA + breakout above 20-day high
        if curr_close > curr_ema200 and curr_close > don_high:
            sl = curr_close - (2.0 * atr)
            tp = curr_close + (4.0 * atr)
            return {
                "strategy": "CRYPTO_DONCHIAN_MOMENTUM",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 85.0,
                "current_price": round(curr_close, 2),
                "ema_200": round(curr_ema200, 2),
                "donchian_high": round(don_high, 2),
                "donchian_low": round(don_low, 2),
                "reason": f"Donchian 20-Day High Breakout ({curr_close:.0f} > {don_high:.0f}) above 200-EMA ({curr_ema200:.0f}). Strong trend expansion.",
                "suggested_sl": round(sl, 2),
                "suggested_tp": round(tp, 2)
            }
        elif curr_close < don_low:
            return {
                "strategy": "CRYPTO_DONCHIAN_MOMENTUM",
                "symbol": self.symbol,
                "action": "SELL / TRAIL_EXIT",
                "confidence": 85.0,
                "current_price": round(curr_close, 2),
                "ema_200": round(curr_ema200, 2),
                "donchian_high": round(don_high, 2),
                "donchian_low": round(don_low, 2),
                "reason": f"Price broke 20-Day Donchian Low ({curr_close:.0f} < {don_low:.0f}). Momentum exhausted, exit position.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }
        else:
            return {
                "strategy": "CRYPTO_DONCHIAN_MOMENTUM",
                "symbol": self.symbol,
                "action": "HOLD / CONSOLIDATION",
                "confidence": 50.0,
                "current_price": round(curr_close, 2),
                "ema_200": round(curr_ema200, 2),
                "donchian_high": round(don_high, 2),
                "donchian_low": round(don_low, 2),
                "reason": f"Price between Donchian High ({don_high:.0f}) and Low ({don_low:.0f}). Awaiting next range breakout.",
                "suggested_sl": round(curr_close - (2.0 * atr), 2),
                "suggested_tp": round(don_high, 2)
            }


class CryptoPeakHourSeasonalityStrategy:
    """
    Strategy 06: BTC Peak-Hour Intraday Seasonality
    Rules:
    - Filter: Price > Daily 200-SMA.
    - Optimal Window: 21:00 UTC to 23:00 UTC (02:30 AM to 04:30 AM IST).
    - Mondays & Thursdays show statistically highest positive expectation.
    - Hold for 2 hours and exit at window close.
    """
    def __init__(self, symbol="BTC-USD"):
        self.symbol = symbol

    def evaluate(self):
        df_daily = clean_ohlcv(yf.download(self.symbol, period="1y", interval="1d", progress=False))
        if df_daily.empty or len(df_daily) < 205:
            return {"strategy": "CRYPTO_PEAK_SEASONALITY", "symbol": self.symbol, "action": "NO_DATA", "confidence": 0}

        df_daily['sma_200'] = df_daily['close'].rolling(window=200).mean()
        curr_close = to_float(df_daily['close'].iloc[-1])
        sma_200 = to_float(df_daily['sma_200'].iloc[-1])
        is_above_200sma = curr_close > sma_200

        now_utc = datetime.now(timezone.utc)
        cur_hour = now_utc.hour
        cur_weekday = now_utc.weekday()

        is_peak_window = (cur_hour >= 21 and cur_hour < 23)
        is_prime_day = cur_weekday in [0, 3]

        if is_peak_window and is_above_200sma:
            return {
                "strategy": "CRYPTO_PEAK_SEASONALITY",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 80.0 if is_prime_day else 70.0,
                "current_price": round(curr_close, 2),
                "reason": f"Active Peak Seasonality Window ({cur_hour}:00 UTC) with Price > 200 SMA ({sma_200:.0f}). Prime day bonus: {is_prime_day}.",
                "suggested_sl": round(curr_close * 0.985, 2),
                "suggested_tp": round(curr_close * 1.025, 2)
            }
        elif not is_above_200sma:
            return {
                "strategy": "CRYPTO_PEAK_SEASONALITY",
                "symbol": self.symbol,
                "action": "AVOID_BEAR",
                "confidence": 30.0,
                "current_price": round(curr_close, 2),
                "reason": f"Price below 200 SMA ({sma_200:.0f}). Macro filter blocks seasonality longs.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }
        else:
            return {
                "strategy": "CRYPTO_PEAK_SEASONALITY",
                "symbol": self.symbol,
                "action": "STANDBY_WINDOW",
                "confidence": 50.0,
                "current_price": round(curr_close, 2),
                "reason": f"Outside 21:00-23:00 UTC window (Current UTC: {cur_hour}:00). Standby for nocturnal liquidity surge.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }
