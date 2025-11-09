"""
Performance Tracker - Comprehensive performance monitoring and analytics
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    # Basic metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L metrics
    total_pnl: float = 0.0
    total_pnl_percent: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Risk metrics
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    current_drawdown: float = 0.0
    
    # Trade metrics
    avg_hold_time_hours: float = 0.0
    avg_r_multiple: float = 0.0
    expectancy: float = 0.0
    
    # Streak metrics
    current_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0
    
    # Time-based
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0


class PerformanceTracker:
    """
    Tracks and analyzes trading performance
    
    Features:
    - Real-time P&L tracking
    - Win rate and profit factor
    - Sharpe and Sortino ratios
    - Drawdown tracking
    - R-multiple analysis
    - Time-based performance
    - Strategy comparison
    """
    
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        
        # Trade history
        self.trades: List[Dict] = []
        self.daily_returns: List[float] = []
        
        # Equity curve
        self.equity_curve: List[tuple] = [(datetime.utcnow(), initial_balance)]
        
        # Strategy performance
        self.strategy_performance: Dict[str, PerformanceMetrics] = {}
        
        # Streaks
        self.current_streak = 0
        self.max_win_streak = 0
        self.max_loss_streak = 0
        
        logger.info(f"✓ Performance Tracker initialized with ${initial_balance:,.2f}")
    
    def add_trade(self, trade: Dict):
        """
        Add completed trade to tracking
        
        Args:
            trade: {
                'symbol': str,
                'action': str,
                'entry_price': float,
                'exit_price': float,
                'position_size': float,
                'pnl': float,
                'pnl_percent': float,
                'strategy': str,
                'entry_time': datetime,
                'exit_time': datetime,
                'was_winner': bool
            }
        """
        self.trades.append(trade)
        
        # Update balance
        self.current_balance += trade['pnl']
        
        # Update peak
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Update equity curve
        self.equity_curve.append((trade['exit_time'], self.current_balance))
        
        # Update daily returns
        daily_return = (trade['pnl'] / self.current_balance) * 100
        self.daily_returns.append(daily_return)
        
        # Update streaks
        if trade['was_winner']:
            if self.current_streak >= 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
            self.max_win_streak = max(self.max_win_streak, self.current_streak)
        else:
            if self.current_streak <= 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1
            self.max_loss_streak = max(self.max_loss_streak, abs(self.current_streak))
        
        # Update strategy performance
        strategy = trade['strategy']
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = PerformanceMetrics()
        
        self._update_strategy_metrics(strategy, trade)
        
        logger.debug(
            f"📊 Trade added: {trade['strategy']} {trade['action']} "
            f"P&L: ${trade['pnl']:.2f} ({trade['pnl_percent']:+.2f}%)"
        )
    
    def _update_strategy_metrics(self, strategy: str, trade: Dict):
        """Update metrics for specific strategy"""
        metrics = self.strategy_performance[strategy]
        
        metrics.total_trades += 1
        
        if trade['was_winner']:
            metrics.winning_trades += 1
            metrics.avg_win = (
                (metrics.avg_win * (metrics.winning_trades - 1) + trade['pnl']) 
                / metrics.winning_trades
            )
            metrics.largest_win = max(metrics.largest_win, trade['pnl'])
        else:
            metrics.losing_trades += 1
            metrics.avg_loss = (
                (metrics.avg_loss * (metrics.losing_trades - 1) + trade['pnl']) 
                / metrics.losing_trades
            )
            metrics.largest_loss = min(metrics.largest_loss, trade['pnl'])
        
        metrics.total_pnl += trade['pnl']
        metrics.win_rate = metrics.winning_trades / metrics.total_trades
    
    def get_overall_metrics(self) -> PerformanceMetrics:
        """Calculate overall performance metrics"""
        if not self.trades:
            return PerformanceMetrics()
        
        metrics = PerformanceMetrics()
        
        # Basic counts
        metrics.total_trades = len(self.trades)
        metrics.winning_trades = sum(1 for t in self.trades if t['was_winner'])
        metrics.losing_trades = metrics.total_trades - metrics.winning_trades
        metrics.win_rate = metrics.winning_trades / metrics.total_trades if metrics.total_trades > 0 else 0
        
        # P&L metrics
        metrics.total_pnl = self.current_balance - self.initial_balance
        metrics.total_pnl_percent = (metrics.total_pnl / self.initial_balance) * 100
        
        winning_trades = [t for t in self.trades if t['was_winner']]
        losing_trades = [t for t in self.trades if not t['was_winner']]
        
        metrics.avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        metrics.avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        metrics.largest_win = max([t['pnl'] for t in winning_trades]) if winning_trades else 0
        metrics.largest_loss = min([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe ratio
        if len(self.daily_returns) > 1:
            returns_array = np.array(self.daily_returns)
            metrics.sharpe_ratio = (
                np.mean(returns_array) / np.std(returns_array) * np.sqrt(252)
                if np.std(returns_array) > 0 else 0
            )
        
        # Sortino ratio (only downside deviation)
        if len(self.daily_returns) > 1:
            returns_array = np.array(self.daily_returns)
            negative_returns = returns_array[returns_array < 0]
            if len(negative_returns) > 0:
                downside_std = np.std(negative_returns)
                metrics.sortino_ratio = (
                    np.mean(returns_array) / downside_std * np.sqrt(252)
                    if downside_std > 0 else 0
                )
        
        # Drawdown
        metrics.max_drawdown = self.peak_balance - min(eq[1] for eq in self.equity_curve)
        metrics.max_drawdown_percent = (metrics.max_drawdown / self.peak_balance) * 100
        metrics.current_drawdown = self.peak_balance - self.current_balance
        
        # Trade metrics
        hold_times = [
            (t['exit_time'] - t['entry_time']).total_seconds() / 3600
            for t in self.trades
        ]
        metrics.avg_hold_time_hours = np.mean(hold_times) if hold_times else 0
        
        # R-multiple (average profit/loss ratio)
        r_multiples = []
        for t in self.trades:
            if 'risk_amount' in t and t['risk_amount'] > 0:
                r_multiple = t['pnl'] / t['risk_amount']
                r_multiples.append(r_multiple)
        metrics.avg_r_multiple = np.mean(r_multiples) if r_multiples else 0
        
        # Expectancy (average $ per trade)
        metrics.expectancy = metrics.total_pnl / metrics.total_trades if metrics.total_trades > 0 else 0
        
        # Streaks
        metrics.current_streak = self.current_streak
        metrics.max_win_streak = self.max_win_streak
        metrics.max_loss_streak = self.max_loss_streak
        
        # Time-based P&L
        now = datetime.utcnow()
        metrics.daily_pnl = self._get_pnl_since(now - timedelta(days=1))
        metrics.weekly_pnl = self._get_pnl_since(now - timedelta(days=7))
        metrics.monthly_pnl = self._get_pnl_since(now - timedelta(days=30))
        
        return metrics
    
    def _get_pnl_since(self, since: datetime) -> float:
        """Get P&L since a specific time"""
        return sum(
            t['pnl'] for t in self.trades
            if t['exit_time'] >= since
        )
    
    def get_strategy_metrics(self, strategy: str) -> Optional[PerformanceMetrics]:
        """Get metrics for specific strategy"""
        return self.strategy_performance.get(strategy)
    
    def get_all_strategy_metrics(self) -> Dict[str, PerformanceMetrics]:
        """Get metrics for all strategies"""
        return self.strategy_performance.copy()
    
    def get_equity_curve_df(self) -> pd.DataFrame:
        """Get equity curve as DataFrame"""
        df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
        df.set_index('timestamp', inplace=True)
        return df
    
    def get_trades_df(self) -> pd.DataFrame:
        """Get trades as DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)
    
    def get_performance_summary(self) -> str:
        """Get formatted performance summary"""
        metrics = self.get_overall_metrics()
        
        summary = f"""
╔══════════════════════════════════════════════════════════════╗
║                    PERFORMANCE SUMMARY                        ║
╠══════════════════════════════════════════════════════════════╣
║ ACCOUNT                                                       ║
║   Initial Balance:     ${self.initial_balance:>12,.2f}              ║
║   Current Balance:     ${self.current_balance:>12,.2f}              ║
║   Total P&L:           ${metrics.total_pnl:>12,.2f} ({metrics.total_pnl_percent:>+6.2f}%)   ║
║   Peak Balance:        ${self.peak_balance:>12,.2f}              ║
╠══════════════════════════════════════════════════════════════╣
║ TRADES                                                        ║
║   Total Trades:        {metrics.total_trades:>12}                    ║
║   Winning Trades:      {metrics.winning_trades:>12}                    ║
║   Losing Trades:       {metrics.losing_trades:>12}                    ║
║   Win Rate:            {metrics.win_rate:>12.1%}                  ║
╠══════════════════════════════════════════════════════════════╣
║ PROFIT/LOSS                                                   ║
║   Average Win:         ${metrics.avg_win:>12,.2f}              ║
║   Average Loss:        ${metrics.avg_loss:>12,.2f}              ║
║   Largest Win:         ${metrics.largest_win:>12,.2f}              ║
║   Largest Loss:        ${metrics.largest_loss:>12,.2f}              ║
║   Profit Factor:       {metrics.profit_factor:>12.2f}                  ║
║   Expectancy:          ${metrics.expectancy:>12,.2f}              ║
╠══════════════════════════════════════════════════════════════╣
║ RISK METRICS                                                  ║
║   Sharpe Ratio:        {metrics.sharpe_ratio:>12.2f}                  ║
║   Sortino Ratio:       {metrics.sortino_ratio:>12.2f}                  ║
║   Max Drawdown:        ${metrics.max_drawdown:>12,.2f} ({metrics.max_drawdown_percent:>5.2f}%)   ║
║   Current Drawdown:    ${metrics.current_drawdown:>12,.2f}              ║
║   Avg R-Multiple:      {metrics.avg_r_multiple:>12.2f}                  ║
╠══════════════════════════════════════════════════════════════╣
║ STREAKS                                                       ║
║   Current Streak:      {metrics.current_streak:>12}                    ║
║   Max Win Streak:      {metrics.max_win_streak:>12}                    ║
║   Max Loss Streak:     {metrics.max_loss_streak:>12}                    ║
╠══════════════════════════════════════════════════════════════╣
║ TIME-BASED P&L                                                ║
║   Today:               ${metrics.daily_pnl:>12,.2f}              ║
║   This Week:           ${metrics.weekly_pnl:>12,.2f}              ║
║   This Month:          ${metrics.monthly_pnl:>12,.2f}              ║
╠══════════════════════════════════════════════════════════════╣
║ TRADE METRICS                                                 ║
║   Avg Hold Time:       {metrics.avg_hold_time_hours:>12.1f} hours         ║
╚══════════════════════════════════════════════════════════════╝
"""
        return summary
    
    def print_summary(self):
        """Print performance summary"""
        print(self.get_performance_summary())
    
    def export_to_dict(self) -> Dict:
        """Export all data to dictionary"""
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'overall_metrics': self.get_overall_metrics().__dict__,
            'strategy_metrics': {
                name: metrics.__dict__
                for name, metrics in self.strategy_performance.items()
            },
            'trades': self.trades,
            'equity_curve': [(t.isoformat(), eq) for t, eq in self.equity_curve]
        }
