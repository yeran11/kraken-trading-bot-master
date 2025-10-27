"""
Kraken API Client for Spot and Futures Trading
"""
import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any
import requests
import krakenex
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import json
import websocket
import threading
from decimal import Decimal
import ccxt

import config


class KrakenClient:
    """Kraken API client for spot and futures trading"""

    def __init__(self):
        """Initialize Kraken client"""
        self.api_key = config.KRAKEN_API_KEY
        self.api_secret = config.KRAKEN_API_SECRET
        self.base_url = config.KRAKEN_BASE_URL
        self.futures_url = config.KRAKEN_FUTURES_URL
        self.session = requests.Session()

        # Initialize krakenex for spot trading
        self.kraken = krakenex.API()
        self.kraken.key = self.api_key
        self.kraken.secret = self.api_secret

        # Initialize CCXT for unified interface
        self.ccxt_client = ccxt.kraken({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # or 'futures'
            }
        })

        # WebSocket connections
        self.ws_connections = {}
        self.ws_callbacks = {}

        # Cache for frequently accessed data
        self.price_cache = {}
        self.balance_cache = {}
        self.last_cache_update = {}

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / config.API_RATE_LIMIT

        # Paper trading state
        self.paper_trading = config.PAPER_TRADING
        self.paper_balance = {'USD': 10000.0}
        self.paper_positions = {}
        self.paper_orders = {}

        logger.info(f"Kraken client initialized (Paper Trading: {self.paper_trading})")

    # ====================
    # AUTHENTICATION
    # ====================

    def _sign_request(self, urlpath: str, data: Dict, secret: str) -> str:
        """Sign request for Kraken API"""
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(signature.digest())
        return sigdigest.decode()

    def _make_request(self, endpoint: str, data: Optional[Dict] = None,
                     is_private: bool = False, is_futures: bool = False) -> Dict:
        """Make API request to Kraken"""
        # Rate limiting
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        try:
            if is_futures:
                url = f"{self.futures_url}{endpoint}"
            else:
                url = f"{self.base_url}{endpoint}"

            if is_private:
                if not data:
                    data = {}
                data['nonce'] = int(time.time() * 1000)

                headers = {
                    'API-Key': self.api_key,
                    'API-Sign': self._sign_request(endpoint, data, self.api_secret),
                    'Content-Type': 'application/x-www-form-urlencoded'
                }

                response = self.session.post(url, headers=headers, data=data)
            else:
                response = self.session.get(url, params=data)

            self.last_request_time = time.time()
            result = response.json()

            if 'error' in result and result['error']:
                raise Exception(f"Kraken API error: {result['error']}")

            return result.get('result', result)

        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    # ====================
    # MARKET DATA
    # ====================

    def get_ticker(self, symbol: str) -> Dict:
        """Get ticker information"""
        if self.paper_trading:
            return self._get_paper_ticker(symbol)

        try:
            # Check cache
            cache_key = f"ticker_{symbol}"
            if self._is_cache_valid(cache_key, config.PRICE_CACHE_TTL):
                return self.price_cache[cache_key]

            # Use CCXT for unified interface
            ticker = self.ccxt_client.fetch_ticker(symbol)

            result = {
                'symbol': symbol,
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'volume': ticker['quoteVolume'],
                'high': ticker['high'],
                'low': ticker['low'],
                'change': ticker['percentage'],
                'timestamp': ticker['timestamp']
            }

            # Update cache
            self.price_cache[cache_key] = result
            self.last_cache_update[cache_key] = time.time()

            return result

        except Exception as e:
            logger.error(f"Error getting ticker for {symbol}: {e}")
            raise

    def get_orderbook(self, symbol: str, depth: int = 20) -> Dict:
        """Get order book"""
        try:
            orderbook = self.ccxt_client.fetch_order_book(symbol, depth)
            return {
                'bids': orderbook['bids'],
                'asks': orderbook['asks'],
                'timestamp': orderbook['timestamp'],
                'symbol': symbol
            }
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            raise

    def get_ohlcv(self, symbol: str, timeframe: str = '5m',
                  limit: int = 100) -> pd.DataFrame:
        """Get OHLCV data"""
        try:
            # Convert timeframe to Kraken format
            timeframe_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '4h': '4h', '1d': '1d'
            }

            kraken_timeframe = timeframe_map.get(timeframe, '5m')

            # Fetch OHLCV data
            ohlcv = self.ccxt_client.fetch_ohlcv(
                symbol, kraken_timeframe, limit=limit
            )

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            return df

        except Exception as e:
            logger.error(f"Error getting OHLCV for {symbol}: {e}")
            raise

    def get_trades(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get recent trades"""
        try:
            trades = self.ccxt_client.fetch_trades(symbol, limit=limit)
            return [
                {
                    'id': trade['id'],
                    'timestamp': trade['timestamp'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'price': trade['price'],
                    'amount': trade['amount'],
                    'cost': trade['cost']
                }
                for trade in trades
            ]
        except Exception as e:
            logger.error(f"Error getting trades for {symbol}: {e}")
            raise

    # ====================
    # ACCOUNT MANAGEMENT
    # ====================

    def get_balance(self) -> Dict:
        """Get account balance"""
        if self.paper_trading:
            return self.paper_balance.copy()

        try:
            # Check cache
            if self._is_cache_valid('balance', 5):
                return self.balance_cache

            balance = self.ccxt_client.fetch_balance()

            # Format balance
            result = {}
            for currency, details in balance['total'].items():
                if details > 0:
                    result[currency] = {
                        'total': details,
                        'free': balance['free'].get(currency, 0),
                        'used': balance['used'].get(currency, 0)
                    }

            # Update cache
            self.balance_cache = result
            self.last_cache_update['balance'] = time.time()

            return result

        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise

    def get_positions(self) -> List[Dict]:
        """Get open positions"""
        if self.paper_trading:
            return list(self.paper_positions.values())

        try:
            positions = self.ccxt_client.fetch_positions()

            return [
                {
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'contracts': pos['contracts'],
                    'contractSize': pos['contractSize'],
                    'unrealizedPnl': pos['unrealizedPnl'],
                    'percentage': pos['percentage'],
                    'markPrice': pos['markPrice'],
                    'entryPrice': pos['info'].get('avgPrice', 0),
                    'timestamp': pos['timestamp']
                }
                for pos in positions if pos['contracts'] > 0
            ]

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get open orders"""
        if self.paper_trading:
            if symbol:
                return [o for o in self.paper_orders.values()
                       if o['symbol'] == symbol and o['status'] == 'open']
            return list(self.paper_orders.values())

        try:
            orders = self.ccxt_client.fetch_open_orders(symbol)

            return [
                {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'price': order['price'],
                    'amount': order['amount'],
                    'filled': order['filled'],
                    'remaining': order['remaining'],
                    'status': order['status'],
                    'timestamp': order['timestamp']
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []

    def get_order_history(self, symbol: Optional[str] = None,
                         limit: int = 100) -> List[Dict]:
        """Get order history"""
        try:
            if self.paper_trading:
                return []

            orders = self.ccxt_client.fetch_closed_orders(symbol, limit=limit)

            return [
                {
                    'id': order['id'],
                    'symbol': order['symbol'],
                    'type': order['type'],
                    'side': order['side'],
                    'price': order['price'],
                    'amount': order['amount'],
                    'filled': order['filled'],
                    'cost': order['cost'],
                    'status': order['status'],
                    'timestamp': order['timestamp']
                }
                for order in orders
            ]

        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []

    # ====================
    # ORDER MANAGEMENT
    # ====================

    def place_order(self, symbol: str, side: str, order_type: str,
                   amount: float, price: Optional[float] = None,
                   stop_price: Optional[float] = None,
                   reduce_only: bool = False,
                   leverage: Optional[int] = None) -> Dict:
        """Place an order"""
        try:
            # Validate order
            if amount * (price or self._get_current_price(symbol)) < config.MIN_ORDER_SIZE_USD:
                raise ValueError(f"Order size below minimum: ${config.MIN_ORDER_SIZE_USD}")

            if self.paper_trading:
                return self._place_paper_order(
                    symbol, side, order_type, amount, price
                )

            # Prepare order parameters
            params = {}
            if stop_price:
                params['stopPrice'] = stop_price
            if reduce_only:
                params['reduceOnly'] = True
            if leverage and config.ENABLE_FUTURES_TRADING:
                params['leverage'] = min(leverage, config.MAX_LEVERAGE)

            # Place order based on type
            if order_type.upper() == 'MARKET':
                order = self.ccxt_client.create_market_order(
                    symbol, side, amount, params
                )
            elif order_type.upper() == 'LIMIT':
                if not price:
                    raise ValueError("Price required for limit orders")
                order = self.ccxt_client.create_limit_order(
                    symbol, side, amount, price, params
                )
            elif order_type.upper() == 'STOP_LOSS':
                if not stop_price:
                    raise ValueError("Stop price required for stop loss orders")
                params['type'] = 'stop_loss'
                order = self.ccxt_client.create_order(
                    symbol, 'stop_loss', side, amount, None, params
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            logger.info(f"Order placed: {order['id']} - {side} {amount} {symbol}")

            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'type': order['type'],
                'amount': order['amount'],
                'price': order.get('price'),
                'status': order['status'],
                'timestamp': order['timestamp']
            }

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        if self.paper_trading:
            if order_id in self.paper_orders:
                self.paper_orders[order_id]['status'] = 'cancelled'
                return True
            return False

        try:
            result = self.ccxt_client.cancel_order(order_id, symbol)
            logger.info(f"Order cancelled: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        """Cancel all open orders"""
        try:
            orders = self.get_open_orders(symbol)
            cancelled = 0

            for order in orders:
                if self.cancel_order(order['id'], order['symbol']):
                    cancelled += 1

            logger.info(f"Cancelled {cancelled} orders")
            return cancelled

        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return 0

    # ====================
    # FUTURES TRADING
    # ====================

    def get_futures_positions(self) -> List[Dict]:
        """Get futures positions"""
        if not config.ENABLE_FUTURES_TRADING:
            return []

        try:
            # Switch to futures
            self.ccxt_client.options['defaultType'] = 'future'
            positions = self.ccxt_client.fetch_positions()
            self.ccxt_client.options['defaultType'] = 'spot'

            return [
                {
                    'symbol': pos['symbol'],
                    'side': pos['side'],
                    'contracts': pos['contracts'],
                    'notional': pos['notional'],
                    'unrealizedPnl': pos['unrealizedPnl'],
                    'realizedPnl': pos['realizedPnl'],
                    'percentage': pos['percentage'],
                    'leverage': pos['info'].get('leverage', 1),
                    'liquidationPrice': pos['liquidationPrice'],
                    'markPrice': pos['markPrice'],
                    'entryPrice': pos['info'].get('avgPrice', 0)
                }
                for pos in positions if pos['contracts'] > 0
            ]

        except Exception as e:
            logger.error(f"Error getting futures positions: {e}")
            return []

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for futures trading"""
        if not config.ENABLE_FUTURES_TRADING:
            return False

        try:
            leverage = min(leverage, config.MAX_LEVERAGE)

            self.ccxt_client.options['defaultType'] = 'future'
            result = self.ccxt_client.set_leverage(leverage, symbol)
            self.ccxt_client.options['defaultType'] = 'spot'

            logger.info(f"Leverage set to {leverage}x for {symbol}")
            return True

        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return False

    # ====================
    # WEBSOCKET STREAMING
    # ====================

    def subscribe_ticker(self, symbols: List[str], callback):
        """Subscribe to ticker updates via WebSocket"""
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if callback:
                    callback(data)
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")

        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")

        def on_close(ws):
            logger.info("WebSocket closed")

        def on_open(ws):
            # Subscribe to ticker channels
            for symbol in symbols:
                subscribe_msg = {
                    "event": "subscribe",
                    "pair": [symbol],
                    "subscription": {"name": "ticker"}
                }
                ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to ticker for {symbols}")

        ws_url = config.KRAKEN_WS_URL
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )

        # Run in separate thread
        ws_thread = threading.Thread(target=ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

        # Store connection
        self.ws_connections['ticker'] = ws
        self.ws_callbacks['ticker'] = callback

        return ws

    def subscribe_trades(self, symbols: List[str], callback):
        """Subscribe to trade updates"""
        # Similar to subscribe_ticker but for trades
        pass

    def subscribe_orderbook(self, symbols: List[str], callback):
        """Subscribe to orderbook updates"""
        # Similar to subscribe_ticker but for orderbook
        pass

    # ====================
    # HELPER METHODS
    # ====================

    def _is_cache_valid(self, key: str, ttl: int) -> bool:
        """Check if cache is valid"""
        if key not in self.last_cache_update:
            return False
        return time.time() - self.last_cache_update[key] < ttl

    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        ticker = self.get_ticker(symbol)
        return ticker['last']

    # ====================
    # PAPER TRADING
    # ====================

    def _get_paper_ticker(self, symbol: str) -> Dict:
        """Get simulated ticker for paper trading"""
        # Simulate price with random walk
        base_price = {
            'BTC/USD': 45000, 'ETH/USD': 2500, 'SOL/USD': 100,
            'MATIC/USD': 0.8, 'LINK/USD': 15
        }.get(symbol, 100)

        # Add some randomness
        variation = np.random.normal(0, 0.001)
        price = base_price * (1 + variation)

        return {
            'symbol': symbol,
            'bid': price * 0.9999,
            'ask': price * 1.0001,
            'last': price,
            'volume': np.random.uniform(1000, 10000),
            'high': price * 1.01,
            'low': price * 0.99,
            'change': variation * 100,
            'timestamp': int(time.time() * 1000)
        }

    def _place_paper_order(self, symbol: str, side: str, order_type: str,
                          amount: float, price: Optional[float] = None) -> Dict:
        """Place paper trading order"""
        order_id = f"paper_{int(time.time() * 1000)}"

        if not price:
            price = self._get_current_price(symbol)

        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'amount': amount,
            'price': price,
            'status': 'filled' if order_type == 'MARKET' else 'open',
            'timestamp': int(time.time() * 1000)
        }

        # Update paper balance
        if order_type == 'MARKET':
            cost = amount * price
            if side == 'BUY':
                if 'USD' in self.paper_balance and self.paper_balance['USD'] >= cost:
                    self.paper_balance['USD'] -= cost
                    base_currency = symbol.split('/')[0]
                    if base_currency not in self.paper_balance:
                        self.paper_balance[base_currency] = 0
                    self.paper_balance[base_currency] += amount
            else:  # SELL
                base_currency = symbol.split('/')[0]
                if base_currency in self.paper_balance and \
                   self.paper_balance[base_currency] >= amount:
                    self.paper_balance[base_currency] -= amount
                    self.paper_balance['USD'] += cost

        self.paper_orders[order_id] = order
        logger.info(f"Paper order placed: {order}")

        return order

    def close_all_positions(self) -> bool:
        """Close all open positions"""
        try:
            positions = self.get_positions()

            for position in positions:
                # Place market order to close position
                side = 'SELL' if position['side'] == 'long' else 'BUY'
                self.place_order(
                    symbol=position['symbol'],
                    side=side,
                    order_type='MARKET',
                    amount=abs(position['contracts']),
                    reduce_only=True
                )

            logger.info(f"Closed {len(positions)} positions")
            return True

        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return False