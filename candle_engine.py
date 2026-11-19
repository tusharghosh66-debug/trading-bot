"""
Antigravity Alpha Trader - Professional Candlestick & Price Action Engine
Analyzes multi-timeframe candles, detects patterns (Engulfing, Hammer, Star, Pinbars),
computes technical confluence (EMA, RSI, MACD, ATR, Support/Resistance),
and generates high-probability institutional trading signals.
"""

import logging
import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    DATA_PERIOD,
    EXECUTION_TIMEFRAME,
    MACRO_TIMEFRAME,
    MIN_RISK_REWARD_RATIO,
    MIN_SIGNAL_CONFIDENCE,
)

logger = logging.getLogger("AlphaTrader.CandleEngine")


class CandleEngine:
    def __init__(self):
        pass

    def fetch_ohlcv(self, symbol, interval=EXECUTION_TIMEFRAME, period=DATA_PERIOD):
        """Fetches OHLCV candlestick data cleanly handling yfinance format variations."""
        try:
            df = yf.download(symbol, period=period, interval=interval, progress=False)
            if df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for {symbol} on {interval}")
                return None

            # Handle multi-level columns if present (e.g. ('Close', 'SPY'))
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0].lower() for col in df.columns]
            else:
                df.columns = [col.lower() for col in df.columns]

            # Ensure numeric types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            df = df.dropna().copy()
            return df
        except Exception as e:
            logger.error(f"Error fetching candles for {symbol}: {e}")
            return None

    def compute_indicators(self, df):
        """Calculates professional technical indicators."""
        df = df.copy()
        close = df['close']
        high = df['high']
        low = df['low']

        # Exponential Moving Averages
        df['ema_9'] = close.ewm(span=9, adjust=False).mean()
        df['ema_21'] = close.ewm(span=21, adjust=False).mean()
        df['ema_50'] = close.ewm(span=50, adjust=False).mean()
        df['ema_200'] = close.ewm(span=200, adjust=False).mean()

        # Relative Strength Index (RSI 14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss.replace(0, np.nan))
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi'] = df['rsi'].fillna(50)

        # MACD (12, 26, 9)
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Average True Range (ATR 14) for dynamic volatility stop loss
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean().bfill()

        # Bollinger Bands (20, 2)
        df['bb_mid'] = close.rolling(window=20).mean()
        bb_std = close.rolling(window=20).std()
        df['bb_upper'] = df['bb_mid'] + (bb_std * 2)
        df['bb_lower'] = df['bb_mid'] - (bb_std * 2)

        # Volume Moving Average
        df['vol_ma'] = df['volume'].rolling(window=20).mean()

        # Swing Highs and Lows (Support & Resistance)
        df['swing_high'] = high.rolling(window=10).max()
        df['swing_low'] = low.rolling(window=10).min()

        return df

    def detect_candlestick_patterns(self, df):
        """
        Detects high-probability candlestick patterns on the latest candles.
        Returns: pattern_name, pattern_type ('BULLISH', 'BEARISH', or 'NEUTRAL'), pattern_score (0-25)
        """
        if len(df) < 5:
            return "No Pattern", "NEUTRAL", 0

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        c_open, c_high, c_low, c_close = curr['open'], curr['high'], curr['low'], curr['close']
        p_open, p_high, p_low, p_close = prev['open'], prev['high'], prev['low'], prev['close']
        p2_open, p2_high, p2_low, p2_close = prev2['open'], prev2['high'], prev2['low'], prev2['close']

        curr_body = abs(c_close - c_open)
        prev_body = abs(p_close - p_open)
        curr_range = c_high - c_low
        atr = curr['atr'] if 'atr' in curr and not np.isnan(curr['atr']) else max(curr_range, 0.01)

        is_green = c_close > c_open
        is_red = c_close < c_open
        prev_is_red = p_close < p_open
        prev_is_green = p_close > p_open

        upper_wick = c_high - max(c_open, c_close)
        lower_wick = min(c_open, c_close) - c_low

        # 1. Bullish Engulfing
        # Previous red candle, current green candle opens at or below prev close and closes above prev open
        if prev_is_red and is_green and (c_close > p_open) and (c_open <= p_close) and (curr_body > prev_body * 1.1):
            return "Bullish Engulfing", "BULLISH", 25

        # 2. Bearish Engulfing
        # Previous green candle, current red candle opens at or above prev close and closes below prev open
        if prev_is_green and is_red and (c_close < p_open) and (c_open >= p_close) and (curr_body > prev_body * 1.1):
            return "Bearish Engulfing", "BEARISH", 25

        # 3. Hammer / Bullish Pinbar
        # Small body at top of candle, long lower shadow (>= 2x body), little or no upper shadow
        if lower_wick >= (2.0 * curr_body) and upper_wick <= (0.35 * curr_body) and curr_body > (0.1 * atr):
            return "Hammer / Rejection Pinbar", "BULLISH", 22

        # 4. Shooting Star / Bearish Pinbar
        # Small body at bottom of candle, long upper shadow (>= 2x body), little or no lower shadow
        if upper_wick >= (2.0 * curr_body) and lower_wick <= (0.35 * curr_body) and curr_body > (0.1 * atr):
            return "Shooting Star / Bearish Rejection", "BEARISH", 22

        # 5. Morning Star (3-candle bullish reversal)
        if (p2_close < p2_open) and (prev_body < curr_range * 0.4) and is_green and (c_close > (p2_open + p2_close) / 2):
            return "Morning Star Reversal", "BULLISH", 24

        # 6. Evening Star (3-candle bearish reversal)
        if (p2_close > p2_open) and (prev_body < curr_range * 0.4) and is_red and (c_close < (p2_open + p2_close) / 2):
            return "Evening Star Reversal", "BEARISH", 24

        # 7. Strong Marubozu / Momentum Bar
        if curr_body >= (0.85 * curr_range) and curr_body >= (1.2 * atr):
            if is_green:
                return "Bullish Momentum Marubozu", "BULLISH", 20
            else:
                return "Bearish Momentum Marubozu", "BEARISH", 20

        # 8. Doji (Indecision)
        if curr_body <= (0.15 * curr_range) and curr_range > 0:
            return "Doji (Market Indecision)", "NEUTRAL", 10

        return "Standard Price Action Candle", "NEUTRAL", 5

    def analyze_symbol(self, symbol, sentiment_bias="NEUTRAL", macro_regime="NEUTRAL"):
        """
        Runs complete professional multi-factor analysis on a symbol.
        Combines: Candlestick Pattern + Trend + RSI + MACD + Volume + Macro Sentiment.
        Outputs signal, entry, stop loss, take profit targets, and confluence score.
        """
        df = self.fetch_ohlcv(symbol, interval=EXECUTION_TIMEFRAME)
        if df is None or len(df) < 30:
            return None

        df = self.compute_indicators(df)
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        current_price = float(curr['close'])
        atr = float(curr['atr']) if not np.isnan(curr['atr']) else current_price * 0.015
        if atr <= 0:
            atr = current_price * 0.015

        pattern_name, pattern_type, pattern_score = self.detect_candlestick_patterns(df)

        bullish_points = 0
        bearish_points = 0
        reasons = []

        # Factor 1: Candlestick Pattern (Max 25 pts)
        if pattern_type == "BULLISH":
            bullish_points += pattern_score
            reasons.append(f"Candlestick: {pattern_name} detected (+{pattern_score}pts)")
        elif pattern_type == "BEARISH":
            bearish_points += pattern_score
            reasons.append(f"Candlestick: {pattern_name} detected (+{pattern_score}pts)")

        # Factor 2: Trend Alignment (EMA 21, 50, 200) (Max 20 pts)
        ema_21 = float(curr['ema_21'])
        ema_50 = float(curr['ema_50'])
        ema_200 = float(curr['ema_200'])

        if current_price > ema_21 > ema_50:
            bullish_points += 20
            reasons.append("Trend: Price above EMA 21 & EMA 50 (Golden Trend) (+20pts)")
        elif current_price < ema_21 < ema_50:
            bearish_points += 20
            reasons.append("Trend: Price below EMA 21 & EMA 50 (Death Trend) (+20pts)")
        else:
            reasons.append("Trend: Consolidation / Rangebound between EMAs")

        # Factor 3: RSI Momentum & Mean Reversion (Max 15 pts)
        rsi = float(curr['rsi'])
        prev_rsi = float(prev['rsi'])
        if rsi < 35 and rsi > prev_rsi:
            bullish_points += 15
            reasons.append(f"RSI: Rebounding from Oversold zone ({rsi:.1f}) (+15pts)")
        elif rsi > 65 and rsi < prev_rsi:
            bearish_points += 15
            reasons.append(f"RSI: Turning down from Overbought zone ({rsi:.1f}) (+15pts)")
        elif 50 < rsi < 65 and rsi > prev_rsi:
            bullish_points += 10
            reasons.append(f"RSI: Bullish momentum expansion ({rsi:.1f}) (+10pts)")
        elif 35 < rsi < 50 and rsi < prev_rsi:
            bearish_points += 10
            reasons.append(f"RSI: Bearish momentum expansion ({rsi:.1f}) (+10pts)")

        # Factor 4: MACD Signal Cross (Max 15 pts)
        macd = float(curr['macd'])
        macd_signal = float(curr['macd_signal'])
        prev_macd = float(prev['macd'])
        prev_macd_signal = float(prev['macd_signal'])

        if macd > macd_signal and prev_macd <= prev_macd_signal:
            bullish_points += 15
            reasons.append("MACD: Fresh Bullish Crossover (+15pts)")
        elif macd > macd_signal:
            bullish_points += 8
            reasons.append("MACD: Positive Histogram / Above Signal (+8pts)")
        elif macd < macd_signal and prev_macd >= prev_macd_signal:
            bearish_points += 15
            reasons.append("MACD: Fresh Bearish Crossover (+15pts)")
        elif macd < macd_signal:
            bearish_points += 8
            reasons.append("MACD: Negative Histogram / Below Signal (+8pts)")

        # Factor 5: Key Support / Resistance Bounce or Breakout (Max 15 pts)
        bb_upper = float(curr['bb_upper'])
        bb_lower = float(curr['bb_lower'])
        curr_low = float(curr['low'])
        curr_high = float(curr['high'])

        if curr_low <= bb_lower and current_price > bb_lower:
            bullish_points += 15
            reasons.append("Support: Lower Bollinger Band bounce (+15pts)")
        elif curr_high >= bb_upper and current_price < bb_upper:
            bearish_points += 15
            reasons.append("Resistance: Upper Bollinger Band rejection (+15pts)")

        # Factor 6: Internet Market Intelligence & Sentiment Bias (Max 10 pts)
        if sentiment_bias == "BULLISH" or "BULLISH" in macro_regime:
            bullish_points += 10
            reasons.append(f"Macro Sentiment: Internet market news is Bullish (+10pts)")
        elif sentiment_bias == "BEARISH" or "BEARISH" in macro_regime:
            bearish_points += 10
            reasons.append(f"Macro Sentiment: Internet market news is Bearish (+10pts)")

        # Decide Final Direction and Calculate Institutional Stops / Targets
        if bullish_points >= bearish_points and bullish_points >= MIN_SIGNAL_CONFIDENCE:
            action = "BUY"
            confidence = min(bullish_points, 100)
            # Stop loss placed below recent swing low or candle low minus 1.2x ATR
            swing_low = float(df['low'].tail(5).min())
            stop_loss = round(min(swing_low, current_price - (1.2 * atr)), 4)
            risk = current_price - stop_loss
            if risk <= 0:
                risk = atr * 1.5
                stop_loss = round(current_price - risk, 4)
            take_profit_1 = round(current_price + (risk * 1.5), 4)  # 1:1.5 RR
            take_profit_2 = round(current_price + (risk * 2.5), 4)  # 1:2.5 RR
            rr_ratio = round((take_profit_2 - current_price) / risk, 2)

        elif bearish_points > bullish_points and bearish_points >= MIN_SIGNAL_CONFIDENCE:
            action = "SELL"
            confidence = min(bearish_points, 100)
            # Stop loss placed above recent swing high or candle high plus 1.2x ATR
            swing_high = float(df['high'].tail(5).max())
            stop_loss = round(max(swing_high, current_price + (1.2 * atr)), 4)
            risk = stop_loss - current_price
            if risk <= 0:
                risk = atr * 1.5
                stop_loss = round(current_price + risk, 4)
            take_profit_1 = round(current_price - (risk * 1.5), 4)
            take_profit_2 = round(current_price - (risk * 2.5), 4)
            rr_ratio = round((current_price - take_profit_2) / risk, 2)

        else:
            action = "HOLD / NEUTRAL"
            confidence = max(bullish_points, bearish_points)
            stop_loss = round(current_price - (1.5 * atr), 4)
            take_profit_1 = round(current_price + (2.0 * atr), 4)
            take_profit_2 = round(current_price + (3.0 * atr), 4)
            rr_ratio = 2.0

        return {
            "symbol": symbol,
            "timestamp": str(curr.name),
            "current_price": round(current_price, 4),
            "action": action,
            "confidence": round(confidence, 1),
            "pattern_name": pattern_name,
            "pattern_type": pattern_type,
            "bullish_points": bullish_points,
            "bearish_points": bearish_points,
            "stop_loss": stop_loss,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "risk_reward_ratio": rr_ratio,
            "atr": round(atr, 4),
            "rsi": round(rsi, 2),
            "reasons": reasons,
            "indicators": {
                "ema_21": round(ema_21, 2),
                "ema_50": round(ema_50, 2),
                "ema_200": round(ema_200, 2),
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
                "macd": round(macd, 4),
                "macd_signal": round(macd_signal, 4)
            }
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    engine = CandleEngine()
    test_symbols = ["SPY", "NVDA", "BTC-USD"]
    print("Testing Candlestick Engine Analysis:\n")
    for s in test_symbols:
        res = engine.analyze_symbol(s, sentiment_bias="BULLISH", macro_regime="MODERATELY BULLISH")
        if res:
            print(f"[{res['symbol']}] Price: ${res['current_price']} | Action: {res['action']} ({res['confidence']}%) | Pattern: {res['pattern_name']}")
            print(f"       SL: ${res['stop_loss']} | TP1: ${res['take_profit_1']} | TP2: ${res['take_profit_2']} (R:R {res['risk_reward_ratio']})")
            print(f"       Reasons: {', '.join(res['reasons'][:2])}\n")
