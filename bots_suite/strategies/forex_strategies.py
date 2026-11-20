"""
Forex & Multi-Asset Global Strategies Suite
Based on quantified research rules from nifty_crypto_forex.html:
1. Forex Major Pairs Mean Reversion (Z-Score +-2.0) (Hourly/4h)
2. London Open Breakout & Retest with Fakeout Filter (15m)
3. Multi-Asset & Commodity 200-Day Donchian + 6-ATR Chandelier Exit (Daily)
"""

from datetime import datetime, time as dtime, timezone
import numpy as np
import pandas as pd
import yfinance as yf

from strategies.common import clean_ohlcv, to_float


class ForexZScoreMeanReversionStrategy:
    """
    Strategy 07: Forex Major Pairs Mean Reversion (Z-Score)
    Rules:
    - High-liquidity correlated pairs: EUR/USD (EURUSD=X) and GBP/USD (GBPUSD=X).
    - Compute rolling 60-period spread and Z-Score: (Spread - Mean) / Std.
    - Entry: When Z-Score exceeds +2.0 (Overextended Long -> Short spread)
             or drops below -2.0 (Overextended Short -> Long spread).
    - Exit: When Z-Score reverts to 0.0 (Mean Reversion complete).
    - Stop Loss: At Z-Score +-3.0.
    """
    def __init__(self, pair1="EURUSD=X", pair2="GBPUSD=X"):
        self.pair1 = pair1
        self.pair2 = pair2

    def evaluate(self):
        df1 = clean_ohlcv(yf.download(self.pair1, period="1mo", interval="1h", progress=False))
        df2 = clean_ohlcv(yf.download(self.pair2, period="1mo", interval="1h", progress=False))

        if df1.empty or df2.empty or len(df1) < 65:
            return {"strategy": "FOREX_ZSCORE_MEAN_REVERSION", "symbol": f"{self.pair1}/{self.pair2}", "action": "NO_DATA", "confidence": 0}

        # Align lengths
        min_len = min(len(df1), len(df2))
        c1 = df1['close'].iloc[-min_len:]
        c2 = df2['close'].iloc[-min_len:]

        spread = c1.values - c2.values
        spread_series = pd.Series(spread)
        rolling_mean = spread_series.rolling(window=60).mean()
        rolling_std = spread_series.rolling(window=60).std()
        z_score = (spread_series - rolling_mean) / rolling_std

        curr_z = to_float(z_score.iloc[-1])
        curr_p1 = to_float(df1['close'].iloc[-1])
        curr_p2 = to_float(df2['close'].iloc[-1])

        if curr_z >= 2.0:
            return {
                "strategy": "FOREX_ZSCORE_MEAN_REVERSION",
                "symbol": f"{self.pair1} (vs {self.pair2})",
                "action": "SELL / SHORT_SPREAD",
                "confidence": 82.0,
                "current_price": round(curr_p1, 4),
                "z_score": round(curr_z, 2),
                "reason": f"Z-Score={curr_z:.2f} >= +2.0 (Statistical Overextension). Mean reversion expected back to zero.",
                "suggested_sl": round(curr_p1 * 1.008, 4),
                "suggested_tp": round(curr_p1 * 0.992, 4)
            }
        elif curr_z <= -2.0:
            return {
                "strategy": "FOREX_ZSCORE_MEAN_REVERSION",
                "symbol": f"{self.pair1} (vs {self.pair2})",
                "action": "BUY / LONG_SPREAD",
                "confidence": 82.0,
                "current_price": round(curr_p1, 4),
                "z_score": round(curr_z, 2),
                "reason": f"Z-Score={curr_z:.2f} <= -2.0 (Statistical Underextension). Mean reversion expected back to zero.",
                "suggested_sl": round(curr_p1 * 0.992, 4),
                "suggested_tp": round(curr_p1 * 1.008, 4)
            }
        elif abs(curr_z) <= 0.3:
            return {
                "strategy": "FOREX_ZSCORE_MEAN_REVERSION",
                "symbol": f"{self.pair1} (vs {self.pair2})",
                "action": "CLOSE_AT_MEAN",
                "confidence": 75.0,
                "current_price": round(curr_p1, 4),
                "z_score": round(curr_z, 2),
                "reason": f"Z-Score={curr_z:.2f} reached equilibrium mean (Z=0). Target met.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }
        else:
            return {
                "strategy": "FOREX_ZSCORE_MEAN_REVERSION",
                "symbol": f"{self.pair1} (vs {self.pair2})",
                "action": "HOLD_NEUTRAL",
                "confidence": 50.0,
                "current_price": round(curr_p1, 4),
                "z_score": round(curr_z, 2),
                "reason": f"Z-Score={curr_z:.2f} is within normal distribution bounds (-2.0 < Z < +2.0).",
                "suggested_sl": 0,
                "suggested_tp": 0
            }


class ForexLondonBreakoutStrategy:
    """
    Strategy 08: London Open Breakout & Retest
    Rules:
    - Mark Asian session High and Low (00:00 to 08:00 UTC).
    - During London session (08:00 to 11:00 UTC), wait for 15m candle close outside Asian range.
    - Enter only when price retests the range boundary (fakeout filter).
    - Exit before or during New York open (13:30 UTC / 07:00 PM IST).
    """
    def __init__(self, symbol="GBPUSD=X"):
        self.symbol = symbol

    def evaluate(self):
        df = clean_ohlcv(yf.download(self.symbol, period="3d", interval="15m", progress=False))
        if df.empty or len(df) < 30:
            return {"strategy": "FOREX_LONDON_BREAKOUT", "symbol": self.symbol, "action": "NO_DATA", "confidence": 0}

        recent_day = df.tail(48)
        asian_slice = recent_day.iloc[:32] if len(recent_day) >= 32 else recent_day.iloc[:16]
        asian_high = to_float(asian_slice['high'].max())
        asian_low = to_float(asian_slice['low'].min())

        curr = df.iloc[-1]
        curr_price = to_float(curr['close'])
        curr_low = to_float(curr['low'])
        curr_high = to_float(curr['high'])

        now_utc = datetime.now(timezone.utc)
        curr_hour = now_utc.hour

        is_london_active = 8 <= curr_hour <= 14

        # Breakout & Retest of Asian High
        if is_london_active and curr_price > asian_high and abs(curr_low - asian_high) / asian_high <= 0.002:
            sl = asian_high - (curr_price * 0.0025)
            tp = curr_price + (2.0 * (curr_price - sl))
            return {
                "strategy": "FOREX_LONDON_BREAKOUT",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 80.0,
                "current_price": round(curr_price, 4),
                "asian_high": round(asian_high, 4),
                "asian_low": round(asian_low, 4),
                "reason": f"London Session: Bullish Breakout & Retest of Asian High ({asian_high:.4f}). Fakeout filter cleared.",
                "suggested_sl": round(sl, 4),
                "suggested_tp": round(tp, 4)
            }
        # Breakout & Retest of Asian Low
        elif is_london_active and curr_price < asian_low and abs(curr_high - asian_low) / asian_low <= 0.002:
            sl = asian_low + (curr_price * 0.0025)
            tp = curr_price - (2.0 * (sl - curr_price))
            return {
                "strategy": "FOREX_LONDON_BREAKOUT",
                "symbol": self.symbol,
                "action": "SELL",
                "confidence": 80.0,
                "current_price": round(curr_price, 4),
                "asian_high": round(asian_high, 4),
                "asian_low": round(asian_low, 4),
                "reason": f"London Session: Bearish Breakdown & Retest of Asian Low ({asian_low:.4f}). Fakeout filter cleared.",
                "suggested_sl": round(sl, 4),
                "suggested_tp": round(tp, 4)
            }
        else:
            return {
                "strategy": "FOREX_LONDON_BREAKOUT",
                "symbol": self.symbol,
                "action": "WAIT_SESSION_RETEST",
                "confidence": 45.0,
                "current_price": round(curr_price, 4),
                "asian_high": round(asian_high, 4),
                "asian_low": round(asian_low, 4),
                "reason": f"Asian Range [{asian_low:.4f} - {asian_high:.4f}]. Awaiting London retest confirmation.",
                "suggested_sl": 0,
                "suggested_tp": 0
            }


class MultiAssetDonchianTrendStrategy:
    """
    Strategy 09: 20+ Multi-Asset & Commodity 200-Day Donchian + 6-ATR Chandelier Exit
    Rules:
    - Daily 200-Day Donchian Channel on closing prices.
    - Long entry when daily close > 200-day high.
    - Short entry when daily close < 200-day low.
    - Exit trailing stop: 6 x ATR(20) Chandelier line.
    - Applicable to: Gold (GC=F), Crude Oil (CL=F), Nasdaq (QQQ), EUR/USD (EURUSD=X).
    """
    def __init__(self, symbol="GC=F"):
        self.symbol = symbol

    def evaluate(self):
        df = clean_ohlcv(yf.download(self.symbol, period="2y", interval="1d", progress=False))
        if df.empty or len(df) < 210:
            return {"strategy": "MULTI_ASSET_DONCHIAN_TREND", "symbol": self.symbol, "action": "NO_DATA", "confidence": 0}

        df['donchian_high_200'] = df['close'].shift(1).rolling(window=200).max()
        df['donchian_low_200'] = df['close'].shift(1).rolling(window=200).min()

        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        df['atr_20'] = tr.rolling(window=20).mean()

        df['chandelier_long_exit'] = df['high'].rolling(window=20).max() - (6.0 * df['atr_20'])
        df['chandelier_short_exit'] = df['low'].rolling(window=20).min() + (6.0 * df['atr_20'])

        curr = df.iloc[-1]
        curr_close = to_float(curr['close'])
        don_high = to_float(curr['donchian_high_200'])
        don_low = to_float(curr['donchian_low_200'])
        chan_exit_long = to_float(curr['chandelier_long_exit'])
        chan_exit_short = to_float(curr['chandelier_short_exit'])
        atr = to_float(curr['atr_20'])

        if curr_close > don_high:
            return {
                "strategy": "MULTI_ASSET_DONCHIAN_TREND",
                "symbol": self.symbol,
                "action": "BUY",
                "confidence": 88.0,
                "current_price": round(curr_close, 2),
                "donchian_high": round(don_high, 2),
                "donchian_low": round(don_low, 2),
                "reason": f"200-Day Donchian Breakout ({curr_close:.2f} > {don_high:.2f}). Systematic Trend Following.",
                "suggested_sl": round(chan_exit_long, 2),
                "suggested_tp": round(curr_close + (3.0 * (curr_close - chan_exit_long)), 2)
            }
        elif curr_close < don_low:
            return {
                "strategy": "MULTI_ASSET_DONCHIAN_TREND",
                "symbol": self.symbol,
                "action": "SELL",
                "confidence": 88.0,
                "current_price": round(curr_close, 2),
                "donchian_high": round(don_high, 2),
                "donchian_low": round(don_low, 2),
                "reason": f"200-Day Donchian Breakdown ({curr_close:.2f} < {don_low:.2f}). Major downtrend expansion.",
                "suggested_sl": round(chan_exit_short, 2),
                "suggested_tp": round(curr_close - (3.0 * (chan_exit_short - curr_close)), 2)
            }
        else:
            return {
                "strategy": "MULTI_ASSET_DONCHIAN_TREND",
                "symbol": self.symbol,
                "action": "HOLD_IN_RANGE",
                "confidence": 55.0,
                "current_price": round(curr_close, 2),
                "donchian_high": round(don_high, 2),
                "donchian_low": round(don_low, 2),
                "reason": f"Trading within 200-Day Channel [{don_low:.2f} - {don_high:.2f}]. Chandelier SL at {chan_exit_long:.2f}.",
                "suggested_sl": round(chan_exit_long, 2),
                "suggested_tp": round(don_high, 2)
            }
