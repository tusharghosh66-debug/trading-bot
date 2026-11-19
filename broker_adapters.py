"""
Antigravity Alpha Trader - Live Broker Integration Adapters
Plug-and-play templates for live brokers: Zerodha Kite, Alpaca, Binance, Interactive Brokers.
To trade real money, fill in your API credentials below and set EXECUTION_MODE = 'LIVE' in config.py.
"""

import logging
from execution_engine import BrokerAdapterBase

logger = logging.getLogger("AlphaTrader.BrokerAdapters")


class AlpacaBrokerAdapter(BrokerAdapterBase):
    """
    Adapter for Alpaca Markets (Equities & Crypto).
    Install dependency: pip install alpaca-trade-api
    """
    def __init__(self, api_key="", api_secret="", base_url="https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.client = None
        if api_key and api_secret:
            try:
                import alpaca_trade_api as tradeapi
                self.client = tradeapi.REST(api_key, api_secret, base_url, api_version='v2')
                logger.info("Alpaca Broker connected successfully.")
            except ImportError:
                logger.warning("Alpaca SDK not installed. Run: pip install alpaca-trade-api")

    def place_order(self, symbol, side, quantity, order_type="market", stop_loss=None, take_profit=None):
        if not self.client:
            logger.warning("Alpaca client not initialized.")
            return None
        try:
            order_data = {
                "symbol": symbol,
                "qty": quantity,
                "side": side.lower(),
                "type": order_type.lower(),
                "time_in_force": "gtc"
            }
            if stop_loss and take_profit:
                order_data["order_class"] = "bracket"
                order_data["stop_loss"] = {"stop_price": stop_loss}
                order_data["take_profit"] = {"limit_price": take_profit}

            order = self.client.submit_order(**order_data)
            return order
        except Exception as e:
            logger.error(f"Alpaca place_order failed: {e}")
            return None


class BinanceBrokerAdapter(BrokerAdapterBase):
    """
    Adapter for Binance (Crypto Spot / Futures).
    Install dependency: pip install python-binance
    """
    def __init__(self, api_key="", api_secret="", testnet=True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.client = None
        if api_key and api_secret:
            try:
                from binance.client import Client
                self.client = Client(api_key, api_secret, testnet=testnet)
                logger.info("Binance Broker connected successfully.")
            except ImportError:
                logger.warning("Binance SDK not installed. Run: pip install python-binance")

    def place_order(self, symbol, side, quantity, order_type="MARKET", stop_loss=None, take_profit=None):
        if not self.client:
            logger.warning("Binance client not initialized.")
            return None
        try:
            clean_symbol = symbol.replace("-", "").replace("/", "")
            return self.client.create_order(
                symbol=clean_symbol,
                side=side.upper(),
                type=order_type.upper(),
                quantity=quantity
            )
        except Exception as e:
            logger.error(f"Binance order failed: {e}")
            return None


class ZerodhaKiteAdapter(BrokerAdapterBase):
    """
    Adapter for Zerodha Kite Connect (Indian Equities & F&O).
    Install dependency: pip install kiteconnect
    """
    def __init__(self, api_key="", api_secret="", access_token=""):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = None
        if api_key and access_token:
            try:
                from kiteconnect import KiteConnect
                self.kite = KiteConnect(api_key=api_key)
                self.kite.set_access_token(access_token)
                logger.info("Zerodha Kite connected successfully.")
            except ImportError:
                logger.warning("kiteconnect not installed. Run: pip install kiteconnect")

    def place_order(self, symbol, side, quantity, order_type="MARKET", stop_loss=None, take_profit=None):
        if not self.kite:
            logger.warning("Zerodha Kite not initialized.")
            return None
        try:
            kite_side = self.kite.TRANSACTION_TYPE_BUY if side.upper() == "BUY" else self.kite.TRANSACTION_TYPE_SELL
            order_id = self.kite.place_order(
                variety=self.kite.VARIETY_REGULAR,
                exchange=self.kite.EXCHANGE_NSE,
                tradingsymbol=symbol,
                transaction_type=kite_side,
                quantity=int(quantity),
                order_type=self.kite.ORDER_TYPE_MARKET,
                product=self.kite.PRODUCT_CNC
            )
            return order_id
        except Exception as e:
            logger.error(f"Zerodha Kite order failed: {e}")
            return None
