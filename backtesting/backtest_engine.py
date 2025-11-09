"""
Backtest Engine - Professional-grade backtesting framework
Event-driven architecture with realistic execution simulation
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np
from dataclasses import dataclass, field


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    initial_balance: float = 10000.0
    commission_rate: float = 0.001  # 0.1% per trade
    slippage_rate: float = 0.0005  # 0.05% slippage
    max_position_size: float = 2500.0
    max_total_exposure: float = 10000.0
    max_daily_loss: float = 500.0
    enable_stop_loss: bool = True
    enable_take_profit: bool = True
    enable_time_stops: bool = True
    max_hold_time_hours: int = 72  # Close position after 72 hours


@dataclass
class Trade:
    """Trade record"""
    entry_time: datetime
    entry_price: float
    position_size: float
    action: str  # 'BUY' or 'SELL'
    strategy: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    hold_time_hours: float = 0.0
    
    def close(self, exit_time: datetime, exit_price: float, exit_reason: str, commission_rate: float, slippage_rate: float):
        """Close the trade and calculate P&L"""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        
        # Calculate hold time
        self.hold_time_hours = (exit_time - self.entry_time).total_seconds() / 3600
        
        # Calculate P&L
        if self.action == 'BUY':
            price_change = exit_price - self.entry_price
        else:  # SELL
            price_change = self.entry_price - exit_price
        
        gross_pnl = price_change * self.position_size / self.entry_price
        
        # Calculate costs
        self.commission = (self.entry_price * self.position_size * commission_rate + 
                          exit_price * self.position_size * commission_rate)
        self.slippage = (self.entry_price * self.position_size * slippage_rate + 
                        exit_price * self.position_size * slippage_rate)
        
        # Net P&L
        self.pnl = gross_pnl - self.commission - self.slippage
        self.pnl_percent = (self.pnl / self.position_size) * 100 if self.position_size > 0 else 0


class BacktestEngine:
    """
    Professional backtesting engine with event-driven architecture
    
    Features:
    - Realistic order execution
    - Commission and slippage modeling
    - Stop loss and take profit simulation
    - Time-based exits
    - Portfolio tracking
    - Performance metrics
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
        # Portfolio state
        self.balance = config.initial_balance
        self.initial_balance = config.initial_balance
        self.equity = config.initial_balance
        self.peak_equity = config.initial_balance
        
        # Positions and trades
        self.open_positions: List[Trade] = []
        self.closed_trades: List[Trade] = []
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.total_commission = 0.0
        self.total_slippage = 0.0
        
        # Equity curve
        self.equity_curve: List[Tuple[datetime, float]] = []
        
        logger.info(f"✓ Backtest Engine initialized with ${config.initial_balance:,.2f}")
    
    def run_backtest(
        self,
        data: pd.DataFrame,
        strategy,
        symbol: str
    ) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            data: OHLCV dataframe with datetime index
            strategy: Strategy instance with analyze() method
            symbol: Trading pair symbol
        
        Returns:
            Backtest results dictionary
        """
        logger.info(f"🔄 Running backtest on {symbol} from {data.index[0]} to {data.index[-1]}")
        logger.info(f"📊 Data points: {len(data)}, Initial balance: ${self.initial_balance:,.2f}")
        
        # Reset state
        self._reset()
        
        # Event loop - process each candle
        for i in range(len(data)):
            current_time = data.index[i]
            current_candle = data.iloc[i]
            
            # Update equity curve
            self._update_equity(current_time, current_candle['close'])
            
            # Check open positions for exits
            self._check_exits(current_time, current_candle)
            
            # Check if we can take new positions
            if self._can_trade():
                # Get strategy signal using data up to current point
                historical_data = data.iloc[:i+1]
                signal = strategy.analyze(historical_data, symbol)
                
                if signal and signal.action != 'HOLD':
                    self._execute_signal(signal, current_time, current_candle['close'])
        
        # Close any remaining positions at end
        if self.open_positions:
            final_time = data.index[-1]
            final_price = data.iloc[-1]['close']
            for position in self.open_positions[:]:
                position.close(
                    final_time,
                    final_price,
                    'END_OF_BACKTEST',
                    self.config.commission_rate,
                    self.config.slippage_rate
                )
                self.closed_trades.append(position)
                self.open_positions.remove(position)
                self.balance += position.pnl
        
        # Calculate final metrics
        results = self._calculate_metrics()
        
        logger.success(f"✅ Backtest complete: {len(self.closed_trades)} trades, Final balance: ${self.balance:,.2f}")
        
        return results
    
    def _reset(self):
        """Reset backtest state"""
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.peak_equity = self.initial_balance
        self.open_positions = []
        self.closed_trades = []
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.total_commission = 0.0
        self.total_slippage = 0.0
        self.equity_curve = []
    
    def _can_trade(self) -> bool:
        """Check if we can take new trades"""
        # Daily loss limit
        if abs(self.daily_pnl) >= self.config.max_daily_loss:
            return False
        
        # Max positions
        if len(self.open_positions) >= 5:  # Max 5 concurrent positions
            return False
        
        # Exposure limit
        current_exposure = sum(p.position_size for p in self.open_positions)
        if current_exposure >= self.config.max_total_exposure:
            return False
        
        return True
    
    def _execute_signal(self, signal, current_time: datetime, current_price: float):
        """Execute trading signal"""
        # Calculate position size
        position_size = min(
            signal.strength * self.config.max_position_size,
            self.config.max_position_size,
            self.balance * 0.2  # Max 20% of balance per trade
        )
        
        # Check if we have enough balance
        if position_size < 50:  # Minimum $50
            return
        
        # Apply slippage to entry
        if signal.action == 'BUY':
            entry_price = current_price * (1 + self.config.slippage_rate)
        else:
            entry_price = current_price * (1 - self.config.slippage_rate)
        
        # Create trade
        trade = Trade(
            entry_time=current_time,
            entry_price=entry_price,
            position_size=position_size,
            action=signal.action,
            strategy=signal.strategy,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        
        self.open_positions.append(trade)
        
        logger.debug(
            f"📈 {signal.action} {position_size:.2f} @ ${entry_price:.2f} "
            f"(SL: ${signal.stop_loss:.2f}, TP: ${signal.take_profit:.2f})"
        )
    
    def _check_exits(self, current_time: datetime, candle: pd.Series):
        """Check if any open positions should be closed"""
        for position in self.open_positions[:]:  # Copy list to allow removal
            should_exit, exit_reason = self._should_exit(position, current_time, candle)
            
            if should_exit:
                # Determine exit price
                if exit_reason == 'STOP_LOSS':
                    exit_price = position.stop_loss
                elif exit_reason == 'TAKE_PROFIT':
                    exit_price = position.take_profit
                else:
                    exit_price = candle['close']
                
                # Close position
                position.close(
                    current_time,
                    exit_price,
                    exit_reason,
                    self.config.commission_rate,
                    self.config.slippage_rate
                )
                
                # Update balances
                self.balance += position.pnl
                self.daily_pnl += position.pnl
                self.total_pnl += position.pnl
                self.total_commission += position.commission
                self.total_slippage += position.slippage
                
                # Move to closed trades
                self.closed_trades.append(position)
                self.open_positions.remove(position)
                
                logger.debug(
                    f"📉 CLOSE {position.action} @ ${exit_price:.2f} "
                    f"({exit_reason}) P&L: ${position.pnl:.2f} ({position.pnl_percent:+.2f}%)"
                )
    
    def _should_exit(self, position: Trade, current_time: datetime, candle: pd.Series) -> Tuple[bool, str]:
        """Check if position should be exited"""
        # Stop loss
        if self.config.enable_stop_loss and position.stop_loss:
            if position.action == 'BUY' and candle['low'] <= position.stop_loss:
                return True, 'STOP_LOSS'
            elif position.action == 'SELL' and candle['high'] >= position.stop_loss:
                return True, 'STOP_LOSS'
        
        # Take profit
        if self.config.enable_take_profit and position.take_profit:
            if position.action == 'BUY' and candle['high'] >= position.take_profit:
                return True, 'TAKE_PROFIT'
            elif position.action == 'SELL' and candle['low'] <= position.take_profit:
                return True, 'TAKE_PROFIT'
        
        # Time stop
        if self.config.enable_time_stops:
            hold_time_hours = (current_time - position.entry_time).total_seconds() / 3600
            if hold_time_hours >= self.config.max_hold_time_hours:
                return True, 'TIME_STOP'
        
        return False, ''
    
    def _update_equity(self, current_time: datetime, current_price: float):
        """Update equity curve"""
        # Calculate unrealized P&L
        unrealized_pnl = 0.0
        for position in self.open_positions:
            if position.action == 'BUY':
                price_change = current_price - position.entry_price
            else:
                price_change = position.entry_price - current_price
            
            unrealized_pnl += price_change * position.position_size / position.entry_price
        
        # Total equity
        self.equity = self.balance + unrealized_pnl
        
        # Update peak
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        # Record equity curve
        self.equity_curve.append((current_time, self.equity))
    
    def _calculate_metrics(self) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'final_balance': self.balance,
                'total_return': 0.0,
                'total_return_percent': 0.0
            }
        
        # Basic metrics
        total_trades = len(self.closed_trades)
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # P&L metrics
        total_return = self.balance - self.initial_balance
        total_return_percent = (total_return / self.initial_balance) * 100
        
        avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Drawdown
        max_drawdown = 0.0
        peak = self.initial_balance
        for _, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Sharpe ratio (simplified - assumes daily returns)
        returns = [t.pnl_percent for t in self.closed_trades]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if len(returns) > 1 else 0
        
        # Average hold time
        avg_hold_time = np.mean([t.hold_time_hours for t in self.closed_trades])
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'final_balance': self.balance,
            'initial_balance': self.initial_balance,
            'total_return': total_return,
            'total_return_percent': total_return_percent,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'max_drawdown_percent': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'total_commission': self.total_commission,
            'total_slippage': self.total_slippage,
            'avg_hold_time_hours': avg_hold_time,
            'trades': self.closed_trades,
            'equity_curve': self.equity_curve
        }
    
    def print_results(self, results: Dict):
        """Print backtest results in a formatted way"""
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Initial Balance:     ${results['initial_balance']:,.2f}")
        print(f"Final Balance:       ${results['final_balance']:,.2f}")
        print(f"Total Return:        ${results['total_return']:,.2f} ({results['total_return_percent']:+.2f}%)")
        print(f"\nTotal Trades:        {results['total_trades']}")
        print(f"Winning Trades:      {results['winning_trades']}")
        print(f"Losing Trades:       {results['losing_trades']}")
        print(f"Win Rate:            {results['win_rate']:.1%}")
        print(f"\nAverage Win:         ${results['avg_win']:.2f}")
        print(f"Average Loss:        ${results['avg_loss']:.2f}")
        print(f"Profit Factor:       {results['profit_factor']:.2f}")
        print(f"\nMax Drawdown:        {results['max_drawdown_percent']:.2f}%")
        print(f"Sharpe Ratio:        {results['sharpe_ratio']:.2f}")
        print(f"\nTotal Commission:    ${results['total_commission']:.2f}")
        print(f"Total Slippage:      ${results['total_slippage']:.2f}")
        print(f"Avg Hold Time:       {results['avg_hold_time_hours']:.1f} hours")
        print("="*60 + "\n")
