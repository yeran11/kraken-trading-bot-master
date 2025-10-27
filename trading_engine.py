"""
Real Trading Engine - Actually executes trades on Kraken
"""
import threading
import time
import json
import os
from datetime import datetime
from loguru import logger
import ccxt

class TradingEngine:
    """
    The REAL trading engine that actually makes trades
    """

    def __init__(self, api_key, api_secret):
        self.exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })

        self.is_running = False
        self.trading_thread = None
        self.positions = {}
        self.trades_history = []
        self.config = {}

        # File paths for persistence
        self.positions_file = 'positions.json'
        self.trades_file = 'trades_history.json'

        logger.info("Trading Engine initialized")

    def load_config(self):
        """Load trading pairs configuration"""
        try:
            if os.path.exists('trading_pairs_config.json'):
                with open('trading_pairs_config.json', 'r') as f:
                    raw_config = json.load(f)

                    # Handle both formats:
                    # 1. New format from Settings page: {"pairs": [...]}
                    # 2. Old flat format: {"BTC/USD": {...}, "ETH/USD": {...}}
                    if 'pairs' in raw_config and isinstance(raw_config['pairs'], list):
                        # Convert pairs array to flat dict
                        self.config = {}
                        for pair in raw_config['pairs']:
                            symbol = pair.get('symbol')
                            if symbol:
                                self.config[symbol] = {
                                    'enabled': pair.get('enabled', False),
                                    'allocation': pair.get('allocation', 10),
                                    'strategies': pair.get('strategies', ['momentum'])
                                }
                    else:
                        # Already flat format
                        self.config = raw_config
            else:
                self.config = {}

            # Load .env settings
            from dotenv import load_dotenv
            load_dotenv()

            self.stop_loss_percent = float(os.getenv('STOP_LOSS_PERCENT', '2.0'))
            self.take_profit_percent = float(os.getenv('TAKE_PROFIT_PERCENT', '3.0'))
            self.max_order_size = float(os.getenv('MAX_ORDER_SIZE_USD', '100'))

            logger.info(f"Loaded config: {len(self.config)} pairs configured")

        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self.config = {}

    def save_positions(self):
        """Save positions to file for persistence across restarts"""
        try:
            with open(self.positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2)
            logger.debug(f"Saved {len(self.positions)} positions to {self.positions_file}")
        except Exception as e:
            logger.error(f"Error saving positions: {e}")

    def load_positions(self):
        """Load positions from file"""
        try:
            if os.path.exists(self.positions_file):
                with open(self.positions_file, 'r') as f:
                    self.positions = json.load(f)
                logger.info(f"Loaded {len(self.positions)} positions from file")
            else:
                logger.info("No saved positions file found")
        except Exception as e:
            logger.error(f"Error loading positions: {e}")
            self.positions = {}

    def save_trades(self):
        """Save trade history to file"""
        try:
            with open(self.trades_file, 'w') as f:
                json.dump(self.trades_history, f, indent=2)
            logger.debug(f"Saved {len(self.trades_history)} trades to {self.trades_file}")
        except Exception as e:
            logger.error(f"Error saving trades: {e}")

    def load_trades(self):
        """Load trade history from file"""
        try:
            if os.path.exists(self.trades_file):
                with open(self.trades_file, 'r') as f:
                    self.trades_history = json.load(f)
                logger.info(f"Loaded {len(self.trades_history)} trades from file")
            else:
                logger.info("No saved trades file found")
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
            self.trades_history = []

    def sync_positions_from_kraken(self):
        """Check Kraken for open positions and sync with local state"""
        try:
            logger.info("Syncing positions from Kraken...")

            # Fetch balance to see what we hold
            balance = self.exchange.fetch_balance()

            # Check enabled pairs for holdings
            enabled_pairs = self._get_enabled_pairs()

            for pair_config in enabled_pairs:
                symbol = pair_config['symbol']

                # Extract base currency (e.g., "BTC" from "BTC/USD")
                base_currency = symbol.split('/')[0]

                # Check if we have a balance in this currency
                if base_currency in balance['total'] and balance['total'][base_currency] > 0:
                    quantity = balance['total'][base_currency]

                    # If not already in our tracked positions, add it
                    if symbol not in self.positions:
                        logger.warning(f"Found untracked position on Kraken: {quantity} {symbol}")

                        # Try to get current price to estimate entry
                        try:
                            ticker = self.exchange.fetch_ticker(symbol)
                            current_price = ticker['last']

                            # We don't know the actual entry price, so use current price
                            # This isn't perfect but prevents errors
                            self.positions[symbol] = {
                                'entry_price': current_price,
                                'quantity': quantity,
                                'usd_invested': current_price * quantity,
                                'entry_time': datetime.now().isoformat(),
                                'order_id': 'recovered',
                                'note': 'Position recovered from Kraken on startup'
                            }

                            logger.info(f"Recovered position: {symbol} qty={quantity} @ ${current_price}")

                        except Exception as e:
                            logger.error(f"Error recovering position for {symbol}: {e}")

            # Save synced positions
            self.save_positions()

            logger.info(f"Position sync complete. Tracking {len(self.positions)} positions")

        except Exception as e:
            logger.error(f"Error syncing positions from Kraken: {e}")

    def start(self):
        """Start the trading engine"""
        if self.is_running:
            logger.warning("Trading engine already running")
            return False

        self.load_config()
        self.load_positions()  # Load saved positions from file
        self.load_trades()     # Load trade history from file
        self.sync_positions_from_kraken()  # Sync with Kraken for any missing positions

        self.is_running = True

        # Start trading loop in background thread
        self.trading_thread = threading.Thread(
            target=self._trading_loop,
            daemon=True,
            name="TradingLoop"
        )
        self.trading_thread.start()

        logger.info("🚀 Trading engine STARTED - Real trades will be executed")
        return True

    def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        if self.trading_thread:
            self.trading_thread.join(timeout=5)

        logger.info("🛑 Trading engine STOPPED")
        return True

    def _trading_loop(self):
        """Main trading loop - runs continuously"""
        logger.info("Trading loop started")

        while self.is_running:
            try:
                # Get enabled trading pairs from config
                enabled_pairs = self._get_enabled_pairs()

                if not enabled_pairs:
                    logger.debug("No trading pairs enabled, waiting...")
                    time.sleep(30)
                    continue

                # Check each enabled pair
                for pair_config in enabled_pairs:
                    if not self.is_running:
                        break

                    try:
                        symbol = pair_config.get('symbol', 'UNKNOWN')
                        logger.debug(f"Processing {symbol}...")
                        self._process_pair(pair_config)
                    except Exception as e:
                        symbol = pair_config.get('symbol', 'UNKNOWN') if isinstance(pair_config, dict) else 'UNKNOWN'
                        logger.error(f"Error processing {symbol}: {e}", exc_info=True)

                # Check existing positions for stop-loss/take-profit
                self._check_positions()

                # Wait before next iteration
                time.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(60)

    def _get_enabled_pairs(self):
        """Get list of enabled trading pairs from config"""
        enabled = []

        try:
            for symbol, config in self.config.items():
                # Handle both dict and list formats
                if isinstance(config, dict):
                    # New format: {"enabled": true, "allocation": 20, "strategies": [...]}
                    if config.get('enabled', False):
                        enabled.append({
                            'symbol': symbol,
                            'allocation': config.get('allocation', 10),
                            'strategies': config.get('strategies', ['momentum'])
                        })
                elif isinstance(config, list):
                    # Old format: just a list of strategies ["momentum", "scalping"]
                    # Assume enabled if strategies are present
                    if config:
                        enabled.append({
                            'symbol': symbol,
                            'allocation': 10,  # Default 10%
                            'strategies': config
                        })
                elif isinstance(config, bool):
                    # Simple boolean format: true/false
                    if config:
                        enabled.append({
                            'symbol': symbol,
                            'allocation': 10,
                            'strategies': ['momentum']
                        })

            logger.info(f"Found {len(enabled)} enabled trading pairs: {[p['symbol'] for p in enabled]}")

        except Exception as e:
            logger.error(f"Error parsing trading pairs config: {e}")
            enabled = []

        return enabled

    def _process_pair(self, pair_config):
        """Process a single trading pair - check for buy/sell signals"""
        symbol = pair_config['symbol']
        strategies = pair_config['strategies']
        allocation = pair_config['allocation']

        if not strategies:
            return

        # Fetch current market data
        ticker = self.exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # Check if we already have a position
        if symbol in self.positions:
            # Have position - check if we should sell
            self._check_sell_signal(symbol, current_price, strategies)
        else:
            # No position - check if we should buy
            self._check_buy_signal(symbol, current_price, allocation, strategies)

    def _check_buy_signal(self, symbol, current_price, allocation, strategies):
        """Check if we should buy this pair"""

        # Get balance to see how much we can spend
        balance = self.exchange.fetch_balance()
        usd_available = balance.get('USD', {}).get('free', 0)

        if usd_available < 1:
            logger.debug(f"Insufficient USD balance: ${usd_available:.2f}")
            return

        # Calculate how much to invest based on allocation
        max_investment = (usd_available * allocation / 100)

        # Don't exceed max order size
        investment = min(max_investment, self.max_order_size)

        if investment < 1:
            logger.debug(f"{symbol}: Investment too small: ${investment:.2f}")
            return

        # Check strategy signals
        signal = self._evaluate_strategies(symbol, current_price, strategies, 'BUY')

        if signal:
            # EXECUTE BUY ORDER
            logger.info(f"🟢 BUY SIGNAL: {symbol} at ${current_price:.2f}")
            self._execute_buy(symbol, investment, current_price)

    def _check_sell_signal(self, symbol, current_price, strategies):
        """Check if we should sell this position"""
        position = self.positions[symbol]
        entry_price = position['entry_price']

        # Calculate P&L
        pnl_percent = ((current_price - entry_price) / entry_price) * 100

        # Check stop-loss
        if pnl_percent <= -self.stop_loss_percent:
            logger.warning(f"🔴 STOP LOSS triggered: {symbol} at {pnl_percent:.2f}%")
            self._execute_sell(symbol, current_price, "STOP_LOSS")
            return

        # Check take-profit
        if pnl_percent >= self.take_profit_percent:
            logger.info(f"🟢 TAKE PROFIT triggered: {symbol} at {pnl_percent:.2f}%")
            self._execute_sell(symbol, current_price, "TAKE_PROFIT")
            return

        # Check strategy sell signals
        signal = self._evaluate_strategies(symbol, current_price, strategies, 'SELL')

        if signal:
            logger.info(f"🟡 SELL SIGNAL: {symbol} at ${current_price:.2f} (P&L: {pnl_percent:.2f}%)")
            self._execute_sell(symbol, current_price, "STRATEGY")

    def _evaluate_strategies(self, symbol, current_price, strategies, action_type):
        """
        Evaluate trading strategies to determine buy/sell signals
        Returns True if signal detected
        """

        # For now, implement simple momentum strategy
        # In production, this would use the full strategies.py implementation

        try:
            # Fetch recent price data
            ohlcv = self.exchange.fetch_ohlcv(symbol, '5m', limit=100)

            if len(ohlcv) < 20:
                return False

            closes = [x[4] for x in ohlcv]  # closing prices

            # Simple momentum: compare current to recent average
            sma_20 = sum(closes[-20:]) / 20
            sma_5 = sum(closes[-5:]) / 5

            if 'momentum' in strategies:
                if action_type == 'BUY':
                    # Buy if short MA crosses above long MA (uptrend)
                    if sma_5 > sma_20 and current_price > sma_5:
                        logger.info(f"{symbol} Momentum BUY signal: Price ${current_price:.2f} > SMA5 ${sma_5:.2f} > SMA20 ${sma_20:.2f}")
                        return True

                elif action_type == 'SELL':
                    # Sell if short MA crosses below long MA (downtrend)
                    if sma_5 < sma_20:
                        logger.info(f"{symbol} Momentum SELL signal: SMA5 ${sma_5:.2f} < SMA20 ${sma_20:.2f}")
                        return True

            if 'mean_reversion' in strategies:
                # Mean reversion: buy dips, sell peaks
                std_dev = self._calculate_std(closes[-20:])
                upper_band = sma_20 + (2 * std_dev)
                lower_band = sma_20 - (2 * std_dev)

                if action_type == 'BUY':
                    # Buy when price drops below lower band
                    if current_price < lower_band:
                        logger.info(f"{symbol} Mean Reversion BUY: Price ${current_price:.2f} < Lower Band ${lower_band:.2f}")
                        return True

                elif action_type == 'SELL':
                    # Sell when price rises above upper band
                    if current_price > upper_band:
                        logger.info(f"{symbol} Mean Reversion SELL: Price ${current_price:.2f} > Upper Band ${upper_band:.2f}")
                        return True

            if 'scalping' in strategies:
                # Scalping: quick small profits
                sma_10 = sum(closes[-10:]) / 10

                if action_type == 'BUY':
                    # Buy on small dips
                    if current_price < sma_10 * 0.995:  # 0.5% below 10-period average
                        logger.info(f"{symbol} Scalping BUY: Price ${current_price:.2f} dipped below SMA10")
                        return True

                elif action_type == 'SELL':
                    # Sell on small gains (1% profit target for scalping)
                    if symbol in self.positions:
                        entry = self.positions[symbol]['entry_price']
                        if current_price > entry * 1.01:  # 1% profit
                            logger.info(f"{symbol} Scalping SELL: 1% profit target reached")
                            return True

        except Exception as e:
            logger.error(f"Error evaluating strategies for {symbol}: {e}")

        return False

    def _calculate_std(self, prices):
        """Calculate standard deviation"""
        mean = sum(prices) / len(prices)
        variance = sum((x - mean) ** 2 for x in prices) / len(prices)
        return variance ** 0.5

    def _execute_buy(self, symbol, usd_amount, price):
        """Execute a BUY order on Kraken"""
        try:
            # Calculate quantity to buy
            quantity = usd_amount / price

            logger.info(f"Executing BUY: {quantity:.8f} {symbol} for ${usd_amount:.2f}")

            # Place market buy order
            order = self.exchange.create_market_buy_order(symbol, quantity)

            # Track position
            self.positions[symbol] = {
                'entry_price': price,
                'quantity': quantity,
                'usd_invested': usd_amount,
                'entry_time': datetime.now().isoformat(),
                'order_id': order.get('id')
            }

            # Log trade
            self.trades_history.append({
                'symbol': symbol,
                'action': 'BUY',
                'price': price,
                'quantity': quantity,
                'usd_amount': usd_amount,
                'timestamp': datetime.now().isoformat()
            })

            # Save positions and trades to file
            self.save_positions()
            self.save_trades()

            logger.success(f"✅ BUY order executed: {symbol} at ${price:.2f}")

        except Exception as e:
            logger.error(f"❌ Failed to execute BUY order for {symbol}: {e}")

    def _execute_sell(self, symbol, price, reason):
        """Execute a SELL order on Kraken"""
        try:
            position = self.positions[symbol]
            quantity = position['quantity']
            entry_price = position['entry_price']

            # Calculate P&L
            pnl = (price - entry_price) * quantity
            pnl_percent = ((price - entry_price) / entry_price) * 100

            logger.info(f"Executing SELL: {quantity:.8f} {symbol} at ${price:.2f} ({reason})")

            # Place market sell order
            order = self.exchange.create_market_sell_order(symbol, quantity)

            # Remove position
            del self.positions[symbol]

            # Log trade
            self.trades_history.append({
                'symbol': symbol,
                'action': 'SELL',
                'price': price,
                'quantity': quantity,
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })

            # Save positions and trades to file
            self.save_positions()
            self.save_trades()

            logger.success(f"✅ SELL order executed: {symbol} at ${price:.2f} | P&L: ${pnl:.2f} ({pnl_percent:.2f}%)")

        except Exception as e:
            logger.error(f"❌ Failed to execute SELL order for {symbol}: {e}")

    def _check_positions(self):
        """Check all open positions for stop-loss/take-profit"""
        for symbol in list(self.positions.keys()):
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']

                position = self.positions[symbol]
                entry_price = position['entry_price']

                # Calculate P&L percentage
                pnl_percent = ((current_price - entry_price) / entry_price) * 100

                # Auto stop-loss
                if pnl_percent <= -self.stop_loss_percent:
                    logger.warning(f"🔴 AUTO STOP-LOSS: {symbol} at {pnl_percent:.2f}%")
                    self._execute_sell(symbol, current_price, "AUTO_STOP_LOSS")

                # Auto take-profit
                elif pnl_percent >= self.take_profit_percent:
                    logger.info(f"🟢 AUTO TAKE-PROFIT: {symbol} at {pnl_percent:.2f}%")
                    self._execute_sell(symbol, current_price, "AUTO_TAKE_PROFIT")

            except Exception as e:
                logger.error(f"Error checking position for {symbol}: {e}")

    def get_positions(self):
        """Get current positions"""
        return self.positions

    def get_trades(self):
        """Get trade history"""
        return self.trades_history
