"""
Strategy Manager - Orchestrates all trading strategies
Manages strategy selection, execution, and performance tracking
"""
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd

from strategies import (
    MomentumStrategy,
    MeanReversionStrategy,
    ScalpingStrategy,
    GridTradingStrategy,
    ArbitrageStrategy,
    Signal
)

from strategies_advanced import (
    BreakoutStrategy,
    TrendFollowingStrategy,
    SupportResistanceStrategy,
    VolumeProfileStrategy,
    MarketStructureStrategy
)


class StrategyManager:
    """
    Manages all trading strategies and their execution
    
    Features:
    - 10 total strategies (5 basic + 5 advanced)
    - Strategy performance tracking
    - Dynamic strategy selection
    - Multi-strategy signal aggregation
    """
    
    def __init__(self, enabled_strategies: List[str] = None):
        """
        Initialize strategy manager
        
        Args:
            enabled_strategies: List of strategy names to enable
                              If None, enables all strategies
        """
        # Initialize all strategies
        self.strategies = {
            # Basic strategies
            'momentum': MomentumStrategy(),
            'mean_reversion': MeanReversionStrategy(),
            'scalping': ScalpingStrategy(),
            'grid': GridTradingStrategy(),
            'arbitrage': ArbitrageStrategy(),
            
            # Advanced strategies
            'breakout': BreakoutStrategy(),
            'trend_following': TrendFollowingStrategy(),
            'support_resistance': SupportResistanceStrategy(),
            'volume_profile': VolumeProfileStrategy(),
            'market_structure': MarketStructureStrategy()
        }
        
        # Enable specified strategies or all by default
        if enabled_strategies:
            self.enabled_strategies = {
                name: strategy for name, strategy in self.strategies.items()
                if name in enabled_strategies
            }
        else:
            self.enabled_strategies = self.strategies.copy()
        
        # Performance tracking
        self.strategy_performance = {name: {
            'total_signals': 0,
            'winning_signals': 0,
            'total_profit': 0.0,
            'win_rate': 0.0,
            'avg_profit': 0.0
        } for name in self.strategies.keys()}
        
        logger.success(f"✓ Strategy Manager initialized with {len(self.enabled_strategies)} strategies")
        logger.info(f"📊 Enabled strategies: {', '.join(self.enabled_strategies.keys())}")
    
    def get_signals(
        self,
        symbol: str,
        df: pd.DataFrame,
        timeframe: str = '5m'
    ) -> List[Signal]:
        """
        Get trading signals from all enabled strategies
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            df: OHLCV dataframe
            timeframe: Trading timeframe
        
        Returns:
            List of Signal objects from all strategies
        """
        signals = []
        
        for strategy_name, strategy in self.enabled_strategies.items():
            try:
                signal = strategy.analyze(df, symbol)
                
                if signal and signal.action != 'HOLD':
                    # Add timeframe to signal
                    signal.timeframe = timeframe
                    signals.append(signal)
                    
                    logger.debug(
                        f"📊 {strategy_name}: {signal.action} {symbol} "
                        f"(strength: {signal.strength:.2f}, confidence: {signal.confidence:.2f})"
                    )
                    
            except Exception as e:
                logger.error(f"Error in {strategy_name} strategy: {e}")
        
        return signals
    
    def get_best_signal(
        self,
        symbol: str,
        df: pd.DataFrame,
        timeframe: str = '5m'
    ) -> Optional[Signal]:
        """
        Get the best signal from all strategies
        
        Selects signal with highest confidence * strength score
        
        Args:
            symbol: Trading pair
            df: OHLCV dataframe
            timeframe: Trading timeframe
        
        Returns:
            Best Signal or None
        """
        signals = self.get_signals(symbol, df, timeframe)
        
        if not signals:
            return None
        
        # Score each signal (confidence * strength)
        scored_signals = [
            (signal, signal.confidence * signal.strength)
            for signal in signals
        ]
        
        # Sort by score
        scored_signals.sort(key=lambda x: x[1], reverse=True)
        
        best_signal = scored_signals[0][0]
        best_score = scored_signals[0][1]
        
        logger.info(
            f"🎯 Best signal: {best_signal.strategy} - {best_signal.action} "
            f"(score: {best_score:.2f})"
        )
        
        return best_signal
    
    def aggregate_signals(
        self,
        symbol: str,
        df: pd.DataFrame,
        timeframe: str = '5m',
        min_agreement: int = 2
    ) -> Optional[Signal]:
        """
        Aggregate signals from multiple strategies
        
        Requires minimum number of strategies to agree on direction
        
        Args:
            symbol: Trading pair
            df: OHLCV dataframe
            timeframe: Trading timeframe
            min_agreement: Minimum strategies that must agree
        
        Returns:
            Aggregated Signal or None
        """
        signals = self.get_signals(symbol, df, timeframe)
        
        if len(signals) < min_agreement:
            return None
        
        # Count BUY and SELL signals
        buy_signals = [s for s in signals if s.action == 'BUY']
        sell_signals = [s for s in signals if s.action == 'SELL']
        
        # Check for agreement
        if len(buy_signals) >= min_agreement:
            # Aggregate BUY signals
            avg_strength = sum(s.strength for s in buy_signals) / len(buy_signals)
            avg_confidence = sum(s.confidence for s in buy_signals) / len(buy_signals)
            
            # Use the most conservative stop loss and most aggressive take profit
            stop_losses = [s.stop_loss for s in buy_signals if s.stop_loss]
            take_profits = [s.take_profit for s in buy_signals if s.take_profit]
            
            return Signal(
                symbol=symbol,
                action='BUY',
                strength=avg_strength,
                strategy='aggregated',
                reason=f"{len(buy_signals)} strategies agree on BUY: {', '.join([s.strategy for s in buy_signals])}",
                confidence=avg_confidence,
                stop_loss=max(stop_losses) if stop_losses else None,
                take_profit=max(take_profits) if take_profits else None,
                timeframe=timeframe
            )
        
        elif len(sell_signals) >= min_agreement:
            # Aggregate SELL signals
            avg_strength = sum(s.strength for s in sell_signals) / len(sell_signals)
            avg_confidence = sum(s.confidence for s in sell_signals) / len(sell_signals)
            
            stop_losses = [s.stop_loss for s in sell_signals if s.stop_loss]
            take_profits = [s.take_profit for s in sell_signals if s.take_profit]
            
            return Signal(
                symbol=symbol,
                action='SELL',
                strength=avg_strength,
                strategy='aggregated',
                reason=f"{len(sell_signals)} strategies agree on SELL: {', '.join([s.strategy for s in sell_signals])}",
                confidence=avg_confidence,
                stop_loss=min(stop_losses) if stop_losses else None,
                take_profit=min(take_profits) if take_profits else None,
                timeframe=timeframe
            )
        
        return None
    
    def update_performance(
        self,
        strategy_name: str,
        was_profitable: bool,
        profit: float
    ):
        """
        Update strategy performance metrics
        
        Args:
            strategy_name: Name of the strategy
            was_profitable: Whether the trade was profitable
            profit: Profit/loss amount
        """
        if strategy_name not in self.strategy_performance:
            return
        
        perf = self.strategy_performance[strategy_name]
        perf['total_signals'] += 1
        
        if was_profitable:
            perf['winning_signals'] += 1
        
        perf['total_profit'] += profit
        
        # Calculate metrics
        if perf['total_signals'] > 0:
            perf['win_rate'] = perf['winning_signals'] / perf['total_signals']
            perf['avg_profit'] = perf['total_profit'] / perf['total_signals']
    
    def get_performance_report(self) -> Dict:
        """Get performance report for all strategies"""
        return self.strategy_performance.copy()
    
    def get_top_strategies(self, n: int = 3) -> List[str]:
        """
        Get top N performing strategies by win rate
        
        Args:
            n: Number of top strategies to return
        
        Returns:
            List of strategy names
        """
        # Filter strategies with at least 10 signals
        qualified = {
            name: perf for name, perf in self.strategy_performance.items()
            if perf['total_signals'] >= 10
        }
        
        if not qualified:
            return list(self.enabled_strategies.keys())[:n]
        
        # Sort by win rate
        sorted_strategies = sorted(
            qualified.items(),
            key=lambda x: x[1]['win_rate'],
            reverse=True
        )
        
        return [name for name, _ in sorted_strategies[:n]]
    
    def enable_strategy(self, strategy_name: str):
        """Enable a specific strategy"""
        if strategy_name in self.strategies:
            self.enabled_strategies[strategy_name] = self.strategies[strategy_name]
            logger.info(f"✓ Enabled strategy: {strategy_name}")
        else:
            logger.warning(f"Strategy not found: {strategy_name}")
    
    def disable_strategy(self, strategy_name: str):
        """Disable a specific strategy"""
        if strategy_name in self.enabled_strategies:
            del self.enabled_strategies[strategy_name]
            logger.info(f"✗ Disabled strategy: {strategy_name}")
    
    def get_strategy_info(self) -> Dict:
        """Get information about all strategies"""
        info = {}
        
        for name, strategy in self.strategies.items():
            info[name] = {
                'name': name,
                'enabled': name in self.enabled_strategies,
                'description': strategy.__doc__.split('\n')[1].strip() if strategy.__doc__ else '',
                'performance': self.strategy_performance[name]
            }
        
        return info
