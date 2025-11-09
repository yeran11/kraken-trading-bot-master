"""
Advanced Risk Calculator - Dynamic, Adaptive Risk Management
Calculates optimal position sizes and risk parameters based on market conditions
"""
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import numpy as np
import pandas as pd


class RiskCalculator:
    """
    Advanced risk calculator with dynamic position sizing
    
    Features:
    - Volatility-adjusted position sizing
    - Drawdown-based scaling
    - Time-based risk management
    - Kelly Criterion optimization
    - Risk-reward ratio analysis
    """
    
    def __init__(self, config: Dict):
        """
        Initialize risk calculator
        
        Args:
            config: Risk configuration dictionary
        """
        self.max_position_size = config.get('max_position_size_usd', 2500)
        self.min_position_size = config.get('min_position_size_usd', 50)
        self.max_total_exposure = config.get('max_total_exposure_usd', 10000)
        self.max_daily_loss = config.get('max_daily_loss_usd', 500)
        self.base_risk_per_trade = config.get('base_risk_per_trade', 0.02)  # 2% per trade
        
        # Performance tracking
        self.current_drawdown = 0.0
        self.peak_balance = 0.0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        logger.info("✓ Advanced Risk Calculator initialized")
    
    def calculate_position_size(
        self,
        account_balance: float,
        signal_confidence: float,
        volatility_regime: str,
        current_exposure: float,
        strategy_win_rate: Optional[float] = None,
        risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate optimal position size using multiple factors
        
        Args:
            account_balance: Current account balance
            signal_confidence: Signal confidence (0.0-1.0)
            volatility_regime: 'LOW', 'MEDIUM', or 'HIGH'
            current_exposure: Current total exposure
            strategy_win_rate: Historical win rate of strategy (optional)
            risk_reward_ratio: Expected risk/reward ratio
        
        Returns:
            Position size in USD
        """
        # Base position size (2% of balance)
        base_size = account_balance * self.base_risk_per_trade
        
        # 1. Confidence adjustment
        confidence_multiplier = self._get_confidence_multiplier(signal_confidence)
        size = base_size * confidence_multiplier
        
        # 2. Volatility adjustment
        volatility_multiplier = self._get_volatility_multiplier(volatility_regime)
        size *= volatility_multiplier
        
        # 3. Drawdown adjustment
        drawdown_multiplier = self._get_drawdown_multiplier()
        size *= drawdown_multiplier
        
        # 4. Kelly Criterion (if win rate available)
        if strategy_win_rate is not None:
            kelly_multiplier = self._calculate_kelly_multiplier(
                strategy_win_rate,
                risk_reward_ratio
            )
            size *= kelly_multiplier
        
        # 5. Exposure limit check
        remaining_exposure = self.max_total_exposure - current_exposure
        size = min(size, remaining_exposure)
        
        # 6. Enforce absolute limits
        size = max(self.min_position_size, min(size, self.max_position_size))
        
        logger.debug(
            f"Position size: ${size:.2f} "
            f"(confidence: {confidence_multiplier:.2f}x, "
            f"volatility: {volatility_multiplier:.2f}x, "
            f"drawdown: {drawdown_multiplier:.2f}x)"
        )
        
        return size
    
    def _get_confidence_multiplier(self, confidence: float) -> float:
        """
        Calculate position size multiplier based on signal confidence
        
        Confidence mapping:
        - 50%: 0.5x (minimum)
        - 60%: 0.8x
        - 70%: 1.0x (base)
        - 80%: 1.3x
        - 90%: 1.6x
        - 95%+: 2.0x (maximum)
        """
        if confidence < 0.5:
            return 0.0  # Don't trade below 50% confidence
        elif confidence < 0.6:
            return 0.5
        elif confidence < 0.7:
            return 0.8
        elif confidence < 0.8:
            return 1.0
        elif confidence < 0.9:
            return 1.3
        elif confidence < 0.95:
            return 1.6
        else:
            return 2.0
    
    def _get_volatility_multiplier(self, regime: str) -> float:
        """
        Calculate position size multiplier based on volatility
        
        Low volatility: Larger positions (1.2x)
        Medium volatility: Normal positions (1.0x)
        High volatility: Smaller positions (0.6x)
        """
        volatility_map = {
            'LOW_VOLATILITY': 1.2,
            'MEDIUM_VOLATILITY': 1.0,
            'HIGH_VOLATILITY': 0.6,
            'UNKNOWN': 0.8
        }
        return volatility_map.get(regime, 0.8)
    
    def _get_drawdown_multiplier(self) -> float:
        """
        Calculate position size multiplier based on current drawdown
        
        No drawdown: 1.0x
        5% drawdown: 0.9x
        10% drawdown: 0.7x
        15% drawdown: 0.5x
        20%+ drawdown: 0.3x
        """
        if self.current_drawdown < 0.05:
            return 1.0
        elif self.current_drawdown < 0.10:
            return 0.9
        elif self.current_drawdown < 0.15:
            return 0.7
        elif self.current_drawdown < 0.20:
            return 0.5
        else:
            return 0.3
    
    def _calculate_kelly_multiplier(
        self,
        win_rate: float,
        risk_reward_ratio: float
    ) -> float:
        """
        Calculate Kelly Criterion multiplier
        
        Kelly % = (Win Rate * Risk/Reward Ratio - Loss Rate) / Risk/Reward Ratio
        
        We use fractional Kelly (25%) for safety
        """
        if win_rate <= 0 or win_rate >= 1:
            return 1.0
        
        loss_rate = 1 - win_rate
        
        # Kelly formula
        kelly_percent = (win_rate * risk_reward_ratio - loss_rate) / risk_reward_ratio
        
        # Use fractional Kelly (25% of full Kelly) for safety
        fractional_kelly = kelly_percent * 0.25
        
        # Ensure multiplier is between 0.5 and 1.5
        multiplier = max(0.5, min(1.5, 1.0 + fractional_kelly))
        
        return multiplier
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        action: str,
        atr: float,
        atr_multiplier: float = 2.0,
        max_loss_percent: float = 3.0
    ) -> float:
        """
        Calculate dynamic stop loss based on ATR
        
        Args:
            entry_price: Entry price
            action: 'BUY' or 'SELL'
            atr: Average True Range
            atr_multiplier: ATR multiplier (default 2.0)
            max_loss_percent: Maximum loss percentage (default 3%)
        
        Returns:
            Stop loss price
        """
        # ATR-based stop
        atr_stop_distance = atr * atr_multiplier
        
        # Percentage-based stop
        percent_stop_distance = entry_price * (max_loss_percent / 100)
        
        # Use the tighter of the two
        stop_distance = min(atr_stop_distance, percent_stop_distance)
        
        if action == 'BUY':
            stop_loss = entry_price - stop_distance
        else:  # SELL
            stop_loss = entry_price + stop_distance
        
        return stop_loss
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        action: str,
        risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate take profit based on risk/reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            action: 'BUY' or 'SELL'
            risk_reward_ratio: Target R:R ratio (default 2:1)
        
        Returns:
            Take profit price
        """
        # Calculate risk (distance to stop loss)
        risk = abs(entry_price - stop_loss)
        
        # Calculate reward (risk * R:R ratio)
        reward = risk * risk_reward_ratio
        
        if action == 'BUY':
            take_profit = entry_price + reward
        else:  # SELL
            take_profit = entry_price - reward
        
        return take_profit
    
    def update_drawdown(self, current_balance: float):
        """Update current drawdown metrics"""
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L"""
        self.daily_pnl += pnl
    
    def reset_daily_pnl(self):
        """Reset daily P&L (call at start of new day)"""
        self.daily_pnl = 0.0
    
    def update_streak(self, was_winner: bool):
        """Update win/loss streak"""
        if was_winner:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
    
    def should_stop_trading(self) -> Tuple[bool, str]:
        """
        Check if trading should be stopped due to risk limits
        
        Returns:
            (should_stop, reason)
        """
        # Daily loss limit
        if abs(self.daily_pnl) >= self.max_daily_loss:
            return True, f"Daily loss limit reached: ${abs(self.daily_pnl):.2f}"
        
        # Maximum drawdown
        if self.current_drawdown >= 0.20:  # 20% drawdown
            return True, f"Maximum drawdown reached: {self.current_drawdown:.1%}"
        
        # Consecutive losses (circuit breaker)
        if self.consecutive_losses >= 5:
            return True, f"Too many consecutive losses: {self.consecutive_losses}"
        
        return False, ""
    
    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        return {
            'current_drawdown': self.current_drawdown,
            'peak_balance': self.peak_balance,
            'daily_pnl': self.daily_pnl,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'max_daily_loss': self.max_daily_loss,
            'max_position_size': self.max_position_size,
            'max_total_exposure': self.max_total_exposure
        }


class TimeBasedRiskManager:
    """
    Time-based risk management
    Adjusts risk based on time of day, day of week, and market events
    """
    
    def __init__(self):
        # High liquidity hours (UTC)
        self.high_liquidity_hours = list(range(13, 21))  # 1 PM - 9 PM UTC (US trading hours)
        
        # Low liquidity hours
        self.low_liquidity_hours = list(range(0, 6))  # Midnight - 6 AM UTC
        
        logger.info("✓ Time-based Risk Manager initialized")
    
    def get_time_multiplier(self, current_time: Optional[datetime] = None) -> float:
        """
        Get risk multiplier based on current time
        
        Returns:
            Multiplier (0.5 - 1.2)
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        hour = current_time.hour
        weekday = current_time.weekday()  # 0 = Monday, 6 = Sunday
        
        # Weekend (reduce risk)
        if weekday >= 5:  # Saturday or Sunday
            return 0.7
        
        # High liquidity hours (increase risk)
        if hour in self.high_liquidity_hours:
            return 1.2
        
        # Low liquidity hours (reduce risk)
        if hour in self.low_liquidity_hours:
            return 0.5
        
        # Normal hours
        return 1.0
    
    def is_high_risk_period(self, current_time: Optional[datetime] = None) -> bool:
        """Check if current time is high-risk (low liquidity)"""
        if current_time is None:
            current_time = datetime.utcnow()
        
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Weekend or low liquidity hours
        return weekday >= 5 or hour in self.low_liquidity_hours


class CorrelationRiskManager:
    """
    Correlation-based risk management
    Prevents over-concentration in correlated assets
    """
    
    def __init__(self, max_correlated_positions: int = 3):
        self.max_correlated_positions = max_correlated_positions
        self.correlation_groups = {
            'BTC_GROUP': ['BTC/USD', 'BTC/USDT', 'XBTUSD'],
            'ETH_GROUP': ['ETH/USD', 'ETH/USDT', 'ETHUSD'],
            'ALTCOIN_GROUP': ['SOL/USD', 'MATIC/USD', 'LINK/USD', 'ADA/USD'],
            'DEFI_GROUP': ['UNI/USD', 'AAVE/USD', 'COMP/USD'],
            'MEME_GROUP': ['DOGE/USD', 'SHIB/USD']
        }
        
        logger.info("✓ Correlation Risk Manager initialized")
    
    def get_correlation_group(self, symbol: str) -> Optional[str]:
        """Get correlation group for a symbol"""
        for group_name, symbols in self.correlation_groups.items():
            if symbol in symbols:
                return group_name
        return None
    
    def check_correlation_limit(
        self,
        new_symbol: str,
        current_positions: list
    ) -> Tuple[bool, str]:
        """
        Check if adding new position would exceed correlation limits
        
        Returns:
            (is_allowed, reason)
        """
        new_group = self.get_correlation_group(new_symbol)
        
        if new_group is None:
            return True, ""  # Unknown symbol, allow
        
        # Count positions in same group
        group_count = sum(
            1 for pos in current_positions
            if self.get_correlation_group(pos) == new_group
        )
        
        if group_count >= self.max_correlated_positions:
            return False, f"Too many positions in {new_group} ({group_count}/{self.max_correlated_positions})"
        
        return True, ""
