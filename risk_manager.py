"""
Risk Management System for Kraken Trading Bot
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import numpy as np

import config
from database import db_manager, Trade, Position


class RiskManager:
    """Comprehensive risk management system"""

    def __init__(self, kraken_client):
        self.kraken_client = kraken_client

        # Risk Limits
        self.max_position_size_usd = config.MAX_POSITION_SIZE_USD
        self.max_total_exposure_usd = config.MAX_TOTAL_EXPOSURE_USD
        self.max_daily_loss_usd = config.MAX_DAILY_LOSS_USD
        self.max_drawdown_percent = config.MAX_DRAWDOWN_PERCENT
        self.min_order_size_usd = config.MIN_ORDER_SIZE_USD

        # Position Tracking
        self.positions = {}
        self.daily_pnl = 0.0
        self.peak_balance = 0.0
        self.current_balance = 0.0

        # Risk Metrics
        self.current_exposure = 0.0
        self.current_drawdown = 0.0
        self.daily_trades_count = 0
        self.consecutive_losses = 0

        # Correlation Matrix
        self.correlation_matrix = {}

        logger.info("Risk Manager initialized")

    def initialize(self):
        """Initialize risk manager with current state"""
        try:
            # Load current positions
            self._load_positions()

            # Calculate current metrics
            self._update_metrics()

            # Load historical data for correlation
            self._load_correlation_data()

            logger.info("Risk Manager ready")
            return True

        except Exception as e:
            logger.error(f"Risk Manager initialization error: {e}")
            return False

    # ====================
    # POSITION SIZING
    # ====================

    def calculate_position_size(self, symbol: str, signal_strength: float = 0.5,
                               strategy: str = None) -> float:
        """Calculate optimal position size based on Kelly Criterion and risk limits"""
        try:
            # Get current price
            ticker = self.kraken_client.get_ticker(symbol)
            if not ticker:
                return 0

            current_price = ticker['last']

            # Get account balance
            balance = self._get_available_balance()

            # Base position size (percentage of balance)
            base_size_usd = balance * 0.02  # 2% of balance per trade

            # Adjust by signal strength
            adjusted_size_usd = base_size_usd * signal_strength

            # Apply Kelly Criterion if we have historical data
            if strategy:
                kelly_multiplier = self._calculate_kelly_criterion(strategy)
                adjusted_size_usd *= kelly_multiplier

            # Apply risk limits
            # 1. Maximum single position size
            adjusted_size_usd = min(adjusted_size_usd, self.max_position_size_usd)

            # 2. Minimum order size
            if adjusted_size_usd < self.min_order_size_usd:
                logger.warning(f"Position size below minimum: ${adjusted_size_usd:.2f}")
                return 0

            # 3. Check total exposure limit
            if self.current_exposure + adjusted_size_usd > self.max_total_exposure_usd:
                available = self.max_total_exposure_usd - self.current_exposure
                if available < self.min_order_size_usd:
                    logger.warning("Maximum exposure limit reached")
                    return 0
                adjusted_size_usd = available

            # 4. Reduce size after consecutive losses
            if self.consecutive_losses >= 3:
                reduction_factor = 0.5 ** (self.consecutive_losses - 2)
                adjusted_size_usd *= reduction_factor
                logger.info(f"Reducing position size due to {self.consecutive_losses} consecutive losses")

            # Convert USD to asset quantity
            quantity = adjusted_size_usd / current_price

            # Round to appropriate decimal places
            quantity = self._round_quantity(symbol, quantity)

            logger.info(f"Position size calculated: {quantity} {symbol} (${adjusted_size_usd:.2f})")
            return quantity

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0

    def _calculate_kelly_criterion(self, strategy: str) -> float:
        """Calculate Kelly Criterion for position sizing"""
        try:
            # Get strategy win rate and average win/loss
            trades = db_manager.get_recent_trades(limit=100)
            strategy_trades = [t for t in trades if t.strategy == strategy]

            if len(strategy_trades) < 20:
                return 0.5  # Default conservative multiplier

            wins = [t for t in strategy_trades if t.pnl > 0]
            losses = [t for t in strategy_trades if t.pnl < 0]

            if not wins or not losses:
                return 0.5

            win_rate = len(wins) / len(strategy_trades)
            avg_win = sum(t.pnl for t in wins) / len(wins)
            avg_loss = abs(sum(t.pnl for t in losses) / len(losses))

            # Kelly formula: f = (p * b - q) / b
            # where f = fraction to bet, p = win rate, q = loss rate, b = win/loss ratio
            b = avg_win / avg_loss
            q = 1 - win_rate
            kelly_fraction = (win_rate * b - q) / b

            # Apply Kelly fraction with safety factor
            kelly_fraction = max(0, min(kelly_fraction * 0.25, 0.25))  # Max 25% of Kelly

            return kelly_fraction

        except Exception as e:
            logger.error(f"Kelly Criterion calculation error: {e}")
            return 0.5

    # ====================
    # RISK VALIDATION
    # ====================

    def validate_signal(self, signal: Dict) -> bool:
        """Validate if signal passes risk checks"""
        try:
            symbol = signal['symbol']

            # Check if we already have a position in this symbol
            if symbol in self.positions:
                existing_position = self.positions[symbol]
                # Allow adding to winning positions only
                if existing_position['unrealized_pnl'] < 0:
                    logger.warning(f"Cannot add to losing position: {symbol}")
                    return False

            # Check correlation risk
            if not self._check_correlation_risk(symbol):
                logger.warning(f"High correlation risk for {symbol}")
                return False

            # Check daily loss limit
            if self.daily_pnl <= -self.max_daily_loss_usd:
                logger.error("Daily loss limit reached")
                return False

            # Check drawdown
            if self.current_drawdown >= self.max_drawdown_percent:
                logger.error(f"Maximum drawdown reached: {self.current_drawdown:.2f}%")
                return False

            # Check volatility
            if not self._check_volatility_risk(symbol):
                logger.warning(f"High volatility risk for {symbol}")
                return False

            # Check liquidity
            if not self._check_liquidity(symbol):
                logger.warning(f"Insufficient liquidity for {symbol}")
                return False

            return True

        except Exception as e:
            logger.error(f"Signal validation error: {e}")
            return False

    def can_open_position(self, symbol: str, size: float) -> Tuple[bool, str]:
        """Check if we can open a new position"""
        try:
            # Get current price
            ticker = self.kraken_client.get_ticker(symbol)
            if not ticker:
                return False, "Cannot get price"

            position_value = size * ticker['last']

            # Check minimum order size
            if position_value < self.min_order_size_usd:
                return False, f"Below minimum order size (${self.min_order_size_usd})"

            # Check maximum position size
            if position_value > self.max_position_size_usd:
                return False, f"Exceeds maximum position size (${self.max_position_size_usd})"

            # Check total exposure
            if self.current_exposure + position_value > self.max_total_exposure_usd:
                return False, f"Would exceed maximum exposure (${self.max_total_exposure_usd})"

            # Check available balance
            available_balance = self._get_available_balance()
            if position_value > available_balance:
                return False, "Insufficient balance"

            # Check daily loss limit
            if self.daily_pnl <= -self.max_daily_loss_usd * 0.8:  # 80% of limit
                return False, "Approaching daily loss limit"

            return True, "OK"

        except Exception as e:
            logger.error(f"Position check error: {e}")
            return False, str(e)

    def _check_correlation_risk(self, symbol: str) -> bool:
        """Check correlation with existing positions"""
        try:
            if not self.positions:
                return True

            # Simple correlation check - limit positions in same base currency
            base_currency = symbol.split('/')[0]
            correlated_positions = sum(
                1 for s in self.positions.keys()
                if s.split('/')[0] == base_currency
            )

            if correlated_positions >= 2:
                return False  # Max 2 positions in same base currency

            return True

        except Exception as e:
            logger.error(f"Correlation check error: {e}")
            return True

    def _check_volatility_risk(self, symbol: str) -> bool:
        """Check if volatility is within acceptable range"""
        try:
            # Get recent price data
            df = self.kraken_client.get_ohlcv(symbol, '1h', limit=24)
            if df is None or df.empty:
                return False

            # Calculate volatility (standard deviation of returns)
            returns = df['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(24)  # Annualized

            # Check if volatility is too high (>100% annualized)
            if volatility > 1.0:
                logger.warning(f"High volatility for {symbol}: {volatility*100:.2f}%")
                return False

            return True

        except Exception as e:
            logger.error(f"Volatility check error: {e}")
            return True

    def _check_liquidity(self, symbol: str) -> bool:
        """Check if market has sufficient liquidity"""
        try:
            # Get order book
            orderbook = self.kraken_client.get_orderbook(symbol, depth=10)
            if not orderbook:
                return False

            # Calculate total bid/ask volume in top 10 levels
            bid_volume = sum(bid[1] for bid in orderbook['bids'][:10])
            ask_volume = sum(ask[1] for ask in orderbook['asks'][:10])

            # Get typical trade size
            ticker = self.kraken_client.get_ticker(symbol)
            typical_trade_usd = self.max_position_size_usd * 0.5

            # Check if there's enough liquidity
            min_liquidity = typical_trade_usd / ticker['last']
            if bid_volume < min_liquidity or ask_volume < min_liquidity:
                return False

            return True

        except Exception as e:
            logger.error(f"Liquidity check error: {e}")
            return True

    # ====================
    # POSITION MANAGEMENT
    # ====================

    def open_position(self, symbol: str, side: str, quantity: float,
                     entry_price: float, stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None):
        """Register a new position"""
        try:
            # Calculate stop loss if not provided
            if not stop_loss:
                if side == 'BUY':
                    stop_loss = entry_price * (1 - config.STOP_LOSS_PERCENT / 100)
                else:
                    stop_loss = entry_price * (1 + config.STOP_LOSS_PERCENT / 100)

            # Calculate take profit if not provided
            if not take_profit:
                if side == 'BUY':
                    take_profit = entry_price * (1 + config.TAKE_PROFIT_PERCENT / 100)
                else:
                    take_profit = entry_price * (1 - config.TAKE_PROFIT_PERCENT / 100)

            position = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'entry_price': entry_price,
                'current_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'unrealized_pnl': 0,
                'opened_at': datetime.utcnow()
            }

            self.positions[symbol] = position

            # Update exposure
            self.current_exposure += quantity * entry_price

            logger.info(f"Position opened: {symbol} {side} {quantity} @ {entry_price}")

        except Exception as e:
            logger.error(f"Error opening position: {e}")

    def close_position(self, symbol: str, exit_price: float, reason: str = 'manual'):
        """Close a position and calculate PnL"""
        try:
            if symbol not in self.positions:
                logger.warning(f"Position not found: {symbol}")
                return

            position = self.positions[symbol]

            # Calculate PnL
            if position['side'] == 'BUY':
                pnl = (exit_price - position['entry_price']) * position['quantity']
            else:
                pnl = (position['entry_price'] - exit_price) * position['quantity']

            # Update metrics
            self.daily_pnl += pnl
            self.current_exposure -= position['quantity'] * position['entry_price']

            # Track consecutive losses
            if pnl < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0

            # Remove position
            del self.positions[symbol]

            logger.info(f"Position closed: {symbol} @ {exit_price} - PnL: ${pnl:.2f} ({reason})")

            # Record to database
            # ... implementation ...

        except Exception as e:
            logger.error(f"Error closing position: {e}")

    def update_position(self, symbol: str, current_price: float):
        """Update position with current price"""
        try:
            if symbol not in self.positions:
                return

            position = self.positions[symbol]
            position['current_price'] = current_price

            # Calculate unrealized PnL
            if position['side'] == 'BUY':
                position['unrealized_pnl'] = (current_price - position['entry_price']) * position['quantity']
            else:
                position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['quantity']

            # Check if stop loss or take profit hit
            self._check_exit_conditions(position)

        except Exception as e:
            logger.error(f"Error updating position: {e}")

    def _check_exit_conditions(self, position: Dict):
        """Check if position should be closed"""
        try:
            current_price = position['current_price']
            symbol = position['symbol']

            # Check stop loss
            if position['side'] == 'BUY':
                if current_price <= position['stop_loss']:
                    logger.warning(f"Stop loss triggered for {symbol}")
                    # Signal to close position
                    return 'stop_loss'

                if current_price >= position['take_profit']:
                    logger.info(f"Take profit triggered for {symbol}")
                    return 'take_profit'
            else:
                if current_price >= position['stop_loss']:
                    logger.warning(f"Stop loss triggered for {symbol}")
                    return 'stop_loss'

                if current_price <= position['take_profit']:
                    logger.info(f"Take profit triggered for {symbol}")
                    return 'take_profit'

            return None

        except Exception as e:
            logger.error(f"Error checking exit conditions: {e}")
            return None

    # ====================
    # METRICS & MONITORING
    # ====================

    def calculate_drawdown(self) -> float:
        """Calculate current drawdown percentage"""
        try:
            current_balance = self._get_total_balance()

            if current_balance > self.peak_balance:
                self.peak_balance = current_balance

            if self.peak_balance > 0:
                self.current_drawdown = ((self.peak_balance - current_balance) / self.peak_balance) * 100
            else:
                self.current_drawdown = 0

            return self.current_drawdown

        except Exception as e:
            logger.error(f"Drawdown calculation error: {e}")
            return 0

    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        return {
            'current_exposure': self.current_exposure,
            'max_exposure': self.max_total_exposure_usd,
            'exposure_percentage': (self.current_exposure / self.max_total_exposure_usd * 100) if self.max_total_exposure_usd > 0 else 0,
            'daily_pnl': self.daily_pnl,
            'daily_loss_limit': self.max_daily_loss_usd,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown_percent,
            'open_positions': len(self.positions),
            'consecutive_losses': self.consecutive_losses,
            'positions': list(self.positions.values())
        }

    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of trading day)"""
        self.daily_pnl = 0
        self.daily_trades_count = 0
        logger.info("Daily metrics reset")

    # ====================
    # HELPER METHODS
    # ====================

    def _load_positions(self):
        """Load existing positions from database"""
        try:
            # Load from database
            # ... implementation ...
            pass
        except Exception as e:
            logger.error(f"Error loading positions: {e}")

    def _update_metrics(self):
        """Update all risk metrics"""
        try:
            # Update exposure
            self.current_exposure = sum(
                p['quantity'] * p['current_price']
                for p in self.positions.values()
            )

            # Update drawdown
            self.calculate_drawdown()

        except Exception as e:
            logger.error(f"Metrics update error: {e}")

    def _load_correlation_data(self):
        """Load correlation data for risk analysis"""
        try:
            # Load historical correlation data
            # ... implementation ...
            pass
        except Exception as e:
            logger.error(f"Correlation data load error: {e}")

    def _get_available_balance(self) -> float:
        """Get available balance for trading"""
        try:
            balance = self.kraken_client.get_balance()
            if 'USD' in balance:
                if isinstance(balance['USD'], dict):
                    return balance['USD'].get('free', 0)
                return balance['USD']
            return 0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0

    def _get_total_balance(self) -> float:
        """Get total account balance in USD"""
        try:
            balance = self.kraken_client.get_balance()
            total_usd = 0

            for currency, amount in balance.items():
                if isinstance(amount, dict):
                    amount = amount.get('total', 0)

                if currency == 'USD':
                    total_usd += amount
                else:
                    # Convert to USD
                    try:
                        ticker = self.kraken_client.get_ticker(f"{currency}/USD")
                        if ticker:
                            total_usd += amount * ticker['last']
                    except:
                        pass

            return total_usd

        except Exception as e:
            logger.error(f"Error getting total balance: {e}")
            return 0

    def _round_quantity(self, symbol: str, quantity: float) -> float:
        """Round quantity to appropriate decimal places"""
        # Kraken-specific rounding rules
        if 'BTC' in symbol:
            return round(quantity, 8)
        elif 'ETH' in symbol:
            return round(quantity, 6)
        else:
            return round(quantity, 4)

    def update_limits(self):
        """Update risk limits from configuration"""
        self.max_position_size_usd = config.MAX_POSITION_SIZE_USD
        self.max_total_exposure_usd = config.MAX_TOTAL_EXPOSURE_USD
        self.max_daily_loss_usd = config.MAX_DAILY_LOSS_USD
        self.max_drawdown_percent = config.MAX_DRAWDOWN_PERCENT
        logger.info("Risk limits updated")