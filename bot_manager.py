"""
Bot Manager - Controls the trading bot lifecycle
"""
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

import config
from kraken_client import KrakenClient
from risk_manager import RiskManager
from database import db_manager, BotStatus, Trade, Position, Alert


class BotManager:
    """Central bot management and control system"""

    def __init__(self, kraken_client: KrakenClient, strategy_manager, risk_manager: RiskManager, alert_manager):
        self.kraken_client = kraken_client
        self.strategy_manager = strategy_manager
        self.risk_manager = risk_manager
        self.alert_manager = alert_manager

        # Bot State
        self.is_running = False
        self.session_id = None
        self.start_time = None
        self.trading_thread = None
        self.monitoring_thread = None
        self.executor = ThreadPoolExecutor(max_workers=5)

        # Configuration
        self.enabled_strategies = []
        self.trading_pairs = []
        self.max_positions = 5
        self.update_interval = config.STRATEGY_RUN_INTERVAL

        # Performance Tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.positions = {}

        # Safety Flags
        self.emergency_stop = False
        self.pause_trading = False

        logger.info("Bot Manager initialized")

    # ====================
    # LIFECYCLE MANAGEMENT
    # ====================

    def start(self, strategies: List[str] = None, trading_pairs: List[str] = None,
             max_positions: int = 5) -> bool:
        """Start the trading bot"""
        try:
            if self.is_running:
                logger.warning("Bot is already running")
                return False

            # Initialize session
            self.session_id = str(uuid.uuid4())
            self.start_time = datetime.utcnow()

            # Configure bot
            self.enabled_strategies = strategies or config.ENABLED_STRATEGIES
            self.trading_pairs = trading_pairs or config.TRADING_PAIRS
            self.max_positions = max_positions

            # Validate configuration
            if not self._validate_configuration():
                return False

            # Initialize components
            self._initialize_components()

            # Start trading threads
            self.is_running = True
            self.emergency_stop = False

            # Main trading loop
            self.trading_thread = threading.Thread(
                target=self._trading_loop,
                daemon=True,
                name="TradingLoop"
            )
            self.trading_thread.start()

            # Monitoring loop
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MonitoringLoop"
            )
            self.monitoring_thread.start()

            # Record bot status
            self._update_bot_status('started')

            # Send alert
            self.alert_manager.send_alert(
                title="Bot Started",
                message=f"Trading bot started with {len(self.enabled_strategies)} strategies",
                level="info"
            )

            logger.info(f"Bot started successfully - Session: {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            self.is_running = False
            return False

    def stop(self, close_positions: bool = False, cancel_orders: bool = True) -> bool:
        """Stop the trading bot"""
        try:
            if not self.is_running:
                logger.warning("Bot is not running")
                return False

            logger.info("Stopping bot...")
            self.is_running = False

            # Cancel pending orders
            if cancel_orders:
                self._cancel_all_orders()

            # Close open positions if requested
            if close_positions:
                self._close_all_positions()

            # Wait for threads to finish
            if self.trading_thread and self.trading_thread.is_alive():
                self.trading_thread.join(timeout=5)

            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)

            # Update bot status
            self._update_bot_status('stopped')

            # Send alert
            self.alert_manager.send_alert(
                title="Bot Stopped",
                message="Trading bot stopped successfully",
                level="warning"
            )

            logger.info("Bot stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
            return False

    def emergency_stop(self) -> bool:
        """Emergency stop - close all positions immediately"""
        try:
            logger.warning("EMERGENCY STOP TRIGGERED")
            self.emergency_stop = True
            self.is_running = False

            # Close all positions immediately
            self._close_all_positions(emergency=True)

            # Cancel all orders
            self._cancel_all_orders()

            # Send critical alert
            self.alert_manager.send_alert(
                title="EMERGENCY STOP",
                message="Emergency stop executed - all positions closed",
                level="critical"
            )

            return True

        except Exception as e:
            logger.error(f"Emergency stop error: {e}")
            return False

    def pause(self) -> bool:
        """Pause trading without stopping the bot"""
        self.pause_trading = True
        logger.info("Trading paused")
        return True

    def resume(self) -> bool:
        """Resume trading"""
        self.pause_trading = False
        logger.info("Trading resumed")
        return True

    # ====================
    # MAIN TRADING LOOP
    # ====================

    def _trading_loop(self):
        """Main trading loop"""
        logger.info("Trading loop started")

        while self.is_running and not self.emergency_stop:
            try:
                if not self.pause_trading:
                    # Run strategy analysis
                    self._run_strategies()

                    # Check risk limits
                    self._check_risk_limits()

                    # Update positions
                    self._update_positions()

                    # Process pending signals
                    self._process_signals()

                # Sleep before next iteration
                time.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Trading loop error: {e}")
                self._handle_trading_error(e)

        logger.info("Trading loop stopped")

    def _run_strategies(self):
        """Run all enabled strategies"""
        try:
            for symbol in self.trading_pairs:
                # Skip if max positions reached
                if len(self.positions) >= self.max_positions:
                    break

                # Get market data
                df = self.kraken_client.get_ohlcv(symbol, config.DEFAULT_TIMEFRAME, limit=500)

                if df is None or df.empty:
                    continue

                # Run each strategy
                for strategy_name in self.enabled_strategies:
                    if strategy_name in self.strategy_manager.strategies:
                        strategy = self.strategy_manager.strategies[strategy_name]

                        # Analyze market
                        signal = strategy.analyze(symbol, df)

                        if signal:
                            # Validate with risk manager
                            if self.risk_manager.validate_signal(signal):
                                # Execute signal
                                self._execute_signal(signal)
                            else:
                                logger.warning(f"Signal rejected by risk manager: {signal}")

        except Exception as e:
            logger.error(f"Error running strategies: {e}")

    def _execute_signal(self, signal: Dict) -> bool:
        """Execute a trading signal"""
        try:
            symbol = signal['symbol']
            action = signal['action']
            quantity = signal.get('quantity', 0)

            # Calculate position size if not provided
            if quantity == 0:
                quantity = self.risk_manager.calculate_position_size(
                    symbol=symbol,
                    signal_strength=signal.get('strength', 0.5)
                )

            # Check if we can open position
            can_trade, reason = self.risk_manager.can_open_position(symbol, quantity)
            if not can_trade:
                logger.warning(f"Cannot execute signal: {reason}")
                return False

            # Place order
            order = self.kraken_client.place_order(
                symbol=symbol,
                side=action,
                order_type='MARKET',
                amount=quantity,
                stop_price=signal.get('stop_loss'),
            )

            if order:
                # Record trade
                trade_data = {
                    'order_id': order['id'],
                    'symbol': symbol,
                    'side': action,
                    'order_type': 'MARKET',
                    'price': order.get('price', 0),
                    'quantity': quantity,
                    'cost': order.get('price', 0) * quantity,
                    'strategy': signal.get('strategy'),
                    'strategy_signal': signal,
                    'status': 'filled',
                    'is_paper': config.PAPER_TRADING
                }

                db_manager.record_trade(trade_data)

                # Update position
                self._update_position(symbol, order)

                # Update metrics
                self.total_trades += 1

                logger.info(f"Signal executed: {action} {quantity} {symbol}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return False

    def _update_position(self, symbol: str, order: Dict):
        """Update position after order execution"""
        try:
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'symbol': symbol,
                    'side': 'long' if order['side'] == 'BUY' else 'short',
                    'quantity': order['amount'],
                    'entry_price': order['price'],
                    'current_price': order['price'],
                    'unrealized_pnl': 0,
                    'opened_at': datetime.utcnow()
                }
            else:
                # Update existing position
                position = self.positions[symbol]
                if order['side'] == 'BUY':
                    # Adding to position
                    new_quantity = position['quantity'] + order['amount']
                    position['entry_price'] = (
                        (position['entry_price'] * position['quantity'] +
                         order['price'] * order['amount']) / new_quantity
                    )
                    position['quantity'] = new_quantity
                else:
                    # Reducing position
                    position['quantity'] -= order['amount']
                    if position['quantity'] <= 0:
                        # Position closed
                        del self.positions[symbol]

            # Update in database
            if symbol in self.positions:
                db_manager.update_position(symbol, self.positions[symbol])

        except Exception as e:
            logger.error(f"Error updating position: {e}")

    def _update_positions(self):
        """Update all open positions with current prices"""
        try:
            for symbol, position in self.positions.items():
                # Get current price
                ticker = self.kraken_client.get_ticker(symbol)
                if ticker:
                    current_price = ticker['last']
                    position['current_price'] = current_price

                    # Calculate unrealized PnL
                    if position['side'] == 'long':
                        position['unrealized_pnl'] = (
                            (current_price - position['entry_price']) * position['quantity']
                        )
                    else:
                        position['unrealized_pnl'] = (
                            (position['entry_price'] - current_price) * position['quantity']
                        )

                    # Check stop loss / take profit
                    self._check_position_exits(position)

        except Exception as e:
            logger.error(f"Error updating positions: {e}")

    def _check_position_exits(self, position: Dict):
        """Check if position should be closed"""
        try:
            symbol = position['symbol']
            pnl_percentage = (position['unrealized_pnl'] /
                            (position['entry_price'] * position['quantity']) * 100)

            # Check stop loss
            if pnl_percentage <= -config.STOP_LOSS_PERCENT:
                logger.warning(f"Stop loss triggered for {symbol}")
                self._close_position(symbol, reason='stop_loss')

            # Check take profit
            elif pnl_percentage >= config.TAKE_PROFIT_PERCENT:
                logger.info(f"Take profit triggered for {symbol}")
                self._close_position(symbol, reason='take_profit')

        except Exception as e:
            logger.error(f"Error checking position exits: {e}")

    def _close_position(self, symbol: str, reason: str = 'manual'):
        """Close a specific position"""
        try:
            if symbol not in self.positions:
                return False

            position = self.positions[symbol]
            side = 'SELL' if position['side'] == 'long' else 'BUY'

            # Place closing order
            order = self.kraken_client.place_order(
                symbol=symbol,
                side=side,
                order_type='MARKET',
                amount=position['quantity'],
                reduce_only=True
            )

            if order:
                # Calculate realized PnL
                realized_pnl = position['unrealized_pnl']

                # Update metrics
                if realized_pnl > 0:
                    self.winning_trades += 1
                self.total_pnl += realized_pnl

                # Remove position
                del self.positions[symbol]

                # Update database
                db_manager.close_position(symbol)

                logger.info(f"Position closed: {symbol} - Reason: {reason} - PnL: ${realized_pnl:.2f}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False

    def _close_all_positions(self, emergency: bool = False):
        """Close all open positions"""
        logger.info(f"Closing all positions (Emergency: {emergency})")

        for symbol in list(self.positions.keys()):
            self._close_position(symbol, reason='emergency' if emergency else 'manual')

    def _cancel_all_orders(self):
        """Cancel all pending orders"""
        try:
            cancelled = self.kraken_client.cancel_all_orders()
            logger.info(f"Cancelled {cancelled} orders")
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")

    # ====================
    # MONITORING
    # ====================

    def _monitoring_loop(self):
        """Monitor bot health and performance"""
        logger.info("Monitoring loop started")

        while self.is_running:
            try:
                # Check system health
                self._check_system_health()

                # Update performance metrics
                self._update_performance_metrics()

                # Check for alerts
                self._check_alerts()

                # Send heartbeat
                self._send_heartbeat()

                time.sleep(config.HEALTH_CHECK_INTERVAL)

            except Exception as e:
                logger.error(f"Monitoring error: {e}")

        logger.info("Monitoring loop stopped")

    def _check_system_health(self):
        """Check system health and resources"""
        try:
            # Check API connectivity
            balance = self.kraken_client.get_balance()
            if not balance:
                self.alert_manager.send_alert(
                    title="API Connection Issue",
                    message="Unable to connect to Kraken API",
                    level="error"
                )

            # Check database connectivity
            # ... implementation ...

        except Exception as e:
            logger.error(f"Health check error: {e}")

    def _check_risk_limits(self):
        """Check if risk limits are breached"""
        try:
            # Check daily loss limit
            if self.total_pnl <= -config.MAX_DAILY_LOSS_USD:
                logger.error("Daily loss limit reached")
                self.pause_trading = True
                self.alert_manager.send_alert(
                    title="Daily Loss Limit Reached",
                    message=f"Daily loss: ${abs(self.total_pnl):.2f}",
                    level="critical"
                )

            # Check drawdown
            drawdown = self.risk_manager.calculate_drawdown()
            if drawdown > config.MAX_DRAWDOWN_PERCENT:
                logger.error(f"Maximum drawdown exceeded: {drawdown:.2f}%")
                self.pause_trading = True
                self.alert_manager.send_alert(
                    title="Maximum Drawdown Exceeded",
                    message=f"Current drawdown: {drawdown:.2f}%",
                    level="critical"
                )

            # Check exposure
            total_exposure = sum(
                p['quantity'] * p['current_price']
                for p in self.positions.values()
            )
            if total_exposure > config.MAX_TOTAL_EXPOSURE_USD:
                logger.warning(f"Maximum exposure reached: ${total_exposure:.2f}")
                self.pause_trading = True

        except Exception as e:
            logger.error(f"Risk check error: {e}")

    def _check_alerts(self):
        """Check for system alerts"""
        try:
            alerts = db_manager.get_unacknowledged_alerts()
            for alert in alerts:
                # Process critical alerts
                if alert.level == 'critical':
                    logger.critical(f"Critical alert: {alert.title}")
                    # Could trigger emergency actions

        except Exception as e:
            logger.error(f"Alert check error: {e}")

    def _send_heartbeat(self):
        """Send heartbeat to indicate bot is alive"""
        try:
            # Update bot status in database
            self._update_bot_status('running')

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    # ====================
    # HELPER METHODS
    # ====================

    def _validate_configuration(self) -> bool:
        """Validate bot configuration"""
        try:
            # Check API credentials
            if not config.KRAKEN_API_KEY or not config.KRAKEN_API_SECRET:
                if not config.PAPER_TRADING:
                    logger.error("API credentials required for live trading")
                    return False

            # Check strategies
            if not self.enabled_strategies:
                logger.error("No strategies enabled")
                return False

            # Check trading pairs
            if not self.trading_pairs:
                logger.error("No trading pairs configured")
                return False

            # Validate risk settings
            if config.MAX_POSITION_SIZE_USD < config.MIN_ORDER_SIZE_USD:
                logger.error("Invalid position size configuration")
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False

    def _initialize_components(self):
        """Initialize bot components"""
        try:
            # Initialize strategies
            for strategy_name in self.enabled_strategies:
                self.strategy_manager.load_strategy(strategy_name)

            # Initialize risk manager
            self.risk_manager.initialize()

            # Initialize database
            db_manager.init_database()

            logger.info("Bot components initialized")

        except Exception as e:
            logger.error(f"Component initialization error: {e}")
            raise

    def _update_bot_status(self, status: str):
        """Update bot status in database"""
        try:
            status_data = {
                'session_id': self.session_id,
                'is_running': self.is_running,
                'is_paper_trading': config.PAPER_TRADING,
                'start_time': self.start_time,
                'enabled_strategies': self.enabled_strategies,
                'trading_pairs': self.trading_pairs,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'total_pnl': self.total_pnl,
                'open_positions': len(self.positions),
                'last_heartbeat': datetime.utcnow()
            }

            # Save to database
            # ... implementation ...

        except Exception as e:
            logger.error(f"Status update error: {e}")

    def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            metrics = db_manager.calculate_performance_metrics(
                self.session_id,
                period='hourly'
            )

            # Update internal metrics
            if metrics:
                self.total_trades = metrics.get('total_trades', 0)
                self.winning_trades = metrics.get('winning_trades', 0)
                self.total_pnl = metrics.get('net_pnl', 0)

        except Exception as e:
            logger.error(f"Metrics update error: {e}")

    def _handle_trading_error(self, error: Exception):
        """Handle trading loop errors"""
        logger.error(f"Trading error: {error}")

        # Send alert
        self.alert_manager.send_alert(
            title="Trading Error",
            message=str(error),
            level="error"
        )

        # Pause trading for safety
        self.pause_trading = True

    def _process_signals(self):
        """Process any pending signals from queue"""
        # Implementation for signal queue processing
        pass

    # ====================
    # PUBLIC METHODS
    # ====================

    def get_status(self) -> Dict:
        """Get current bot status"""
        return {
            'is_running': self.is_running,
            'session_id': self.session_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'enabled_strategies': self.enabled_strategies,
            'trading_pairs': self.trading_pairs,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'total_pnl': self.total_pnl,
            'open_positions': len(self.positions),
            'pause_trading': self.pause_trading,
            'paper_trading': config.PAPER_TRADING
        }

    def get_positions(self) -> List[Dict]:
        """Get current open positions"""
        return list(self.positions.values())

    def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.total_trades - self.winning_trades,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'total_pnl': self.total_pnl,
            'daily_pnl': self._get_daily_pnl(),
            'open_positions': len(self.positions),
            'total_exposure': sum(
                p['quantity'] * p['current_price']
                for p in self.positions.values()
            )
        }

    def _get_daily_pnl(self) -> float:
        """Get today's PnL"""
        # Implementation to fetch from database
        return self.total_pnl  # Simplified for now

    def update_settings(self, settings: Dict) -> bool:
        """Update bot settings"""
        try:
            if 'strategies' in settings:
                self.enabled_strategies = settings['strategies']

            if 'pairs' in settings:
                self.trading_pairs = settings['pairs']

            if 'max_positions' in settings:
                self.max_positions = settings['max_positions']

            logger.info("Settings updated")
            return True

        except Exception as e:
            logger.error(f"Settings update error: {e}")
            return False