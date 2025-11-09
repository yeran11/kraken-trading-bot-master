#!/usr/bin/env python3
"""
Run Backtest - Simple script to run backtests on strategies
"""
import sys
import os
from datetime import datetime, timedelta
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtesting.backtest_engine import BacktestEngine, BacktestConfig
from backtesting.data_manager import DataManager
from strategies import MomentumStrategy, MeanReversionStrategy, ScalpingStrategy
from strategies_advanced import (
    BreakoutStrategy,
    TrendFollowingStrategy,
    SupportResistanceStrategy
)


def run_simple_backtest():
    """Run a simple backtest example"""
    
    print("\n" + "="*60)
    print("KRAKEN TRADING BOT - BACKTEST")
    print("="*60 + "\n")
    
    # Configuration
    symbol = 'BTC/USD'
    timeframe = '1h'
    days_back = 90
    
    # Dates
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)
    
    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    print(f"Period: {start_date.date()} to {end_date.date()} ({days_back} days)")
    print()
    
    # Initialize data manager
    data_manager = DataManager()
    
    # Fetch data
    print("📡 Fetching historical data...")
    df = data_manager.fetch_ohlcv(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date
    )
    
    if df.empty:
        print("❌ Failed to fetch data")
        return
    
    print(f"✅ Loaded {len(df)} candles\n")
    
    # Backtest configuration
    config = BacktestConfig(
        initial_balance=10000.0,
        commission_rate=0.001,  # 0.1%
        slippage_rate=0.0005,   # 0.05%
        max_position_size=2500.0,
        max_total_exposure=10000.0,
        max_daily_loss=500.0
    )
    
    # Strategies to test
    strategies = {
        'Momentum': MomentumStrategy(),
        'Mean Reversion': MeanReversionStrategy(),
        'Breakout': BreakoutStrategy(),
        'Trend Following': TrendFollowingStrategy(),
        'Support/Resistance': SupportResistanceStrategy()
    }
    
    # Run backtests
    results = {}
    
    for strategy_name, strategy in strategies.items():
        print(f"\n{'='*60}")
        print(f"Testing: {strategy_name}")
        print('='*60)
        
        # Create engine
        engine = BacktestEngine(config)
        
        # Run backtest
        result = engine.run_backtest(df, strategy, symbol)
        
        # Store results
        results[strategy_name] = result
        
        # Print results
        engine.print_results(result)
    
    # Compare strategies
    print("\n" + "="*60)
    print("STRATEGY COMPARISON")
    print("="*60)
    print(f"{'Strategy':<20} {'Return':<12} {'Win Rate':<10} {'Trades':<8} {'Sharpe':<8}")
    print("-"*60)
    
    for strategy_name, result in results.items():
        print(
            f"{strategy_name:<20} "
            f"{result['total_return_percent']:>+10.2f}% "
            f"{result['win_rate']:>8.1%} "
            f"{result['total_trades']:>7} "
            f"{result['sharpe_ratio']:>7.2f}"
        )
    
    print("="*60 + "\n")
    
    # Find best strategy
    best_strategy = max(results.items(), key=lambda x: x[1]['total_return_percent'])
    print(f"🏆 Best Strategy: {best_strategy[0]} ({best_strategy[1]['total_return_percent']:+.2f}%)")
    print()


if __name__ == '__main__':
    try:
        run_simple_backtest()
    except KeyboardInterrupt:
        print("\n\n⚠️  Backtest interrupted by user")
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        import traceback
        traceback.print_exc()
