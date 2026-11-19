"""
Antigravity Alpha Trader - Market Intelligence & Web Sentiment Engine
Gathers macroeconomic news, fear & greed index, and asset-specific sentiment
before any trading decisions are made.
"""

import json
import logging
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import yfinance as yf

from config import INTELLIGENCE_FILE, WATCHLIST

logger = logging.getLogger("AlphaTrader.Intelligence")

# Comprehensive Financial Sentiment Lexicon
BULLISH_KEYWORDS = {
    "surge": 2.5, "surging": 2.5, "soar": 2.5, "soaring": 2.5, "rally": 2.0, "rallies": 2.0,
    "breakout": 2.5, "record high": 3.0, "all-time high": 3.0, "beat": 2.0, "beats": 2.0,
    "bullish": 2.5, "jump": 1.5, "jumps": 1.5, "gains": 1.5, "gain": 1.5,
    "rate cut": 2.5, "rate cuts": 2.5, "easing": 1.5, "stimulus": 2.0, "expansion": 1.5,
    "upgraded": 2.0, "upgrade": 2.0, "strong demand": 2.0, "profit surge": 2.5, "rebound": 1.8,
    "recovery": 1.8, "boom": 2.0, "outperform": 2.0, "growth": 1.2, "optimism": 1.5,
    "confidence": 1.2, "higher": 1.0, "upside": 1.8, "green": 1.0, "accumulate": 1.5
}

BEARISH_KEYWORDS = {
    "slump": 2.0, "slumps": 2.0, "plunge": 2.5, "plunges": 2.5, "tumble": 2.0, "tumbles": 2.0,
    "fall": 1.5, "falls": 1.5, "drop": 1.5, "drops": 1.5, "crash": 3.0, "crashes": 3.0,
    "selloff": 2.5, "sell-off": 2.5, "bearish": 2.5, "miss": 2.0, "misses": 2.0,
    "warning": 2.0, "warns": 2.0, "rate hike": 2.5, "rate hikes": 2.5, "tightening": 1.5,
    "tariff": 1.8, "tariffs": 1.8, "inflation": 1.5, "inflation spikes": 2.5, "recession": 2.8,
    "downturn": 2.0, "downgraded": 2.0, "downgrade": 2.0, "layoffs": 1.8, "layoff": 1.8,
    "investigation": 1.8, "lawsuit": 1.5, "debt crisis": 2.8, "default": 2.5, "panic": 2.8,
    "fear": 1.8, "red": 1.0, "plummet": 2.8, "losses": 1.5, "loss": 1.2, "decline": 1.5
}


