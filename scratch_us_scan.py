from candle_engine import CandleEngine

stocks = ['NVDA', 'TSLA', 'AAPL', 'MSFT']
e = CandleEngine()
for s in stocks:
    r = e.analyze_symbol(s)
    if r:
        price = r["current_price"]
        action = r["action"]
        conf = r["confidence"]
        pat = r["pattern_name"]
        sl = r["stop_loss"]
        tp2 = r["take_profit_2"]
        print(f"{s}: INR Price=Rs{price:,.0f} | Action={action} | Confidence={conf}% | Pattern={pat}")
        print(f"    SL=Rs{sl:,.0f} | TP2=Rs{tp2:,.0f}")
    else:
        print(f"{s}: No data available")
