"""
Real Trading Engine - Multi-Timeframe AI-Powered Trading
Supports: Scalping (5m), Day Trading (1h), Swing Trading (4h)
AI validates ALL trades across multiple timeframes
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

# TIER 3 & 4: Master Trader Advanced Modules
from trade_history import TradeHistory
from alerter import alerter
from deepseek_chain import DeepSeekChain
from deepseek_debate import DeepSeekDebate

# Multi-Timeframe Trading Components
from multi_timeframe_analyzer import MultiTimeframeAnalyzer
from signal_aggregator import SignalAggregator
from trading_config import (
    STRATEGY_CONFIGS,
    TRADING_LOOP_CONFIG,
    POSITION_RULES,
    AI_TIMEFRAME_ANALYSIS,
    get_strategy_config,
    get_enabled_strategies
)


def format_price(price: float) -> str:
    """
    Dynamically format price based on its magnitude to handle both high and low-priced tokens.

    Args:
        price: The price value to format

    Returns:
        Formatted price string with appropriate decimal places

    Examples:
        $1234.56 -> "$1234.56" (2 decimals)
        $12.3456 -> "$12.35" (2 decimals)
        $0.123456 -> "$0.1235" (4 decimals)
        $0.00123456 -> "$0.001235" (6 decimals)
        $0.00000123 -> "$0.0000012" (8 decimals)
    """
    if price == 0:
        return "$0.00"

    abs_price = abs(price)

    # For prices >= $1, use 2 decimals
    if abs_price >= 1:
        return f"${price:.2f}"
    # For prices >= $0.01, use 4 decimals
    elif abs_price >= 0.01:
        return f"${price:.4f}"
    # For prices >= $0.0001, use 6 decimals
    elif abs_price >= 0.0001:
        return f"${price:.6f}"
    # For very small prices (< $0.0001), use 8 decimals
    else:
        return f"${price:.8f}"


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

        # Initialize Multi-Timeframe Components
        self.mt_analyzer = MultiTimeframeAnalyzer(self.exchange)
        self.signal_aggregator = SignalAggregator(self.exchange)
        logger.info("✓ Multi-Timeframe Analyzer initialized")
        logger.info("✓ Signal Aggregator initialized")

        # ============================================
        # TIER 3 & 4: MASTER TRADER MODULES
        # ============================================
        # Performance tracking database
        self.trade_history = TradeHistory()
        logger.info("✓ Trade History Database initialized")

        # Advanced AI reasoning modules
        self.deepseek_chain = DeepSeekChain(api_key=deepseek_key)
        self.deepseek_debate = DeepSeekDebate(api_key=deepseek_key)
        logger.info("✓ Advanced AI Reasoning (Chain + Debate) initialized")

        # Telegram alerts
        logger.info("✓ Alerter system initialized")

        # AI reasoning mode selection
        # 'standard' = Fast ensemble (default)
        # 'chain' = 3-call chained reasoning (thorough)
        # 'debate' = Multi-agent debate (comprehensive)
        self.ai_reasoning_mode = os.getenv('AI_REASONING_MODE', 'standard').lower()
        logger.info(f"✓ AI Reasoning Mode: {self.ai_reasoning_mode.upper()}")

        # AI configuration
        self.ai_enabled = os.getenv('AI_ENSEMBLE_ENABLED', 'true').lower() == 'true'
        self.ai_min_confidence = float(os.getenv('AI_MIN_CONFIDENCE', '0.65'))

        logger.success("=" * 70)
        logger.success("✓ MULTI-TIMEFRAME TRADING ENGINE INITIALIZED")
        logger.success("=" * 70)

        # Show enabled trading strategies
        enabled_strats = get_enabled_strategies()
        logger.success(f"📊 ACTIVE TRADING STRATEGIES: {len(enabled_strats)}")
        for strat in enabled_strats:
            config = get_strategy_config(strat)
            logger.success(f"   ✓ {config['name']}")
            logger.success(f"      Timeframe: {config['timeframe']} | Check every: {config['check_interval']//60}min")
            logger.success(f"      Risk: {config['stop_loss_percent']}% SL / {config['take_profit_percent']}% TP")

        logger.success("")

        # CRITICAL: Log AI configuration prominently
        if self.ai_enabled:
            logger.success("🧠 AI ENSEMBLE: ENABLED ✅")
            logger.success("   ⚡ DeepSeek AI validates ALL trades across ALL timeframes")
            logger.success(f"   🎯 Minimum confidence threshold: {self.ai_min_confidence*100:.0f}%")
            if deepseek_key:
                logger.success("   🔑 DeepSeek API Key: CONFIGURED ✅")
                logger.success("   🚀 FULL AI MODE: Real-time reasoning with DeepSeek-R1")
            else:
                logger.warning("   ⚠️  DeepSeek API Key: NOT SET")
                logger.warning("   📊 DEMO MODE: Using fallback AI (Set DEEPSEEK_API_KEY for full power)")
        else:
            logger.critical("=" * 70)
            logger.critical("🚨 WARNING: AI ENSEMBLE DISABLED! 🚨")
            logger.critical("=" * 70)
            logger.critical("⚠️  Trading WITHOUT AI validation is EXTREMELY RISKY")
            logger.critical("⚠️  All trades will be BLOCKED until AI is enabled")
            logger.critical("⚠️  Set AI_ENSEMBLE_ENABLED=true in .env to enable protection")
            logger.critical("=" * 70)

        # Log AI health
        ai_health = self.ai_ensemble.get_model_health()
        logger.info("")
        logger.info(f"📊 AI Health Check: {ai_health['overall']}")
        logger.info(f"   Sentiment Model: {ai_health['sentiment']}")
        logger.info(f"   Technical Analysis: {ai_health['technical']}")
        logger.info(f"   Macro Analysis: {ai_health['macro']}")
        logger.info(f"   DeepSeek Validator: {ai_health['deepseek']}")
        logger.success("=" * 70)

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

        # CRITICAL: Test API connection before starting
        logger.info("🔑 Testing Kraken API connection...")
        try:
            test_balance = self.exchange.fetch_balance()
            usd_balance = test_balance.get('USD', {}).get('free', 0)
            logger.success(f"✅ API Connection successful! USD Balance: ${usd_balance:.2f}")
        except Exception as e:
            error_msg = str(e)
            logger.critical("=" * 70)
            logger.critical("🚨 CRITICAL ERROR: Cannot connect to Kraken API!")
            logger.critical("=" * 70)
            logger.critical(f"Error: {error_msg}")
            logger.critical("")
            logger.critical("POSSIBLE CAUSES:")
            logger.critical("1. API key expired or revoked")
            logger.critical("2. API key missing required permissions")
            logger.critical("3. Invalid API credentials")
            logger.critical("4. IP not whitelisted (if enabled)")
            logger.critical("")
            logger.critical("HOW TO FIX:")
            logger.critical("1. Go to: https://www.kraken.com/u/security/api")
            logger.critical("2. Generate NEW API key with these permissions:")
            logger.critical("   ✅ Query Funds")
            logger.critical("   ✅ Query Open Orders & Trades")
            logger.critical("   ✅ Query Closed Orders & Trades")
            logger.critical("   ✅ Create & Modify Orders")
            logger.critical("   ✅ Cancel/Close Orders")
            logger.critical("3. Update KRAKEN_API_KEY and KRAKEN_API_SECRET in .env")
            logger.critical("4. Restart the bot")
            logger.critical("=" * 70)
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

        # Send Telegram alert
        alerter.bot_started()

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

        try:
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

        except Exception as e:
            error_str = str(e)
            if "Invalid key" in error_str or "EAPI" in error_str:
                logger.critical(f"🚨 API AUTHENTICATION ERROR for {symbol}: {error_str}")
                logger.critical("Your Kraken API keys are invalid! Bot cannot trade.")
                logger.critical("Please generate new API keys and update .env file")
                # Don't crash, just skip this iteration
            else:
                logger.error(f"Error processing {symbol}: {e}")

    def _check_buy_signal(self, symbol, current_price, allocation, strategies):
        """Check if we should buy this pair"""

        # Get balance to see how much we can spend
        balance = self.exchange.fetch_balance()
        usd_available = balance.get('USD', {}).get('free', 0)

        logger.debug(f"💰 {symbol} - Checking BUY signal | Balance: ${usd_available:.2f} | Price: {format_price(current_price)}")

        if usd_available < 1:
            logger.warning(f"❌ {symbol}: Insufficient USD balance: ${usd_available:.2f}")
            return

        # Calculate how much to invest based on allocation
        max_investment = (usd_available * allocation / 100)

        # Don't exceed max order size
        investment = min(max_investment, self.max_order_size)

        logger.debug(f"💵 {symbol} - Max investment: ${max_investment:.2f} | Capped at: ${investment:.2f} (max order: ${self.max_order_size})")

        if investment < 1:
            logger.warning(f"❌ {symbol}: Investment too small: ${investment:.2f}")
            return

        # Check strategy signals
        logger.debug(f"📊 {symbol} - Evaluating strategies: {strategies}")
        signal = self._evaluate_strategies(symbol, current_price, strategies, 'BUY')

        if signal:
            logger.info(f"✅ {symbol} - STRATEGY SIGNAL DETECTED!")
            logger.info(f"🟢 STRATEGY SIGNAL: {symbol} at {format_price(current_price)}")

            # ============================================
            # MANDATORY AI VALIDATION - DeepSeek AI validates ALL trades
            # ============================================
            logger.info(f"🧠 AI Validation Status: {'ENABLED' if self.ai_enabled else 'DISABLED'}")

            if not self.ai_enabled:
                logger.critical("🚨 AI ENSEMBLE DISABLED - Trading without AI validation is extremely risky!")
                logger.critical("🚨 Set AI_ENSEMBLE_ENABLED=true in .env to enable AI protection")
                logger.warning("🛑 BLOCKING TRADE - AI validation is MANDATORY for safety")
                return  # Refuse to trade without AI

            try:
                logger.info(f"🧠 Consulting DeepSeek AI Ensemble for {symbol}...")

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
                highs = [c[2] for c in candles_data]
                lows = [c[3] for c in candles_data]
                technical_indicators = self._get_technical_indicators(closes, current_price)

                # PHASE 3: Calculate portfolio and volatility context for AI
                logger.debug("📊 Calculating portfolio context for AI...")
                portfolio_context = self._calculate_portfolio_context()

                logger.debug("📈 Calculating volatility metrics for AI...")
                volatility_metrics = self._calculate_volatility_metrics(symbol, highs, lows, closes)

                # Get AI signal using asyncio WITH FULL CONTEXT
                logger.debug("Creating asyncio event loop for AI analysis...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ai_result = loop.run_until_complete(
                    self.ai_ensemble.generate_signal(
                        symbol=symbol,
                        current_price=current_price,
                        candles=candles,
                        technical_indicators=technical_indicators,
                        portfolio_context=portfolio_context,
                        volatility_metrics=volatility_metrics
                    )
                )
                loop.close()

                ai_signal = ai_result['signal']
                ai_confidence = ai_result['confidence']
                ai_reasoning = ai_result['reasoning']

                # Extract AI's autonomous trading parameters
                ai_parameters = ai_result.get('parameters', {})
                position_size_percent = ai_parameters.get('position_size_percent', 10)
                stop_loss_percent = ai_parameters.get('stop_loss_percent', 2.0)
                take_profit_percent = ai_parameters.get('take_profit_percent', 3.5)
                risk_reward_ratio = ai_parameters.get('risk_reward_ratio', 1.75)

                logger.success(f"✅ DeepSeek AI Analysis Complete!")
                logger.info(f"🤖 AI Decision: {ai_signal} (confidence: {ai_confidence*100:.1f}%)")
                logger.info(f"💭 AI Reasoning: {ai_reasoning}")
                logger.info(f"🎯 AI Parameters: Position={position_size_percent:.1f}%, SL={stop_loss_percent:.2f}%, TP={take_profit_percent:.2f}%, R:R={risk_reward_ratio:.2f}")

                # Check if AI agrees with BUY
                if ai_signal != 'BUY':
                    logger.warning(f"⚠️ AI OVERRIDE: DeepSeek recommends {ai_signal}, CANCELLING BUY")
                    logger.warning(f"🛡️ AI is protecting your capital - trade blocked")
                    return

                # Check confidence threshold
                if ai_confidence < self.ai_min_confidence:
                    logger.warning(f"⚠️ AI CONFIDENCE TOO LOW: {ai_confidence*100:.1f}% < {self.ai_min_confidence*100:.1f}% threshold")
                    logger.warning(f"🛡️ Not confident enough - trade blocked for safety")
                    return

                logger.success(f"✅ AI APPROVED: {symbol} BUY signal validated by DeepSeek!")
                logger.success(f"🎯 Proceeding with trade execution...")

            except Exception as e:
                logger.error(f"❌ AI validation error: {e}")
                logger.critical("⚠️ AI VALIDATION FAILED - Cannot validate BUY signal safely")
                logger.warning("🛡️ BLOCKING TRADE for safety (AI ensemble is mandatory)")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return  # Don't trade if AI fails - safety first!

            # EXECUTE BUY ORDER (Only reached if AI approved)
            logger.info(f"🚀 EXECUTING AI-APPROVED BUY: {symbol} at {format_price(current_price)}")

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

            # PHASE 3: Pass AI's dynamic parameters to execution
            self._execute_buy(
                symbol=symbol,
                usd_amount=investment,
                price=current_price,
                strategy=strategy_name,
                ai_position_size_percent=position_size_percent,
                ai_stop_loss_percent=stop_loss_percent,
                ai_take_profit_percent=take_profit_percent,
                ai_risk_reward_ratio=risk_reward_ratio
            )

    def _check_sell_signal(self, symbol, current_price, strategies):
        """Check if we should sell this position - WITH AI VALIDATION"""
        position = self.positions[symbol]
        entry_price = position['entry_price']

        # Calculate P&L
        pnl_percent = ((current_price - entry_price) / entry_price) * 100

        # EMERGENCY STOP-LOSS - Execute immediately without AI (emergency exit)
        if pnl_percent <= -self.stop_loss_percent:
            logger.warning(f"🔴 EMERGENCY STOP LOSS triggered: {symbol} at {pnl_percent:.2f}%")
            self._execute_sell(symbol, current_price, "STOP_LOSS")
            return

        # For all other scenarios, consult AI FIRST before selling
        # This includes: take-profit, strategy signals, and profit protection

        # Check if we have profit to protect or if take-profit is near
        should_consider_selling = False
        sell_reason = None

        # Automatic take-profit hit
        if pnl_percent >= self.take_profit_percent:
            logger.info(f"🟢 TAKE PROFIT level reached: {symbol} at {pnl_percent:.2f}%")
            should_consider_selling = True
            sell_reason = "TAKE_PROFIT"

        # Profit protection - if we're up 2%+, AI should evaluate if we should lock it in
        elif pnl_percent >= 2.0:
            logger.info(f"💰 Profit protection: {symbol} up {pnl_percent:.2f}% - consulting AI")
            should_consider_selling = True
            sell_reason = "PROFIT_PROTECTION"

        # Check strategy sell signals
        else:
            signal = self._evaluate_strategies(symbol, current_price, strategies, 'SELL')
            if signal:
                logger.info(f"🟡 STRATEGY SELL SIGNAL: {symbol} at {format_price(current_price)} (P&L: {pnl_percent:.2f}%)")
                should_consider_selling = True
                sell_reason = "STRATEGY"

        # ============================================
        # MANDATORY AI VALIDATION FOR SELL DECISIONS
        # ============================================
        if should_consider_selling:
            logger.info(f"🧠 AI Validation Status: {'ENABLED' if self.ai_enabled else 'DISABLED'}")

            if not self.ai_enabled:
                logger.critical("🚨 AI ENSEMBLE DISABLED - Cannot validate SELL decision!")
                logger.warning("🛑 BLOCKING SELL - AI validation required (set AI_ENSEMBLE_ENABLED=true)")
                return  # Don't sell without AI validation

            try:
                logger.info(f"🧠 Consulting DeepSeek AI for SELL decision on {symbol}...")
                logger.info(f"   Current P&L: {pnl_percent:+.2f}% | Reason: {sell_reason}")

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

                # Add position context for AI
                technical_indicators['position_pnl'] = pnl_percent
                technical_indicators['entry_price'] = entry_price
                technical_indicators['hold_time'] = position.get('entry_time', 'unknown')

                # Get AI signal using asyncio
                logger.debug("Creating asyncio event loop for AI SELL analysis...")
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

                logger.success(f"✅ DeepSeek AI SELL Analysis Complete!")
                logger.info(f"🤖 AI Decision: {ai_signal} (confidence: {ai_confidence*100:.1f}%)")
                logger.info(f"💭 AI Reasoning: {ai_reasoning}")

                # AI can recommend SELL (take profits) or HOLD (let it run)
                if ai_signal == 'SELL' and ai_confidence >= self.ai_min_confidence:
                    logger.success(f"✅ AI APPROVED SELL: {symbol} - Taking profits at {pnl_percent:+.2f}%")
                    logger.success(f"🎯 DeepSeek validated: Time to lock in gains")
                    self._execute_sell(symbol, current_price, sell_reason)
                    return
                elif ai_signal == 'HOLD':
                    logger.info(f"🤚 AI RECOMMENDS HOLD: DeepSeek says let {symbol} run longer")
                    logger.info(f"💎 Current P&L: {pnl_percent:+.2f}% - Holding for more gains")
                    return
                elif ai_signal == 'BUY':
                    logger.info(f"📈 AI RECOMMENDS HOLD: DeepSeek sees more upside potential")
                    logger.info(f"💎 Current P&L: {pnl_percent:+.2f}% - Not selling yet")
                    return
                else:
                    logger.warning(f"⚠️ AI confidence too low: {ai_confidence*100:.1f}% < {self.ai_min_confidence*100:.1f}%")
                    logger.warning(f"🤚 Defaulting to HOLD for safety")
                    return

            except Exception as e:
                logger.error(f"❌ AI SELL validation error: {e}")
                logger.critical("⚠️ AI VALIDATION FAILED - Cannot validate SELL decision safely")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")

                # Emergency fallback: Only execute if TAKE_PROFIT (to lock in profits)
                if sell_reason == "TAKE_PROFIT" and pnl_percent >= self.take_profit_percent:
                    logger.warning("⚠️ AI failed but TAKE_PROFIT hit - executing sell as fallback")
                    self._execute_sell(symbol, current_price, sell_reason)
                else:
                    logger.warning("🛡️ AI failed - BLOCKING SELL for safety (defaulting to HOLD)")
                    return

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
                    # Buy if short MA is above long MA (uptrend)
                    # ULTRA-AGGRESSIVE: LOWERED from 0.3% to 0.15% to catch MORE opportunities
                    # This allows catching earlier uptrends for better entry prices
                    sma_diff_percent = ((sma_5 - sma_20) / sma_20) * 100

                    if sma_5 > sma_20 and current_price > sma_5 and sma_diff_percent >= 0.15:
                        logger.info(f"{symbol} 🎯 MOMENTUM BUY SIGNAL: Price {format_price(current_price)} > SMA5 {format_price(sma_5)} > SMA20 {format_price(sma_20)} (Gap: {sma_diff_percent:.2f}%)")
                        return True
                    else:
                        logger.debug(f"{symbol} Momentum BUY: SMA5/SMA20 gap: {sma_diff_percent:.2f}% (need 0.15%+)")

                elif action_type == 'SELL':
                    # CRITICAL FIX: Only sell if momentum has CLEARLY reversed
                    # Require SMA5 to be at least 0.3% BELOW SMA20 (not just any amount)
                    # This prevents immediate sell-offs from small dips
                    sma_diff_percent = ((sma_5 - sma_20) / sma_20) * 100

                    # Reduced minimum hold time from 15 to 8 minutes for faster exits
                    if symbol in self.positions:
                        entry_time_str = self.positions[symbol].get('entry_time', '')
                        if entry_time_str:
                            from datetime import datetime
                            entry_time = datetime.fromisoformat(entry_time_str)
                            hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

                            if hold_minutes < 8:
                                logger.debug(f"{symbol} Momentum SELL: Too soon! Hold time: {hold_minutes:.1f} min (need 8 min)")
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

                # Calculate RSI for additional signal confirmation
                rsi = self._calculate_rsi(closes)

                if action_type == 'BUY':
                    # ULTRA-AGGRESSIVE MEAN REVERSION: Buy on MULTIPLE conditions:
                    # 1. Price below lower Bollinger Band (oversold), OR
                    # 2. RSI < 40 AND price within 1.5% of lower band (approaching oversold), OR
                    # 3. RSI < 30 (extreme oversold regardless of band position)
                    near_lower_band = current_price < lower_band * 1.015  # Within 1.5% of lower band (more lenient)

                    if current_price < lower_band or (rsi < 30):
                        deviation = ((current_price - lower_band) / lower_band) * 100
                        logger.info(f"{symbol} Mean Reversion BUY: Price {format_price(current_price)} < Lower Band {format_price(lower_band)} (Deviation: {deviation:.2f}%, RSI: {rsi:.1f})")
                        return True
                    elif rsi < 35 and near_lower_band:
                        logger.info(f"{symbol} Mean Reversion BUY: RSI oversold ({rsi:.1f}) + near lower band {format_price(lower_band)}")
                        return True
                    else:
                        logger.debug(f"{symbol} Mean Reversion BUY: Not oversold. Price: {format_price(current_price)}, Lower Band: {format_price(lower_band)}, RSI: {rsi:.1f}")

                elif action_type == 'SELL':
                    # CRITICAL FIX: Sell when price returns to middle or above
                    # Don't wait for upper band - that's too extreme!
                    if symbol in self.positions:
                        entry_price = self.positions[symbol]['entry_price']

                        # Reduced minimum hold time from 10 to 5 minutes for faster exits
                        entry_time_str = self.positions[symbol].get('entry_time', '')
                        if entry_time_str:
                            from datetime import datetime
                            entry_time = datetime.fromisoformat(entry_time_str)
                            hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

                            if hold_minutes < 5:
                                logger.debug(f"{symbol} Mean Reversion SELL: Too soon! Hold time: {hold_minutes:.1f} min (need 5 min)")
                                return False

                        # Calculate profit
                        profit_percent = ((current_price - entry_price) / entry_price) * 100

                        # SELL if any of these conditions:
                        # 1. Price reached middle band AND profit >= 1.5%
                        # 2. Price reached upper band (extreme overbought)
                        # 3. Profit >= 2.5% (good profit regardless of bands)

                        if current_price >= middle_band and profit_percent >= 1.5:
                            logger.info(f"{symbol} Mean Reversion SELL: Price returned to middle - {format_price(current_price)} >= {format_price(middle_band)}, Profit: {profit_percent:.2f}%")
                            return True
                        elif current_price > upper_band:
                            logger.info(f"{symbol} Mean Reversion SELL: Extreme overbought - Price {format_price(current_price)} > Upper Band {format_price(upper_band)}, Profit: {profit_percent:.2f}%")
                            return True
                        elif profit_percent >= 2.5:
                            logger.info(f"{symbol} Mean Reversion SELL: Good profit target reached - {profit_percent:.2f}%")
                            return True
                        else:
                            logger.debug(f"{symbol} Mean Reversion SELL: Waiting for reversion. Price: {format_price(current_price)}, Middle: {format_price(middle_band)}, Profit: {profit_percent:.2f}%")
                            return False

            if 'scalping' in strategies:
                # Scalping: quick small profits on micro-dips
                # OPTIMIZED: Lower threshold for more opportunities
                sma_10 = sum(closes[-10:]) / 10

                if action_type == 'BUY':
                    # IMPROVED: Reduced from 1.5% to 0.8% for true scalping
                    # 0.8% dips happen frequently and provide quick bounce opportunities
                    if current_price < sma_10 * 0.992:  # 0.8% below 10-period average
                        logger.info(f"{symbol} Scalping BUY: Price {format_price(current_price)} dipped 0.8%+ below SMA10 {format_price(sma_10)}")
                        return True
                    else:
                        logger.debug(f"{symbol} Scalping BUY: Dip not significant enough (need 0.8% below SMA10)")

                elif action_type == 'SELL':
                    # OPTIMIZED: Reduced from 2% to 1.2% for faster profit-taking
                    # 1.2% provides decent profit after 0.32% fees while exiting quickly
                    if symbol in self.positions:
                        entry = self.positions[symbol]['entry_price']

                        # Reduced minimum hold time from 10 to 3 minutes for quick scalps
                        entry_time_str = self.positions[symbol].get('entry_time', '')
                        if entry_time_str:
                            from datetime import datetime
                            entry_time = datetime.fromisoformat(entry_time_str)
                            hold_minutes = (datetime.now() - entry_time).total_seconds() / 60

                            if hold_minutes < 3:
                                logger.debug(f"{symbol} Scalping SELL: Too soon! Hold time: {hold_minutes:.1f} min (need 3 min)")
                                return False

                        if current_price > entry * 1.012:  # 1.2% profit target (was 2%)
                            pnl_percent = ((current_price - entry) / entry) * 100
                            logger.info(f"{symbol} Scalping SELL: 1.2% profit target reached (P&L: {pnl_percent:.2f}%)")
                            return True
                        else:
                            logger.debug(f"{symbol} Scalping SELL: Not at 1.2% profit yet")

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
                        logger.debug(f"{symbol} MACD+Supertrend BUY: No recent MACD crossover (MACD: {macd_line:.8f}, Signal: {signal_line:.8f})")
                        return False

                    # Step 4: SECOND condition - Price must be above Supertrend (bullish)
                    price_above_supertrend = current_price > supertrend and trend_direction == 'bullish'

                    if not price_above_supertrend:
                        logger.debug(f"{symbol} MACD+Supertrend BUY: Price not above Supertrend (Price: {format_price(current_price)}, ST: {format_price(supertrend)}, Trend: {trend_direction})")
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
                    logger.success(f"   ✅ Price above Supertrend ({format_price(current_price)} > {format_price(supertrend)})")
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
                logger.info(f"🔔 {symbol} MACD BULLISH CROSSOVER detected! MACD: {macd_line:.8f} > Signal: {signal_line:.8f}")
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

    def _execute_buy(self, symbol, usd_amount, price, strategy='unknown',
                     ai_position_size_percent=None, ai_stop_loss_percent=None,
                     ai_take_profit_percent=None, ai_risk_reward_ratio=None):
        """Execute a BUY order on Kraken with AI-determined parameters"""
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

            # Log AI autonomous parameters if provided
            if ai_position_size_percent is not None:
                logger.info(f"🤖 AI Autonomous Parameters: Position={ai_position_size_percent:.1f}%, SL={ai_stop_loss_percent:.2f}%, TP={ai_take_profit_percent:.2f}%, R:R={ai_risk_reward_ratio:.2f}")

            # Place market buy order
            order = self.exchange.create_market_buy_order(symbol, quantity)

            # Track position with strategy, trailing stop data, AND AI parameters
            self.positions[symbol] = {
                'entry_price': price,
                'quantity': quantity,
                'usd_invested': usd_amount,
                'entry_time': datetime.now().isoformat(),
                'order_id': order.get('id'),
                'strategy': strategy,
                'highest_price': price,  # For trailing stop
                # PHASE 3: Store AI's autonomous trading parameters
                'ai_position_size_percent': ai_position_size_percent,
                'ai_stop_loss_percent': ai_stop_loss_percent,
                'ai_take_profit_percent': ai_take_profit_percent,
                'ai_risk_reward_ratio': ai_risk_reward_ratio
            }

            # TIER 4: Record trade entry in performance database
            ai_result = {
                'confidence': ai_position_size_percent or 60,  # Default if not provided
                'reasoning': strategy,
                'parameters': {
                    'position_size_percent': ai_position_size_percent or 10,
                    'stop_loss_percent': ai_stop_loss_percent or 2.0,
                    'take_profit_percent': ai_take_profit_percent or 3.5
                }
            }
            trade_id = self.trade_history.record_entry(
                symbol=symbol,
                strategy=strategy,
                entry_price=price,
                quantity=quantity,
                ai_result=ai_result
            )
            # Store trade_id for later exit recording
            self.positions[symbol]['trade_id'] = trade_id

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

            # TIER 4: Send Telegram alert
            alerter.buy_executed(
                symbol=symbol,
                price=price,
                quantity=quantity,
                usd_amount=usd_amount,
                ai_confidence=ai_position_size_percent or 60,
                strategy=strategy
            )

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
                            logger.warning(f"Quantity: {quantity:.8f} {base_currency} at {format_price(price)}")
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

                # TIER 4: Record trade exit in performance database
                trade_id = position.get('trade_id')
                if trade_id:
                    outcome = 'WIN' if pnl > 0 else 'LOSS'
                    self.trade_history.record_exit(
                        trade_id=trade_id,
                        exit_price=price,
                        exit_reason=reason
                    )
                    # Record outcome for ensemble weight optimization
                    self.ai_ensemble.record_trade_outcome(outcome)

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

                # TIER 4: Send Telegram alert
                alerter.sell_executed(
                    symbol=symbol,
                    price=price,
                    quantity=quantity,
                    pnl_usd=pnl,
                    pnl_percent=pnl_percent,
                    reason=reason
                )

                # Success logging
                profit_loss = "PROFIT" if pnl >= 0 else "LOSS"
                logger.success(f"✅✅✅ SELL ORDER EXECUTED SUCCESSFULLY ✅✅✅")
                logger.success(f"Symbol: {symbol}")
                logger.success(f"Quantity: {quantity:.8f}")
                logger.success(f"Entry Price: {format_price(entry_price)}")
                logger.success(f"Exit Price: {format_price(price)}")
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

                logger.debug(f"Checking {symbol}: Entry={format_price(entry_price)}, Qty={quantity:.4f}")

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
                    logger.warning(f"   Quantity: {quantity:.8f} at {format_price(current_price)}")
                    logger.warning(f"   This position is too small to trade - REMOVING from tracking")

                    # Remove dust position
                    del self.positions[symbol]
                    self.save_positions()

                    logger.success(f"✅ Dust position {symbol} removed automatically")
                    continue  # Skip to next position

                # Calculate P&L
                pnl = (current_price - entry_price) * quantity
                pnl_percent = ((current_price - entry_price) / entry_price) * 100

                # PHASE 3: Use AI-determined parameters if available, otherwise use defaults
                ai_stop_loss = position.get('ai_stop_loss_percent')
                ai_take_profit = position.get('ai_take_profit_percent')

                # Use AI parameters if they exist, otherwise fall back to class defaults
                stop_loss_percent = ai_stop_loss if ai_stop_loss is not None else self.stop_loss_percent
                take_profit_percent = ai_take_profit if ai_take_profit is not None else self.take_profit_percent

                # Log which parameters we're using
                if ai_stop_loss is not None:
                    logger.debug(f"🤖 {symbol} using AI parameters: SL={stop_loss_percent:.2f}%, TP={take_profit_percent:.2f}%")

                # Calculate stop-loss and take-profit levels
                stop_loss_price = entry_price * (1 - stop_loss_percent / 100)
                take_profit_price = entry_price * (1 + take_profit_percent / 100)

                # TRAILING STOP LOGIC (for MACD+Supertrend strategy)
                strategy = position.get('strategy', 'unknown')
                if strategy == 'macd_supertrend':
                    # Update highest price reached
                    highest_price = position.get('highest_price', entry_price)
                    if current_price > highest_price:
                        highest_price = current_price
                        position['highest_price'] = highest_price
                        self.save_positions()  # Save updated highest price
                        logger.info(f"📈 {symbol} NEW HIGH: {format_price(highest_price)} (Entry: {format_price(entry_price)})")

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
                            logger.info(f"🛡️ {symbol} TRAILING STOP ACTIVE: Stop moved to {format_price(stop_loss_price)} (3% below high {format_price(highest_price)})")

                logger.info(f"📊 {symbol} | Current: {format_price(current_price)} | P&L: ${pnl:.4f} ({pnl_percent:+.2f}%) | SL: {format_price(stop_loss_price)} | TP: {format_price(take_profit_price)}")

                # CRITICAL: Check stop-loss FIRST (risk protection is priority)
                # Now uses trailing stop if applicable AND AI-determined stop-loss levels
                if current_price <= stop_loss_price:
                    logger.warning(f"🚨🔴 STOP-LOSS TRIGGERED! 🔴🚨")
                    logger.warning(f"Symbol: {symbol}")
                    logger.warning(f"Entry: {format_price(entry_price)}")
                    logger.warning(f"Current: {format_price(current_price)}")
                    logger.warning(f"Loss: ${pnl:.4f} ({pnl_percent:.2f}%)")
                    logger.warning(f"Stop-Loss Level: {stop_loss_percent:.2f}% {'(AI-set)' if ai_stop_loss is not None else '(default)'}")
                    logger.warning(f"EXECUTING EMERGENCY SELL ORDER...")

                    # Execute sell with high priority
                    self._execute_sell_with_retry(symbol, current_price, "STOP_LOSS_AUTO")
                    continue

                # Check take-profit (lock in gains) with AI-determined levels
                elif pnl_percent >= take_profit_percent:
                    logger.info(f"🎉🟢 TAKE-PROFIT TRIGGERED! 🟢🎉")
                    logger.info(f"Symbol: {symbol}")
                    logger.info(f"Entry: {format_price(entry_price)}")
                    logger.info(f"Current: {format_price(current_price)}")
                    logger.info(f"Profit: ${pnl:.4f} ({pnl_percent:.2f}%)")
                    logger.info(f"Take-Profit Level: {take_profit_percent:.2f}% {'(AI-set)' if ai_take_profit is not None else '(default)'}")
                    logger.info(f"EXECUTING PROFIT-TAKING SELL ORDER...")

                    # Execute sell to lock in profit
                    self._execute_sell_with_retry(symbol, current_price, "TAKE_PROFIT_AUTO")
                    continue

                else:
                    # Position is within acceptable range
                    logger.debug(f"✅ {symbol} within range: {pnl_percent:+.2f}% (Target: {take_profit_percent:.2f}%, Stop: -{stop_loss_percent:.2f}%)")

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

    # ============================================
    # AI MASTER TRADER - Portfolio & Risk Context
    # ============================================

    def _calculate_portfolio_context(self):
        """
        Calculate current portfolio state for AI decision-making
        Provides DeepSeek with full portfolio awareness
        """
        try:
            # Count positions by strategy
            strategy_breakdown = {}
            total_exposure_usd = 0
            position_list = []

            for symbol, position in self.positions.items():
                strategy = position.get('strategy', 'unknown')
                strategy_breakdown[strategy] = strategy_breakdown.get(strategy, 0) + 1
                position_list.append(symbol)

                # Calculate current exposure
                try:
                    ticker = self.exchange.fetch_ticker(symbol)
                    current_price = ticker['last']
                    quantity = position['quantity']
                    total_exposure_usd += quantity * current_price
                except Exception as e:
                    logger.debug(f"Could not fetch price for {symbol} in portfolio calc: {e}")

            # Calculate today's P&L from trade history
            today_str = datetime.now().strftime('%Y-%m-%d')
            daily_pnl = 0

            for trade in self.trades_history:
                exit_time = trade.get('exit_time', '')
                if exit_time.startswith(today_str):
                    daily_pnl += trade.get('pnl', 0)

            # Get max positions from config
            from trading_config import POSITION_RULES
            max_positions = POSITION_RULES.get('max_total_positions', 10)

            portfolio_context = {
                'total_positions': len(self.positions),
                'max_positions': max_positions,
                'positions': position_list,
                'daily_pnl': daily_pnl,
                'total_exposure_usd': total_exposure_usd,
                'strategy_breakdown': strategy_breakdown
            }

            logger.debug(f"📊 Portfolio Context: {len(self.positions)}/{max_positions} positions, ${total_exposure_usd:.2f} exposure, P&L: ${daily_pnl:.2f}")

            return portfolio_context

        except Exception as e:
            logger.error(f"Error calculating portfolio context: {e}")
            return {
                'total_positions': 0,
                'max_positions': 10,
                'positions': [],
                'daily_pnl': 0,
                'total_exposure_usd': 0,
                'strategy_breakdown': {}
            }

    def _calculate_volatility_metrics(self, symbol, highs, lows, closes):
        """
        Calculate volatility metrics for risk adjustment
        Helps DeepSeek adapt position sizing and stops to market conditions
        """
        try:
            if len(closes) < 15:
                return {
                    'atr': 0,
                    'atr_percent': 0,
                    'regime': 'UNKNOWN',
                    'avg_daily_range': 0
                }

            # Calculate ATR (14-period) using proper True Range calculation
            atr = self._calculate_atr(highs, lows, closes, period=14)
            if atr is None:
                atr = 0
            current_price = closes[-1]
            atr_percent = (atr / current_price) * 100 if current_price > 0 and atr > 0 else 0

            # Determine volatility regime
            if atr_percent > 5.0:
                regime = 'HIGH'
            elif atr_percent < 2.0:
                regime = 'LOW'
            else:
                regime = 'NORMAL'

            # Calculate average daily range (last 20 periods)
            daily_ranges = []
            for i in range(1, min(21, len(closes))):
                range_pct = abs((closes[-i] - closes[-i-1]) / closes[-i-1]) * 100 if closes[-i-1] > 0 else 0
                daily_ranges.append(range_pct)

            avg_daily_range = sum(daily_ranges) / len(daily_ranges) if daily_ranges else 0

            volatility_metrics = {
                'atr': atr,
                'atr_percent': atr_percent,
                'regime': regime,
                'avg_daily_range': avg_daily_range
            }

            logger.debug(f"📈 Volatility: ATR {atr_percent:.2f}% ({regime}), Avg Range: {avg_daily_range:.2f}%")

            return volatility_metrics

        except Exception as e:
            logger.error(f"Error calculating volatility metrics: {e}")
            return {
                'atr': 0,
                'atr_percent': 0,
                'regime': 'UNKNOWN',
                'avg_daily_range': 0
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