class MarketIntelligenceCollector:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_fear_and_greed_index(self):
        """Fetches the latest Crypto & Market Fear and Greed Index."""
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            resp = requests.get(url, headers=self.headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    item = data[0]
                    return {
                        "value": int(item.get("value", 50)),
                        "classification": item.get("value_classification", "Neutral"),
                        "timestamp": item.get("timestamp")
                    }
        except Exception as e:
            logger.warning(f"Could not fetch Fear & Greed index: {e}")
        return {"value": 50, "classification": "Neutral", "timestamp": str(int(time.time()))}

    def fetch_macro_news(self, max_items=15):
        """Fetches top real-time economic and stock market news from Google News RSS."""
        articles = []
        queries = ["indian+stock+market+nifty+sensex", "rbi+inflation+economy+india", "crypto+bitcoin+ethereum"]
        
        for q in queries:
            try:
                url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
                resp = requests.get(url, headers=self.headers, timeout=8)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    for item in root.findall(".//item")[:max_items]:
                        title = item.find("title").text if item.find("title") is not None else ""
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        link = item.find("link").text if item.find("link") is not None else ""
                        
                        if title and not any(a["title"] == title for a in articles):
                            articles.append({
                                "title": title,
                                "published": pub_date,
                                "source": "Google Finance News",
                                "url": link
                            })
            except Exception as e:
                logger.warning(f"Failed to fetch macro news for query '{q}': {e}")
        return articles[:max_items]

    def fetch_ticker_news(self, symbol, max_items=5):
        """Fetches ticker-specific news using Yahoo Finance."""
        articles = []
        try:
            ticker = yf.Ticker(symbol)
            news_items = ticker.news
            if news_items:
                for item in news_items[:max_items]:
                    content = item.get("content", {})
                    title = content.get("title") or item.get("title", "")
                    summary = content.get("summary") or item.get("summary", "")
                    pub_date = content.get("pubDate") or item.get("providerPublishTime", "")
                    
                    if title:
                        articles.append({
                            "title": title,
                            "summary": summary,
                            "published": str(pub_date),
                            "source": f"Yahoo Finance ({symbol})"
                        })
        except Exception as e:
            logger.warning(f"Could not fetch ticker news for {symbol}: {e}")
        return articles

    def analyze_text_sentiment(self, text):
        """Analyzes text polarity using weighted financial lexicon."""
        if not text:
            return 0.0, "NEUTRAL"
        
        text_lower = text.lower()
        bull_score = 0.0
        bear_score = 0.0

        for word, weight in BULLISH_KEYWORDS.items():
            matches = len(re.findall(r'\b' + re.escape(word) + r'\b', text_lower))
            bull_score += matches * weight

        for word, weight in BEARISH_KEYWORDS.items():
            matches = len(re.findall(r'\b' + re.escape(word) + r'\b', text_lower))
            bear_score += matches * weight

        net_score = bull_score - bear_score
        
        # Normalize into range [-1.0, 1.0]
        total = bull_score + bear_score
        if total == 0:
            return 0.0, "NEUTRAL"
        
        normalized = max(min(net_score / max(total, 3.0), 1.0), -1.0)
        
        if normalized >= 0.25:
            sentiment = "BULLISH"
        elif normalized <= -0.25:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
            
        return round(normalized, 3), sentiment

    def collect_full_intelligence(self, force_refresh=False):
        """
        Runs comprehensive internet search and news synthesis.
        Returns a complete Market Intelligence Dossier.
        """
        # Check cache if not older than 10 minutes
        if not force_refresh and os.path.exists(INTELLIGENCE_FILE):
            try:
                with open(INTELLIGENCE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    cache_time = cached.get("timestamp_epoch", 0)
                    if time.time() - cache_time < 600:  # 10 min cache
                        return cached
            except Exception:
                pass

        logger.info("Scanning the internet for live market news and sentiment...")
        fng = self.fetch_fear_and_greed_index()
        macro_news = self.fetch_macro_news(max_items=12)

        # Analyze macro news
        scored_macro_news = []
        macro_sentiment_sum = 0.0
        for article in macro_news:
            score, tag = self.analyze_text_sentiment(article["title"])
            macro_sentiment_sum += score
            scored_macro_news.append({
                **article,
                "sentiment_score": score,
                "sentiment_tag": tag
            })

        avg_macro_sentiment = (macro_sentiment_sum / len(scored_macro_news)) if scored_macro_news else 0.0

        # Collect per-symbol news and sentiment
        symbol_intelligence = {}
        for item in WATCHLIST:
            sym = item["symbol"]
            sym_news = self.fetch_ticker_news(sym, max_items=4)
            sym_scores = []
            enriched_news = []
            for n in sym_news:
                full_text = f"{n['title']} {n.get('summary', '')}"
                sc, tag = self.analyze_text_sentiment(full_text)
                sym_scores.append(sc)
                enriched_news.append({**n, "sentiment_score": sc, "sentiment_tag": tag})

            sym_avg = (sum(sym_scores) / len(sym_scores)) if sym_scores else 0.0
            symbol_intelligence[sym] = {
                "name": item["name"],
                "type": item["type"],
                "sentiment_score": round(sym_avg, 3),
                "sentiment_tag": "BULLISH" if sym_avg >= 0.15 else ("BEARISH" if sym_avg <= -0.15 else "NEUTRAL"),
                "news_count": len(enriched_news),
                "top_news": enriched_news[:2]
            }

        # Calculate Overall Market Score (-100 to +100)
        # Factor 1: Macro News sentiment (50% weight)
        # Factor 2: Fear & Greed Index normalized to -1 to +1 (30% weight)
        # Factor 3: Symbol average sentiment (20% weight)
        fng_norm = (fng["value"] - 50.0) / 50.0  # e.g., 11 => -0.78
        sym_sentiment_avg = sum(s["sentiment_score"] for s in symbol_intelligence.values()) / max(len(symbol_intelligence), 1)

        composite_score = (avg_macro_sentiment * 0.45) + (fng_norm * 0.35) + (sym_sentiment_avg * 0.20)
        composite_score_100 = round(composite_score * 100, 1)

        if composite_score_100 >= 30:
            market_regime = "STRONG BULLISH"
        elif composite_score_100 >= 10:
            market_regime = "MODERATELY BULLISH"
        elif composite_score_100 <= -30:
            market_regime = "STRONG BEARISH"
        elif composite_score_100 <= -10:
            market_regime = "MODERATELY BEARISH"
        else:
            market_regime = "NEUTRAL / BALANCED"

        dossier = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_epoch": time.time(),
            "market_regime": market_regime,
            "composite_score": composite_score_100,
            "fear_and_greed": fng,
            "macro_sentiment_score": round(avg_macro_sentiment, 3),
            "macro_news": scored_macro_news,
            "symbol_intelligence": symbol_intelligence,
            "summary_for_trader": (
                f"Market Regime is {market_regime} (Score: {composite_score_100}/100). "
                f"Fear & Greed Index: {fng['value']} ({fng['classification']}). "
                f"Analyzed {len(scored_macro_news)} macro headlines and {len(symbol_intelligence)} asset feeds."
            )
        }

        # Save to disk
        try:
            with open(INTELLIGENCE_FILE, "w", encoding="utf-8") as f:
                json.dump(dossier, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving intelligence dossier: {e}")

        return dossier


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    collector = MarketIntelligenceCollector()
    d = collector.collect_full_intelligence(force_refresh=True)
    print("\n=== MARKET INTELLIGENCE SUMMARY ===")
    print(d["summary_for_trader"])
    print("\nTop 3 Macro News:")
    for a in d["macro_news"][:3]:
        print(f" - [{a['sentiment_tag']} | {a['sentiment_score']}] {a['title']}")
