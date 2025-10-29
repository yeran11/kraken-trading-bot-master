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
import asyncio
import pandas as pd

# AI Ensemble - Master Trader Intelligence
from ai_ensemble import AIEnsemble

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

        # Initialize AI Ensemble
        from dotenv import load_dotenv
        load_dotenv()
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        self.ai_ensemble = AIEnsemble(deepseek_api_key=deepseek_key)

        # AI configuration
        self.ai_enabled = os.getenv('AI_ENSEMBLE_ENABLED', 'true').lower() == 'true'
        self.ai_min_confidence = float(os.getenv('AI_MIN_CONFIDENCE', '0.65'))

        logger.success("✓ Trading Engine initialized with AI Ensemble")
        if deepseek_key:
            logger.info("🧠 AI Ensemble: FULL MODE (DeepSeek enabled)")
        else:
            logger.warning("🧠 AI Ensemble: DEMO MODE (Set DEEPSEEK_API_KEY for full AI)")

        # Log AI health
        ai_health = self.ai_ensemble.get_model_health()
        logger.info(f"AI Health: {ai_health['overall']} - {ai_health}")

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
            logger.info(f"🟢 STRATEGY SIGNAL: {symbol} at ${current_price:.2f}")

            # AI VALIDATION - Master Trader validates the signal
            if self.ai_enabled:
                try:
                    logger.info(f"🧠 Validating {symbol} with AI Ensemble...")

                    # Fetch candles for AI analysis
                    candles_data = self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)

                    # Convert to list of dicts for AI
                    candles = []
                    for candle in candles_data:
                        candles.append({
                            'timestamp': candle[0],
                            'open': candle[1],
                            'high': candle[2],
                            'low': candle[3],
                            'close': candle[4],
                            'volume': candle[5]
                        })

                    # Prepare technical indicators for AI
                    closes = [c[4] for c in candles_data]
                    technical_indicators = self._get_technical_indicators(closes, current_price)

                    # Get AI signal using asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    ai_result = loop.run_until_complete(
                        self.ai_ensemble.generate_signal(
                            symbol=symbol,
                            current_price=current_price,
                            candles=candles,
                            technical_indicators=technical_indicators
                        )
                    )
                    loop.close()

                    ai_signal = ai_result['signal']
                    ai_confidence = ai_result['confidence']
                    ai_reasoning = ai_result['reasoning']

                    logger.info(f"🤖 AI Decision: {ai_signal} (confidence: {ai_confidence*100:.1f}%)")
                    logger.info(f"💭 AI Reasoning: {ai_reasoning}")

                    # Check if AI agrees with BUY
                    if ai_signal != 'BUY':
                        logger.warning(f"⚠️ AI OVERRIDE: AI recommends {ai_signal}, cancelling BUY")
                        return

                    # Check confidence threshold
                    if ai_confidence < self.ai_min_confidence:
                        logger.warning(f"⚠️ AI CONFIDENCE TOO LOW: {ai_confidence*100:.1f}% < {self.ai_min_confidence*100:.1f}% threshold")
                        return

                    logger.success(f"✓ AI APPROVED: {symbol} BUY signal validated!")

                except Exception as e:
                    logger.error(f"AI validation error: {e}")
                    logger.warning("Proceeding without AI validation (fallback to strategy only)")

            # EXECUTE BUY ORDER
            logger.info(f"🚀 EXECUTING BUY: {symbol} at ${current_price:.2f}")

            # Determine which strategy triggered (for trailing stop logic)
            strategy_name = 'unknown'
            if 'macd_supertrend' in strategies:
                strategy_name = 'macd_supertrend'
            elif 'momentum' in strategies:
                strategy_name = 'momentum'
            elif 'mean_reversion' in strategies:
                strategy_name = 'mean_reversion'
            elif 'scalping' in strategies:
                strategy_name = 'scalping'

            self._execute_buy(symbol, investment, current_price, strategy_name)

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
            highs = [x[2] for x in ohlcv]   # high prices
            lows = [x[3] for x in ohlcv]    # low prices
            volumes = [x[5] for x in ohlcv] # volume

            # Simple momentum: compare current to recent average
            sma_20 = sum(closes[-20:]) / 20
            sma_5 = sum(closes[-5:]) / 5

            if 'momentum' in strategies:
                if action_type == 'BUY':
                    # Buy if short MA is SIGNIFICANTLY above long MA (strong uptrend)
                    # Require at least 0.5% separation to avoid noise
                    sma_diff_percent = ((sma_5 - sma_20) / sma_20) * 100

                    if sma_5 > sma_20 and current_price > sma_5 and sma_diff_percent >= 0.5:
                        logger.info(f"{symbol} Momentum BUY signal: Price ${current_price:.2f} > SMA5 ${sma_5:.2f} > SMA20 ${sma_20:.2f} (Gap: {sma_diff_percent:.2f}%)")
                        return True
                    else:
                        logger.debug(f"{symbol} Momentum BUY: Not strong enough. SMA5/SMA20 gap: {sma_diff_percent:.2f}% (need 0.5%+)")

                elif action_type == 'SELL':
                    # CRITICAL FIX: Only sell if momentum has CLEARLY reversed
                    # Require SMA5 to be at least 0.3% BELOW SMA20 (not just any amount)
                    # This prevents immediate sell-offs from small dips
                    sma_diff_percent = ((sma_5 - sma_20) / sma_20) * 100

                    # Also check minimum hold time (at least 15 minutes)
                    if symbol in self.positions:
                        entry_time_str = self.positions[symbol].get('entry_time', '')
                        if entry_time_str:
                            from datetime import datetime
                            entry_time = datetime.fromisoformat(entry_time_str)
                            hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

                            if hold_minutes < 15:
                                logger.debug(f"{symbol} Momentum SELL: Too soon! Hold time: {hold_minutes:.1f} min (need 15 min)")
                                return False

                    # Require CLEAR downtrend: SMA5 must be 0.3%+ below SMA20
                    if sma_5 < sma_20 and sma_diff_percent <= -0.3:
                        logger.info(f"{symbol} Momentum SELL signal: Clear downtrend - SMA5 ${sma_5:.2f} < SMA20 ${sma_20:.2f} (Gap: {sma_diff_percent:.2f}%)")
                        return True
                    else:
                        logger.debug(f"{symbol} Momentum SELL: Not confirmed. SMA5/SMA20 gap: {sma_diff_percent:.2f}% (need -0.3% or lower)")
                        return False

            if 'mean_reversion' in strategies:
                # Mean reversion: buy dips, sell peaks
                std_dev = self._calculate_std(closes[-20:])
                upper_band = sma_20 + (2 * std_dev)
                lower_band = sma_20 - (2 * std_dev)
                middle_band = sma_20

                if action_type == 'BUY':
                    # Buy when price drops below lower band (oversold)
                    if current_price < lower_band:
                        deviation = ((current_price - lower_band) / lower_band) * 100
                        logger.info(f"{symbol} Mean Reversion BUY: Price ${current_price:.6f} < Lower Band ${lower_band:.6f} (Deviation: {deviation:.2f}%)")
                        return True
                    else:
                        logger.debug(f"{symbol} Mean Reversion BUY: Not oversold. Price: ${current_price:.6f}, Lower Band: ${lower_band:.6f}")

                elif action_type == 'SELL':
                    # CRITICAL FIX: Sell when price returns to middle or above
                    # Don't wait for upper band - that's too extreme!
                    if symbol in self.positions:
                        entry_price = self.positions[symbol]['entry_price']

                        # Check minimum hold time (at least 10 minutes)
                        entry_time_str = self.positions[symbol].get('entry_time', '')
                        if entry_time_str:
                            from datetime import datetime
                            entry_time = datetime.fromisoformat(entry_time_str)
                            hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

                            if hold_minutes < 10:
                                logger.debug(f"{symbol} Mean Reversion SELL: Too soon! Hold time: {hold_minutes:.1f} min (need 10 min)")
                                return False

                        # Calculate profit
                        profit_percent = ((current_price - entry_price) / entry_price) * 100

                        # SELL if any of these conditions:
                        # 1. Price reached middle band AND profit >= 1.5%
                        # 2. Price reached upper band (extreme overbought)
                        # 3. Profit >= 2.5% (good profit regardless of bands)

                        if current_price >= middle_band and profit_percent >= 1.5:
                            logger.info(f"{symbol} Mean Reversion SELL: Price returned to middle - ${current_price:.6f} >= ${middle_band:.6f}, Profit: {profit_percent:.2f}%")
                            return True
                        elif current_price > upper_band:
                            logger.info(f"{symbol} Mean Reversion SELL: Extreme overbought - Price ${current_price:.6f} > Upper Band ${upper_band:.6f}, Profit: {profit_percent:.2f}%")
                            return True
                        elif profit_percent >= 2.5:
                            logger.info(f"{symbol} Mean Reversion SELL: Good profit target reached - {profit_percent:.2f}%")
                            return True
                        else:
                            logger.debug(f"{symbol} Mean Reversion SELL: Waiting for reversion. Price: ${current_price:.6f}, Middle: ${middle_band:.6f}, Profit: {profit_percent:.2f}%")
                            return False

            if 'scalping' in strategies:
                # Scalping: quick small profits
                # MODIFIED: Less aggressive to avoid over-trading
                sma_10 = sum(closes[-10:]) / 10

                if action_type == 'BUY':
                    # Buy on bigger dips (changed from 0.5% to 1.5%)
                    if current_price < sma_10 * 0.985:  # 1.5% below 10-period average
                        logger.info(f"{symbol} Scalping BUY: Price ${current_price:.2f} dipped 1.5%+ below SMA10")
                        return True
                    else:
                        logger.debug(f"{symbol} Scalping BUY: Dip not significant enough")

                elif action_type == 'SELL':
                    # CRITICAL FIX: Increased profit target to 2% (was 1%)
                    # 1% barely covers fees (0.32% round trip)
                    # 2% gives actual profit margin
                    if symbol in self.positions:
                        entry = self.positions[symbol]['entry_price']

                        # Also check minimum hold time (at least 10 minutes for scalping)
                        entry_time_str = self.positions[symbol].get('entry_time', '')
                        if entry_time_str:
                            from datetime import datetime
                            entry_time = datetime.fromisoformat(entry_time_str)
                            hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

                            if hold_minutes < 10:
                                logger.debug(f"{symbol} Scalping SELL: Too soon! Hold time: {hold_minutes:.1f} min (need 10 min)")
                                return False

                        if current_price > entry * 1.02:  # 2% profit (was 1%)
                            pnl_percent = ((current_price - entry) / entry) * 100
                            logger.info(f"{symbol} Scalping SELL: 2% profit target reached (P&L: {pnl_percent:.2f}%)")
                            return True
                        else:
                            logger.debug(f"{symbol} Scalping SELL: Not at 2% profit yet")

            # MACD + Supertrend Trend Following Strategy
            if 'macd_supertrend' in strategies:
                # This strategy only generates BUY signals
                # Risk management (stop-loss/take-profit) handles SELL

                if action_type == 'BUY':
                    # Step 1: Check minimum data requirements
                    if len(closes) < 30:
                        logger.debug(f"{symbol} MACD+Supertrend: Not enough data (need 30+ candles)")
                        return False

                    # Step 2: Calculate all indicators
                    macd_line, signal_line, histogram = self._calculate_macd(closes)
                    supertrend, trend_direction = self._calculate_supertrend(highs, lows, closes)
                    rsi = self._calculate_rsi(closes)
                    adx = self._calculate_adx(highs, lows, closes)

                    # Check if we have valid indicator values
                    if not all([macd_line, signal_line, supertrend, rsi, adx]):
                        logger.debug(f"{symbol} MACD+Supertrend: Indicators not ready")
                        return False

                    # Step 3: FIRST condition - MACD must have crossed above signal recently
                    macd_crossed = self._check_macd_crossover(symbol, macd_line, signal_line, max_age_minutes=30)

                    if not macd_crossed:
                        logger.debug(f"{symbol} MACD+Supertrend BUY: No recent MACD crossover (MACD: {macd_line:.6f}, Signal: {signal_line:.6f})")
                        return False

                    # Step 4: SECOND condition - Price must be above Supertrend (bullish)
                    price_above_supertrend = current_price > supertrend and trend_direction == 'bullish'

                    if not price_above_supertrend:
                        logger.debug(f"{symbol} MACD+Supertrend BUY: Price not above Supertrend (Price: ${current_price:.6f}, ST: ${supertrend:.6f}, Trend: {trend_direction})")
                        return False

                    # Step 5: Additional confirmations for quality

                    # Volume surge check
                    volume_surge = self._check_volume_surge(volumes, threshold=1.5)
                    if not volume_surge:
                        logger.debug(f"{symbol} MACD+Supertrend BUY: No volume surge detected")
                        return False

                    # RSI overbought filter
                    if rsi > 70:
                        logger.debug(f"{symbol} MACD+Supertrend BUY: RSI overbought ({rsi:.1f} > 70)")
                        return False

                    # ADX trend strength filter
                    if adx < 25:
                        logger.debug(f"{symbol} MACD+Supertrend BUY: ADX too weak (ADX: {adx:.1f} < 25, not trending)")
                        return False

                    # ALL CONDITIONS MET! This is a HIGH-QUALITY signal
                    logger.success(f"🚀 {symbol} MACD+SUPERTREND BUY SIGNAL!")
                    logger.success(f"   ✅ MACD crossed above signal")
                    logger.success(f"   ✅ Price above Supertrend (${current_price:.6f} > ${supertrend:.6f})")
                    logger.success(f"   ✅ Volume surge confirmed")
                    logger.success(f"   ✅ RSI healthy: {rsi:.1f}")
                    logger.success(f"   ✅ ADX strong trend: {adx:.1f}")

                    return True

                elif action_type == 'SELL':
                    # MACD+Supertrend strategy does NOT generate SELL signals
                    # Risk management (stop-loss/take-profit) handles all exits
                    # This is intentional - we want to let winners run with trailing stop
                    return False

        except Exception as e:
            logger.error(f"Error evaluating strategies for {symbol}: {e}")
            import traceback
            traceback.print_exc()

        return False

    def _calculate_std(self, prices):
        """Calculate standard deviation"""
        mean = sum(prices) / len(prices)
        variance = sum((x - mean) ** 2 for x in prices) / len(prices)
        return variance ** 0.5

    def _calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = prices[0]  # Start with first price

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def _calculate_macd(self, closes):
        """
        Calculate MACD (Moving Average Convergence Divergence)
        Returns: (macd_line, signal_line, histogram)
        Standard params: 12, 26, 9
        """
        if len(closes) < 26:
            return None, None, None

        # Calculate 12-period and 26-period EMAs
        ema_12 = []
        ema_26 = []

        # Calculate EMA for each point
        for i in range(26, len(closes) + 1):
            window = closes[i-26:i]
            ema_12.append(self._calculate_ema(window[-12:], 12))
            ema_26.append(self._calculate_ema(window, 26))

        # MACD line = EMA12 - EMA26
        macd_line = [ema_12[i] - ema_26[i] for i in range(len(ema_12))]

        # Signal line = 9-period EMA of MACD line
        if len(macd_line) < 9:
            return None, None, None

        signal_line = self._calculate_ema(macd_line[-9:], 9)

        # Histogram = MACD - Signal
        histogram = macd_line[-1] - signal_line if signal_line else 0

        return macd_line[-1], signal_line, histogram

    def _calculate_atr(self, highs, lows, closes, period=10):
        """Calculate Average True Range"""
        if len(highs) < period + 1:
            return None

        true_ranges = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            true_range = max(high_low, high_close, low_close)
            true_ranges.append(true_range)

        # Average of last 'period' true ranges
        atr = sum(true_ranges[-period:]) / period
        return atr

    def _calculate_supertrend(self, highs, lows, closes, period=10, multiplier=3):
        """
        Calculate Supertrend indicator
        Returns: (supertrend_value, trend_direction)
        trend_direction: 'bullish' or 'bearish'
        """
        if len(closes) < period + 1:
            return None, None

        # Calculate ATR
        atr = self._calculate_atr(highs, lows, closes, period)
        if not atr:
            return None, None

        # Calculate basic upper and lower bands
        hl_avg = (highs[-1] + lows[-1]) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)

        current_price = closes[-1]

        # Determine trend
        if current_price > upper_band:
            trend = 'bullish'
            supertrend = lower_band
        else:
            trend = 'bearish'
            supertrend = upper_band

        return supertrend, trend

    def _calculate_rsi(self, closes, period=14):
        """Calculate Relative Strength Index"""
        if len(closes) < period + 1:
            return None

        # Calculate price changes
        changes = [closes[i] - closes[i-1] for i in range(1, len(closes))]

        # Separate gains and losses
        gains = [change if change > 0 else 0 for change in changes[-period:]]
        losses = [-change if change < 0 else 0 for change in changes[-period:]]

        # Calculate average gain and loss
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_adx(self, highs, lows, closes, period=14):
        """
        Calculate Average Directional Index (trend strength)
        ADX > 25 = trending market
        ADX < 20 = ranging market
        """
        if len(closes) < period + 1:
            return None

        # Calculate +DM and -DM
        plus_dm = []
        minus_dm = []

        for i in range(1, len(highs)):
            high_diff = highs[i] - highs[i-1]
            low_diff = lows[i-1] - lows[i]

            if high_diff > low_diff and high_diff > 0:
                plus_dm.append(high_diff)
            else:
                plus_dm.append(0)

            if low_diff > high_diff and low_diff > 0:
                minus_dm.append(low_diff)
            else:
                minus_dm.append(0)

        # Calculate ATR
        atr = self._calculate_atr(highs, lows, closes, period)
        if not atr or atr == 0:
            return None

        # Calculate +DI and -DI
        plus_di = (sum(plus_dm[-period:]) / period) / atr * 100
        minus_di = (sum(minus_dm[-period:]) / period) / atr * 100

        # Calculate DX
        di_sum = plus_di + minus_di
        if di_sum == 0:
            return None

        dx = abs(plus_di - minus_di) / di_sum * 100

        # ADX is smoothed DX (simplified version)
        return dx

    def _check_volume_surge(self, volumes, threshold=1.5):
        """Check if current volume is above average"""
        if len(volumes) < 20:
            return False

        avg_volume = sum(volumes[-20:-1]) / 19  # Average of last 19 (excluding current)
        current_volume = volumes[-1]

        return current_volume > (avg_volume * threshold)

    def _check_macd_crossover(self, symbol, macd_line, signal_line, max_age_minutes=30):
        """
        Check if MACD crossed above signal line recently
        Stores crossover timestamp for tracking
        """
        # Initialize crossover tracking dict if needed
        if not hasattr(self, 'macd_crossovers'):
            self.macd_crossovers = {}

        # Check if MACD is above signal (bullish)
        if macd_line > signal_line:
            # If we don't have a crossover recorded, record it now
            if symbol not in self.macd_crossovers:
                self.macd_crossovers[symbol] = datetime.now()
                logger.info(f"🔔 {symbol} MACD BULLISH CROSSOVER detected! MACD: {macd_line:.6f} > Signal: {signal_line:.6f}")
                return True
            else:
                # Check if crossover is still valid (within time window)
                crossover_time = self.macd_crossovers[symbol]
                minutes_since = (datetime.now() - crossover_time).total_seconds() / 60

                if minutes_since <= max_age_minutes:
                    logger.debug(f"{symbol} MACD crossover still valid ({minutes_since:.1f} min ago)")
                    return True
                else:
                    # Crossover too old, remove it
                    logger.debug(f"{symbol} MACD crossover expired ({minutes_since:.1f} min ago)")
                    del self.macd_crossovers[symbol]
                    return False
        else:
            # MACD below signal, clear any crossover
            if symbol in self.macd_crossovers:
                del self.macd_crossovers[symbol]
            return False

    def _execute_buy(self, symbol, usd_amount, price, strategy='unknown'):
        """Execute a BUY order on Kraken"""
        try:
            # CRITICAL: Check minimum order value to prevent dust positions
            MIN_ORDER_VALUE = 1.0  # Kraken minimum is ~$1 USD

            if usd_amount < MIN_ORDER_VALUE:
                logger.warning(f"⚠️ Order value ${usd_amount:.6f} below Kraken minimum ${MIN_ORDER_VALUE}")
                logger.warning(f"Skipping BUY to avoid creating dust position")
                return

            # Calculate quantity to buy
            quantity = usd_amount / price

            logger.info(f"Executing BUY: {quantity:.8f} {symbol} for ${usd_amount:.2f} (Strategy: {strategy})")

            # Place market buy order
            order = self.exchange.create_market_buy_order(symbol, quantity)

            # Track position with strategy and trailing stop data
            self.positions[symbol] = {
                'entry_price': price,
                'quantity': quantity,
                'usd_invested': usd_amount,
                'entry_time': datetime.now().isoformat(),
                'order_id': order.get('id'),
                'strategy': strategy,
                'highest_price': price  # For trailing stop
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

    def _execute_sell_with_retry(self, symbol, price, reason, max_retries=5):
        """
        Execute a SELL order with retry mechanism - CRITICAL for risk management
        Will retry up to max_retries times to ensure the order executes
        """
        for attempt in range(max_retries):
            try:
                if symbol not in self.positions:
                    logger.warning(f"Position {symbol} already closed, skipping sell")
                    return

                position = self.positions[symbol]
                tracked_quantity = position['quantity']
                entry_price = position['entry_price']

                # CRITICAL: Fetch actual balance from Kraken before selling
                # This ensures we sell what we actually have, not what we think we have
                base_currency = symbol.split('/')[0]  # e.g., "PUMP" from "PUMP/USD"

                try:
                    balance = self.exchange.fetch_balance()
                    actual_quantity = float(balance.get(base_currency, {}).get('free', 0))

                    logger.info(f"Balance check - Tracked: {tracked_quantity:.8f}, Actual: {actual_quantity:.8f} {base_currency}")

                    # Use actual quantity if it's available
                    if actual_quantity > 0:
                        # Use the smaller of tracked vs actual (to be safe)
                        quantity = min(tracked_quantity, actual_quantity)

                        if actual_quantity < tracked_quantity * 0.99:  # More than 1% difference
                            logger.warning(f"⚠️ Balance mismatch! Tracked: {tracked_quantity:.8f}, Actual: {actual_quantity:.8f}")
                            logger.warning(f"Using actual balance: {actual_quantity:.8f} {base_currency}")
                            quantity = actual_quantity

                        # CRITICAL FIX: Check if position value meets Kraken minimum
                        position_value_usd = quantity * price
                        MIN_ORDER_VALUE = 1.0  # Kraken minimum is ~$1 USD

                        if position_value_usd < MIN_ORDER_VALUE:
                            logger.warning(f"⚠️ DUST POSITION DETECTED!")
                            logger.warning(f"Position value: ${position_value_usd:.6f} (minimum: ${MIN_ORDER_VALUE})")
                            logger.warning(f"Quantity: {quantity:.8f} {base_currency} at ${price:.6f}")
                            logger.warning(f"This position is too small to sell on Kraken (below minimum order size)")
                            logger.warning(f"Removing dust position from tracking...")

                            # Remove from tracking
                            del self.positions[symbol]
                            self.save_positions()

                            logger.info(f"✅ Dust position removed. No further action needed.")
                            return  # Exit successfully

                    else:
                        logger.error(f"❌ No {base_currency} balance found on Kraken!")
                        logger.error(f"Tracked quantity: {tracked_quantity:.8f}")
                        logger.error(f"This position may have been manually closed or the buy order didn't fill")
                        # Remove position from tracking since it doesn't exist
                        del self.positions[symbol]
                        self.save_positions()
                        return

                except Exception as balance_error:
                    logger.warning(f"Could not fetch balance: {balance_error}. Using tracked quantity.")
                    quantity = tracked_quantity

                # Calculate P&L
                pnl = (price - entry_price) * quantity
                pnl_percent = ((price - entry_price) / entry_price) * 100

                logger.info(f"[Attempt {attempt+1}/{max_retries}] Executing SELL: {quantity:.8f} {symbol} at ${price:.2f} ({reason})")

                # Place market sell order - THIS IS CRITICAL
                order = self.exchange.create_market_sell_order(symbol, quantity)

                # Verify order was created
                if not order or 'id' not in order:
                    raise Exception("Order creation returned invalid response")

                logger.success(f"✅ Order #{order.get('id')} created successfully")

                # Remove position from tracking
                del self.positions[symbol]

                # Log trade to history
                trade_record = {
                    'symbol': symbol,
                    'action': 'SELL',
                    'price': price,
                    'quantity': quantity,
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat(),
                    'order_id': order.get('id')
                }
                self.trades_history.append(trade_record)

                # CRITICAL: Save immediately to disk
                self.save_positions()
                self.save_trades()

                # Success logging
                profit_loss = "PROFIT" if pnl >= 0 else "LOSS"
                logger.success(f"✅✅✅ SELL ORDER EXECUTED SUCCESSFULLY ✅✅✅")
                logger.success(f"Symbol: {symbol}")
                logger.success(f"Quantity: {quantity:.8f}")
                logger.success(f"Entry Price: ${entry_price:.6f}")
                logger.success(f"Exit Price: ${price:.6f}")
                logger.success(f"{profit_loss}: ${pnl:.4f} ({pnl_percent:+.2f}%)")
                logger.success(f"Reason: {reason}")
                logger.success(f"Order ID: {order.get('id')}")

                return  # SUCCESS - exit function

            except Exception as e:
                logger.error(f"❌ Attempt {attempt+1}/{max_retries} failed to execute SELL for {symbol}: {e}")

                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 3  # Exponential backoff: 3s, 6s, 9s, 12s, 15s
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

                    # Try to get updated price for next attempt
                    try:
                        ticker = self.exchange.fetch_ticker(symbol)
                        price = ticker['last']
                        logger.info(f"Updated price for retry: ${price:.6f}")
                    except:
                        pass  # Use existing price if can't fetch
                else:
                    # CRITICAL FAILURE - all retries exhausted
                    logger.critical(f"🚨🚨🚨 CRITICAL: Failed to execute SELL for {symbol} after {max_retries} attempts!")
                    logger.critical(f"Manual intervention required! Check Kraken account and close position manually!")
                    logger.critical(f"Position data: {position}")

    def _execute_sell(self, symbol, price, reason):
        """Execute a SELL order on Kraken - wrapper that calls retry version"""
        self._execute_sell_with_retry(symbol, price, reason, max_retries=3)

    def _check_positions(self):
        """
        CRITICAL: Check all open positions for stop-loss/take-profit
        This is the MAIN risk management function - runs every 30 seconds
        """
        if not self.positions:
            logger.debug("No open positions to check")
            return

        logger.info(f"🔍 Checking {len(self.positions)} open position(s) for risk management...")

        for symbol in list(self.positions.keys()):
            try:
                position = self.positions[symbol]
                entry_price = position['entry_price']
                quantity = position['quantity']
                entry_time = position.get('entry_time', 'unknown')

                logger.debug(f"Checking {symbol}: Entry=${entry_price:.6f}, Qty={quantity:.4f}")

                # Fetch current price with retry mechanism
                current_price = None
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        ticker = self.exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Failed to fetch price for {symbol} (attempt {attempt+1}/{max_retries}): {e}")
                            time.sleep(2)
                        else:
                            raise

                if current_price is None or current_price <= 0:
                    logger.error(f"Invalid price for {symbol}: {current_price}")
                    continue

                # DUST POSITION CHECK - Auto-remove worthless positions
                position_value_usd = quantity * current_price
                MIN_POSITION_VALUE = 1.0  # $1 minimum

                if position_value_usd < MIN_POSITION_VALUE:
                    logger.warning(f"🗑️ DUST POSITION DETECTED: {symbol}")
                    logger.warning(f"   Position value: ${position_value_usd:.6f} (minimum: ${MIN_POSITION_VALUE:.2f})")
                    logger.warning(f"   Quantity: {quantity:.8f} at ${current_price:.6f}")
                    logger.warning(f"   This position is too small to trade - REMOVING from tracking")

                    # Remove dust position
                    del self.positions[symbol]
                    self.save_positions()

                    logger.success(f"✅ Dust position {symbol} removed automatically")
                    continue  # Skip to next position

                # Calculate P&L
                pnl = (current_price - entry_price) * quantity
                pnl_percent = ((current_price - entry_price) / entry_price) * 100

                # Calculate stop-loss and take-profit levels
                stop_loss_price = entry_price * (1 - self.stop_loss_percent / 100)
                take_profit_price = entry_price * (1 + self.take_profit_percent / 100)

                # TRAILING STOP LOGIC (for MACD+Supertrend strategy)
                strategy = position.get('strategy', 'unknown')
                if strategy == 'macd_supertrend':
                    # Update highest price reached
                    highest_price = position.get('highest_price', entry_price)
                    if current_price > highest_price:
                        highest_price = current_price
                        position['highest_price'] = highest_price
                        self.save_positions()  # Save updated highest price
                        logger.info(f"📈 {symbol} NEW HIGH: ${highest_price:.6f} (Entry: ${entry_price:.6f})")

                    # Calculate trailing stop (move stop-loss up as profit grows)
                    # If price is up 5% or more, move stop-loss to breakeven + 2%
                    # This locks in profit while letting winners run
                    profit_from_entry = ((highest_price - entry_price) / entry_price) * 100

                    if profit_from_entry >= 5.0:
                        # Price has gone up 5%+, activate trailing stop
                        # Set stop to 3% below highest price reached
                        trailing_stop_price = highest_price * 0.97  # 3% below high

                        # Make sure trailing stop is always better than entry
                        if trailing_stop_price > entry_price:
                            stop_loss_price = max(stop_loss_price, trailing_stop_price)
                            logger.info(f"🛡️ {symbol} TRAILING STOP ACTIVE: Stop moved to ${stop_loss_price:.6f} (3% below high ${highest_price:.6f})")

                logger.info(f"📊 {symbol} | Current: ${current_price:.6f} | P&L: ${pnl:.4f} ({pnl_percent:+.2f}%) | SL: ${stop_loss_price:.6f} | TP: ${take_profit_price:.6f}")

                # CRITICAL: Check stop-loss FIRST (risk protection is priority)
                # Now uses trailing stop if applicable
                if current_price <= stop_loss_price:
                    logger.warning(f"🚨🔴 STOP-LOSS TRIGGERED! 🔴🚨")
                    logger.warning(f"Symbol: {symbol}")
                    logger.warning(f"Entry: ${entry_price:.6f}")
                    logger.warning(f"Current: ${current_price:.6f}")
                    logger.warning(f"Loss: ${pnl:.4f} ({pnl_percent:.2f}%)")
                    logger.warning(f"Stop-Loss Level: {self.stop_loss_percent}%")
                    logger.warning(f"EXECUTING EMERGENCY SELL ORDER...")

                    # Execute sell with high priority
                    self._execute_sell_with_retry(symbol, current_price, "STOP_LOSS_AUTO")
                    continue

                # Check take-profit (lock in gains)
                elif pnl_percent >= self.take_profit_percent:
                    logger.info(f"🎉🟢 TAKE-PROFIT TRIGGERED! 🟢🎉")
                    logger.info(f"Symbol: {symbol}")
                    logger.info(f"Entry: ${entry_price:.6f}")
                    logger.info(f"Current: ${current_price:.6f}")
                    logger.info(f"Profit: ${pnl:.4f} ({pnl_percent:.2f}%)")
                    logger.info(f"Take-Profit Level: {self.take_profit_percent}%")
                    logger.info(f"EXECUTING PROFIT-TAKING SELL ORDER...")

                    # Execute sell to lock in profit
                    self._execute_sell_with_retry(symbol, current_price, "TAKE_PROFIT_AUTO")
                    continue

                else:
                    # Position is within acceptable range
                    logger.debug(f"✅ {symbol} within range: {pnl_percent:+.2f}% (Target: {self.take_profit_percent}%, Stop: -{self.stop_loss_percent}%)")

            except Exception as e:
                logger.error(f"❌ CRITICAL ERROR checking position for {symbol}: {e}", exc_info=True)
                # Don't let one position error stop checking others
                continue

    def get_positions(self):
        """Get current positions"""
        return self.positions

    def get_trades(self):
        """Get trade history"""
        return self.trades_history

    def _get_technical_indicators(self, closes, current_price):
        """
        Prepare technical indicators for AI analysis
        Returns a dict of technical indicators
        """
        try:
            indicators = {}

            # RSI
            if len(closes) >= 15:
                deltas = []
                for i in range(1, len(closes)):
                    deltas.append(closes[i] - closes[i-1])

                gains = [d if d > 0 else 0 for d in deltas]
                losses = [-d if d < 0 else 0 for d in deltas]

                avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0
                avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0

                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))

                indicators['rsi'] = rsi
            else:
                indicators['rsi'] = 50

            # MACD
            if len(closes) >= 26:
                # Calculate EMA 12
                ema_12 = closes[0]
                multiplier_12 = 2 / 13
                for price in closes[1:]:
                    ema_12 = (price - ema_12) * multiplier_12 + ema_12

                # Calculate EMA 26
                ema_26 = closes[0]
                multiplier_26 = 2 / 27
                for price in closes[1:]:
                    ema_26 = (price - ema_26) * multiplier_26 + ema_26

                macd = ema_12 - ema_26
                indicators['macd'] = macd
                indicators['macd_signal'] = 'BULLISH' if macd > 0 else 'BEARISH'
            else:
                indicators['macd'] = 0
                indicators['macd_signal'] = 'NEUTRAL'

            # Volume ratio (approximate - use recent average)
            indicators['volume_ratio'] = 1.0  # Default

            # ADX (simplified - trend strength)
            indicators['adx'] = 20  # Default moderate trend

            # Supertrend (simplified)
            indicators['supertrend'] = 'NEUTRAL'

            return indicators

        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return {
                'rsi': 50,
                'macd': 0,
                'macd_signal': 'NEUTRAL',
                'volume_ratio': 1.0,
                'adx': 20,
                'supertrend': 'NEUTRAL'
            }

    def test_risk_management(self):
        """
        Test the risk management system without real trades
        This simulates stop-loss and take-profit triggers
        """
        logger.info("=" * 80)
        logger.info("🧪 RISK MANAGEMENT TEST MODE")
        logger.info("=" * 80)

        if not self.positions:
            logger.warning("No positions to test. Create a test position first.")
            return

        for symbol, position in self.positions.items():
            entry_price = position['entry_price']
            quantity = position['quantity']

            logger.info(f"\nTesting {symbol}:")
            logger.info(f"  Entry Price: ${entry_price:.6f}")
            logger.info(f"  Quantity: {quantity:.8f}")
            logger.info(f"  Stop-Loss Threshold: -{self.stop_loss_percent}%")
            logger.info(f"  Take-Profit Threshold: +{self.take_profit_percent}%")

            # Calculate trigger prices
            stop_loss_price = entry_price * (1 - self.stop_loss_percent / 100)
            take_profit_price = entry_price * (1 + self.take_profit_percent / 100)

            logger.info(f"\n  📍 Trigger Prices:")
            logger.info(f"    Stop-Loss will trigger at: ${stop_loss_price:.6f}")
            logger.info(f"    Take-Profit will trigger at: ${take_profit_price:.6f}")

            # Simulate different price scenarios
            logger.info(f"\n  🎭 Simulated Scenarios:")

            # Scenario 1: Price drops to stop-loss
            test_price_sl = entry_price * 0.98  # -2%
            pnl_sl = (test_price_sl - entry_price) * quantity
            pnl_percent_sl = ((test_price_sl - entry_price) / entry_price) * 100
            logger.info(f"    1. Price drops to ${test_price_sl:.6f} ({pnl_percent_sl:.2f}%)")
            if pnl_percent_sl <= -self.stop_loss_percent:
                logger.warning(f"       🔴 STOP-LOSS WOULD TRIGGER! Loss: ${pnl_sl:.4f}")
            else:
                logger.info(f"       ✅ Within acceptable range")

            # Scenario 2: Price rises to take-profit
            test_price_tp = entry_price * 1.03  # +3%
            pnl_tp = (test_price_tp - entry_price) * quantity
            pnl_percent_tp = ((test_price_tp - entry_price) / entry_price) * 100
            logger.info(f"    2. Price rises to ${test_price_tp:.6f} ({pnl_percent_tp:.2f}%)")
            if pnl_percent_tp >= self.take_profit_percent:
                logger.success(f"       🟢 TAKE-PROFIT WOULD TRIGGER! Profit: ${pnl_tp:.4f}")
            else:
                logger.info(f"       ✅ Within acceptable range")

            # Scenario 3: Small movement
            test_price_neutral = entry_price * 1.005  # +0.5%
            pnl_neutral = (test_price_neutral - entry_price) * quantity
            pnl_percent_neutral = ((test_price_neutral - entry_price) / entry_price) * 100
            logger.info(f"    3. Price moves to ${test_price_neutral:.6f} ({pnl_percent_neutral:.2f}%)")
            logger.info(f"       ✅ Within acceptable range - no action taken")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Risk Management Test Complete")
        logger.info("   The system will automatically:")
        logger.info(f"   - SELL if price drops {self.stop_loss_percent}% (protect capital)")
        logger.info(f"   - SELL if price rises {self.take_profit_percent}% (lock in profit)")
        logger.info("   - Check every 30 seconds while bot is running")
        logger.info("=" * 80)
