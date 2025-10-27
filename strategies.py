"""
Trading Strategies for Kraken Bot - Optimized Implementation
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import ta as ta_lib
from scipy import stats
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

import config
from risk_manager import RiskManager


class Signal:
    """Trading signal representation"""
    def __init__(self, symbol: str, action: str, strength: float,
                 strategy: str, reason: str, **kwargs):
        self.symbol = symbol
        self.action = action  # BUY/SELL/HOLD
        self.strength = strength  # 0-1
        self.strategy = strategy
        self.reason = reason
        self.timestamp = datetime.utcnow()
        self.indicators = kwargs.get('indicators', {})
        self.confidence = kwargs.get('confidence', 0.5)
        self.stop_loss = kwargs.get('stop_loss')
        self.take_profit = kwargs.get('take_profit')
        self.timeframe = kwargs.get('timeframe', '5m')

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'action': self.action,
            'strength': self.strength,
            'strategy': self.strategy,
            'reason': self.reason,
            'confidence': self.confidence,
            'indicators': self.indicators,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'timestamp': self.timestamp.isoformat()
        }


class TechnicalIndicators:
    """Optimized technical indicator calculations using ta library"""

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators"""
        try:
            # Ensure we have enough data
            if len(df) < 50:
                return df

            # Trend Indicators
            df['SMA_20'] = ta_lib.trend.SMAIndicator(df['close'], window=20).sma_indicator()
            df['SMA_50'] = ta_lib.trend.SMAIndicator(df['close'], window=50).sma_indicator()
            df['EMA_12'] = ta_lib.trend.EMAIndicator(df['close'], window=12).ema_indicator()
            df['EMA_26'] = ta_lib.trend.EMAIndicator(df['close'], window=26).ema_indicator()

            # MACD
            macd = ta_lib.trend.MACD(df['close'])
            df['MACD'] = macd.macd()
            df['MACD_SIGNAL'] = macd.macd_signal()
            df['MACD_HIST'] = macd.macd_diff()

            # RSI
            df['RSI'] = ta_lib.momentum.RSIIndicator(df['close'], window=14).rsi()

            # Stochastic
            stoch = ta_lib.momentum.StochasticOscillator(
                df['high'], df['low'], df['close'],
                window=14, smooth_window=3
            )
            df['STOCH_K'] = stoch.stoch()
            df['STOCH_D'] = stoch.stoch_signal()

            # Bollinger Bands
            bb = ta_lib.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['BB_UPPER'] = bb.bollinger_hband()
            df['BB_MIDDLE'] = bb.bollinger_mavg()
            df['BB_LOWER'] = bb.bollinger_lband()
            df['BB_PERCENT'] = bb.bollinger_pband()
            df['BB_WIDTH'] = bb.bollinger_wband()

            # ATR (Average True Range)
            df['ATR'] = ta_lib.volatility.AverageTrueRange(
                df['high'], df['low'], df['close'], window=14
            ).average_true_range()

            # ADX (Average Directional Index)
            df['ADX'] = ta_lib.trend.ADXIndicator(
                df['high'], df['low'], df['close'], window=14
            ).adx()

            # CCI (Commodity Channel Index)
            df['CCI'] = ta_lib.trend.CCIIndicator(
                df['high'], df['low'], df['close'], window=20
            ).cci()

            # MFI (Money Flow Index)
            df['MFI'] = ta_lib.volume.MFIIndicator(
                df['high'], df['low'], df['close'], df['volume'], window=14
            ).money_flow_index()

            # OBV (On Balance Volume)
            df['OBV'] = ta_lib.volume.OnBalanceVolumeIndicator(
                df['close'], df['volume']
            ).on_balance_volume()

            # VWAP (Volume Weighted Average Price)
            df['VWAP'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()

            # Volume indicators
            df['VOLUME_SMA'] = df['volume'].rolling(window=20).mean()
            df['VOLUME_RATIO'] = df['volume'] / df['VOLUME_SMA']

            # Volatility
            df['RETURNS'] = df['close'].pct_change()
            df['VOLATILITY'] = df['RETURNS'].rolling(window=20).std()

            # Support and Resistance levels
            df['PIVOT'] = (df['high'] + df['low'] + df['close']) / 3
            df['R1'] = 2 * df['PIVOT'] - df['low']
            df['S1'] = 2 * df['PIVOT'] - df['high']
            df['R2'] = df['PIVOT'] + (df['high'] - df['low'])
            df['S2'] = df['PIVOT'] - (df['high'] - df['low'])

            return df

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df


class BaseStrategy(ABC):
    """Base class for all trading strategies"""

    def __init__(self, name: str):
        self.name = name
        self.indicators = TechnicalIndicators()
        self.min_data_points = 100
        self.confidence_threshold = 0.5

    @abstractmethod
    def analyze(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Analyze market data and generate signal"""
        pass

    def validate_dataframe(self, df: pd.DataFrame) -> bool:
        """Validate input dataframe"""
        if df is None or df.empty:
            return False
        if len(df) < self.min_data_points:
            logger.warning(f"Insufficient data: {len(df)} < {self.min_data_points}")
            return False
        return True

    def calculate_stop_loss(self, df: pd.DataFrame, side: str) -> float:
        """Calculate dynamic stop loss based on ATR"""
        try:
            atr = df['ATR'].iloc[-1]
            current_price = df['close'].iloc[-1]

            if side == 'BUY':
                stop_loss = current_price - (2 * atr)
            else:
                stop_loss = current_price + (2 * atr)

            return stop_loss
        except:
            return None

    def calculate_take_profit(self, df: pd.DataFrame, side: str) -> float:
        """Calculate dynamic take profit based on ATR"""
        try:
            atr = df['ATR'].iloc[-1]
            current_price = df['close'].iloc[-1]

            if side == 'BUY':
                take_profit = current_price + (3 * atr)
            else:
                take_profit = current_price - (3 * atr)

            return take_profit
        except:
            return None


class MomentumStrategy(BaseStrategy):
    """Momentum-based trading strategy"""

    def __init__(self):
        super().__init__('momentum')
        self.lookback_period = 20
        self.momentum_threshold = 0.02
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.adx_threshold = 25

    def analyze(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Analyze for momentum signals"""
        try:
            if not self.validate_dataframe(df):
                return None

            # Calculate indicators
            df = self.indicators.calculate_all(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # Calculate momentum
            momentum = (latest['close'] - df['close'].iloc[-self.lookback_period]) / df['close'].iloc[-self.lookback_period]

            # Trend strength
            trend_strength = latest['ADX'] if not pd.isna(latest['ADX']) else 0

            # BULLISH MOMENTUM SIGNAL
            if (momentum > self.momentum_threshold and
                latest['RSI'] > 50 and latest['RSI'] < self.rsi_overbought and
                latest['MACD'] > latest['MACD_SIGNAL'] and
                trend_strength > self.adx_threshold and
                latest['close'] > latest['SMA_20']):

                confidence = min(0.9, (momentum / 0.05) * (trend_strength / 50))

                return Signal(
                    symbol=symbol,
                    action='BUY',
                    strength=min(momentum / 0.05, 1.0),
                    strategy=self.name,
                    reason=f'Strong bullish momentum ({momentum*100:.2f}%)',
                    confidence=confidence,
                    stop_loss=self.calculate_stop_loss(df, 'BUY'),
                    take_profit=self.calculate_take_profit(df, 'BUY'),
                    indicators={
                        'momentum': momentum * 100,
                        'RSI': latest['RSI'],
                        'ADX': trend_strength,
                        'MACD': latest['MACD']
                    }
                )

            # BEARISH MOMENTUM SIGNAL
            elif (momentum < -self.momentum_threshold and
                  latest['RSI'] < 50 and latest['RSI'] > self.rsi_oversold and
                  latest['MACD'] < latest['MACD_SIGNAL'] and
                  trend_strength > self.adx_threshold and
                  latest['close'] < latest['SMA_20']):

                confidence = min(0.9, (abs(momentum) / 0.05) * (trend_strength / 50))

                return Signal(
                    symbol=symbol,
                    action='SELL',
                    strength=min(abs(momentum) / 0.05, 1.0),
                    strategy=self.name,
                    reason=f'Strong bearish momentum ({momentum*100:.2f}%)',
                    confidence=confidence,
                    stop_loss=self.calculate_stop_loss(df, 'SELL'),
                    take_profit=self.calculate_take_profit(df, 'SELL'),
                    indicators={
                        'momentum': momentum * 100,
                        'RSI': latest['RSI'],
                        'ADX': trend_strength,
                        'MACD': latest['MACD']
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Momentum strategy error: {e}")
            return None


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion trading strategy"""

    def __init__(self):
        super().__init__('mean_reversion')
        self.bb_period = 20
        self.bb_std = 2
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.cci_oversold = -100
        self.cci_overbought = 100

    def analyze(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Analyze for mean reversion opportunities"""
        try:
            if not self.validate_dataframe(df):
                return None

            df = self.indicators.calculate_all(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # Check for Bollinger Band squeeze (low volatility)
            bb_squeeze = latest['BB_WIDTH'] < df['BB_WIDTH'].rolling(50).mean().iloc[-1]

            # OVERSOLD BOUNCE SIGNAL
            if (latest['close'] < latest['BB_LOWER'] and
                latest['RSI'] < self.rsi_oversold and
                latest['CCI'] < self.cci_oversold and
                latest['close'] > prev['close'] and  # Starting to bounce
                latest['STOCH_K'] < 20 and latest['STOCH_K'] > prev['STOCH_K']):

                # Calculate distance from mean
                distance_from_mean = (latest['BB_MIDDLE'] - latest['close']) / latest['close']
                confidence = min(0.85, distance_from_mean * 10)

                return Signal(
                    symbol=symbol,
                    action='BUY',
                    strength=min(distance_from_mean * 10, 0.9),
                    strategy=self.name,
                    reason='Oversold bounce from Bollinger Band',
                    confidence=confidence,
                    stop_loss=latest['close'] * 0.98,  # Tight stop for mean reversion
                    take_profit=latest['BB_MIDDLE'],  # Target the mean
                    indicators={
                        'RSI': latest['RSI'],
                        'CCI': latest['CCI'],
                        'BB_PERCENT': latest['BB_PERCENT'],
                        'distance_from_mean': distance_from_mean * 100,
                        'bb_squeeze': bb_squeeze
                    }
                )

            # OVERBOUGHT REVERSAL SIGNAL
            elif (latest['close'] > latest['BB_UPPER'] and
                  latest['RSI'] > self.rsi_overbought and
                  latest['CCI'] > self.cci_overbought and
                  latest['close'] < prev['close'] and  # Starting to reverse
                  latest['STOCH_K'] > 80 and latest['STOCH_K'] < prev['STOCH_K']):

                distance_from_mean = (latest['close'] - latest['BB_MIDDLE']) / latest['close']
                confidence = min(0.85, distance_from_mean * 10)

                return Signal(
                    symbol=symbol,
                    action='SELL',
                    strength=min(distance_from_mean * 10, 0.9),
                    strategy=self.name,
                    reason='Overbought reversal from Bollinger Band',
                    confidence=confidence,
                    stop_loss=latest['close'] * 1.02,
                    take_profit=latest['BB_MIDDLE'],
                    indicators={
                        'RSI': latest['RSI'],
                        'CCI': latest['CCI'],
                        'BB_PERCENT': latest['BB_PERCENT'],
                        'distance_from_mean': distance_from_mean * 100,
                        'bb_squeeze': bb_squeeze
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Mean reversion strategy error: {e}")
            return None


class ScalpingStrategy(BaseStrategy):
    """High-frequency scalping strategy for quick profits"""

    def __init__(self):
        super().__init__('scalping')
        self.min_data_points = 50  # Need less data for scalping
        self.min_volume_ratio = 1.5
        self.price_move_threshold = 0.001  # 0.1%
        self.quick_profit = 0.003  # 0.3%
        self.tight_stop = 0.002  # 0.2%

    def analyze(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Analyze for quick scalping opportunities"""
        try:
            if not self.validate_dataframe(df):
                return None

            df = self.indicators.calculate_all(df)
            latest = df.iloc[-1]

            # Recent price action (last 5 candles)
            recent_data = df.iloc[-5:]
            price_change = (latest['close'] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]

            # Volume surge detection
            volume_surge = latest['VOLUME_RATIO'] > self.min_volume_ratio

            # Micro-structure analysis
            spread = (latest['high'] - latest['low']) / latest['close']
            is_trending = abs(latest['close'] - latest['open']) / (latest['high'] - latest['low']) > 0.7

            # SCALP BUY SIGNAL
            if (volume_surge and
                price_change > self.price_move_threshold and
                latest['RSI'] > 40 and latest['RSI'] < 65 and
                latest['MFI'] > 50 and
                is_trending and
                latest['close'] > latest['VWAP']):

                return Signal(
                    symbol=symbol,
                    action='BUY',
                    strength=0.7,  # Lower strength for scalping
                    strategy=self.name,
                    reason='Volume surge scalp opportunity',
                    confidence=0.65,
                    stop_loss=latest['close'] * (1 - self.tight_stop),
                    take_profit=latest['close'] * (1 + self.quick_profit),
                    indicators={
                        'price_change': price_change * 100,
                        'volume_ratio': latest['VOLUME_RATIO'],
                        'RSI': latest['RSI'],
                        'MFI': latest['MFI'],
                        'spread': spread * 100
                    }
                )

            # MICRO-REVERSAL SCALP
            elif (latest['RSI'] < 25 and
                  latest['STOCH_K'] < 20 and
                  latest['close'] > latest['open'] and  # Green candle in oversold
                  latest['close'] > latest['S1']):  # Above support

                return Signal(
                    symbol=symbol,
                    action='BUY',
                    strength=0.6,
                    strategy=self.name,
                    reason='Oversold micro-reversal',
                    confidence=0.6,
                    stop_loss=latest['S1'],
                    take_profit=latest['close'] * (1 + self.quick_profit),
                    indicators={
                        'RSI': latest['RSI'],
                        'STOCH_K': latest['STOCH_K'],
                        'support': latest['S1']
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Scalping strategy error: {e}")
            return None


class GridTradingStrategy(BaseStrategy):
    """Grid trading strategy for ranging markets"""

    def __init__(self):
        super().__init__('grid')
        self.grid_levels = 10
        self.grid_spacing = 0.005  # 0.5% between levels
        self.range_period = 24  # Hours to determine range

    def analyze(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Analyze for grid trading setup"""
        try:
            if not self.validate_dataframe(df):
                return None

            df = self.indicators.calculate_all(df)

            # Detect ranging market
            recent_data = df.iloc[-self.range_period:]
            price_range = (recent_data['high'].max() - recent_data['low'].min()) / recent_data['close'].mean()
            is_ranging = price_range < 0.05 and df['ADX'].iloc[-1] < 25

            if not is_ranging:
                return None

            latest = df.iloc[-1]
            current_price = latest['close']

            # Calculate grid levels
            upper_range = recent_data['high'].max()
            lower_range = recent_data['low'].min()
            mid_range = (upper_range + lower_range) / 2

            # Generate signal based on position in range
            position_in_range = (current_price - lower_range) / (upper_range - lower_range)

            # BUY at lower levels of range
            if position_in_range < 0.3:
                return Signal(
                    symbol=symbol,
                    action='BUY',
                    strength=0.5,
                    strategy=self.name,
                    reason=f'Grid buy at lower range ({position_in_range*100:.1f}%)',
                    confidence=0.7,
                    stop_loss=lower_range * 0.98,
                    take_profit=mid_range,
                    indicators={
                        'position_in_range': position_in_range * 100,
                        'range_size': price_range * 100,
                        'ADX': df['ADX'].iloc[-1]
                    }
                )

            # SELL at upper levels of range
            elif position_in_range > 0.7:
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    strength=0.5,
                    strategy=self.name,
                    reason=f'Grid sell at upper range ({position_in_range*100:.1f}%)',
                    confidence=0.7,
                    stop_loss=upper_range * 1.02,
                    take_profit=mid_range,
                    indicators={
                        'position_in_range': position_in_range * 100,
                        'range_size': price_range * 100,
                        'ADX': df['ADX'].iloc[-1]
                    }
                )

            return None

        except Exception as e:
            logger.error(f"Grid strategy error: {e}")
            return None


class ArbitrageStrategy(BaseStrategy):
    """Arbitrage strategy for price discrepancies"""

    def __init__(self):
        super().__init__('arbitrage')
        self.min_spread = 0.002  # 0.2% minimum spread
        self.confidence_threshold = 0.7

    def analyze(self, symbol: str, df: pd.DataFrame) -> Optional[Signal]:
        """Analyze for arbitrage opportunities"""
        # This would typically compare prices across different markets
        # For now, we'll look for price inefficiencies in the order book
        try:
            if not self.validate_dataframe(df):
                return None

            df = self.indicators.calculate_all(df)
            latest = df.iloc[-1]

            # Detect price inefficiency
            price_vs_vwap = (latest['close'] - latest['VWAP']) / latest['VWAP']

            # Significant deviation from VWAP with volume
            if abs(price_vs_vwap) > self.min_spread and latest['VOLUME_RATIO'] > 2:

                if price_vs_vwap < -self.min_spread:
                    # Price below VWAP - potential buy
                    return Signal(
                        symbol=symbol,
                        action='BUY',
                        strength=0.6,
                        strategy=self.name,
                        reason=f'Price below VWAP by {abs(price_vs_vwap)*100:.2f}%',
                        confidence=0.65,
                        stop_loss=latest['close'] * 0.995,
                        take_profit=latest['VWAP'],
                        indicators={
                            'price_vs_vwap': price_vs_vwap * 100,
                            'volume_ratio': latest['VOLUME_RATIO']
                        }
                    )

                elif price_vs_vwap > self.min_spread:
                    # Price above VWAP - potential sell
                    return Signal(
                        symbol=symbol,
                        action='SELL',
                        strength=0.6,
                        strategy=self.name,
                        reason=f'Price above VWAP by {price_vs_vwap*100:.2f}%',
                        confidence=0.65,
                        stop_loss=latest['close'] * 1.005,
                        take_profit=latest['VWAP'],
                        indicators={
                            'price_vs_vwap': price_vs_vwap * 100,
                            'volume_ratio': latest['VOLUME_RATIO']
                        }
                    )

            return None

        except Exception as e:
            logger.error(f"Arbitrage strategy error: {e}")
            return None


class StrategyManager:
    """Manages all trading strategies"""

    def __init__(self, kraken_client, risk_manager: RiskManager):
        self.kraken_client = kraken_client
        self.risk_manager = risk_manager
        self.strategies = {}
        self.active_strategies = []

        # Initialize available strategies
        self.available_strategies = {
            'momentum': MomentumStrategy,
            'mean_reversion': MeanReversionStrategy,
            'scalping': ScalpingStrategy,
            'grid': GridTradingStrategy,
            'arbitrage': ArbitrageStrategy
        }

        logger.info("Strategy Manager initialized")

    def load_strategy(self, strategy_name: str) -> bool:
        """Load and initialize a strategy"""
        try:
            if strategy_name not in self.available_strategies:
                logger.error(f"Unknown strategy: {strategy_name}")
                return False

            if strategy_name not in self.strategies:
                strategy_class = self.available_strategies[strategy_name]
                self.strategies[strategy_name] = strategy_class()
                logger.info(f"Strategy loaded: {strategy_name}")

            return True

        except Exception as e:
            logger.error(f"Error loading strategy {strategy_name}: {e}")
            return False

    def enable_strategy(self, strategy_name: str) -> bool:
        """Enable a strategy for trading"""
        if strategy_name not in self.strategies:
            if not self.load_strategy(strategy_name):
                return False

        if strategy_name not in self.active_strategies:
            self.active_strategies.append(strategy_name)
            logger.info(f"Strategy enabled: {strategy_name}")

        return True

    def disable_strategy(self, strategy_name: str) -> bool:
        """Disable a strategy"""
        if strategy_name in self.active_strategies:
            self.active_strategies.remove(strategy_name)
            logger.info(f"Strategy disabled: {strategy_name}")
            return True
        return False

    def analyze_all(self, symbol: str, df: pd.DataFrame) -> List[Signal]:
        """Run all active strategies on given data"""
        signals = []

        for strategy_name in self.active_strategies:
            if strategy_name in self.strategies:
                try:
                    strategy = self.strategies[strategy_name]
                    signal = strategy.analyze(symbol, df)

                    if signal and signal.confidence >= strategy.confidence_threshold:
                        signals.append(signal)
                        logger.info(f"Signal generated by {strategy_name}: {signal.action} {symbol}")

                except Exception as e:
                    logger.error(f"Error in {strategy_name} strategy: {e}")

        return signals

    def get_consensus_signal(self, signals: List[Signal]) -> Optional[Signal]:
        """Get consensus signal from multiple strategies"""
        if not signals:
            return None

        # Group signals by action
        buy_signals = [s for s in signals if s.action == 'BUY']
        sell_signals = [s for s in signals if s.action == 'SELL']

        # Determine consensus action
        if len(buy_signals) > len(sell_signals):
            # Average the buy signals
            avg_strength = sum(s.strength for s in buy_signals) / len(buy_signals)
            avg_confidence = sum(s.confidence for s in buy_signals) / len(buy_signals)

            return Signal(
                symbol=buy_signals[0].symbol,
                action='BUY',
                strength=avg_strength,
                strategy='consensus',
                reason=f"Consensus from {len(buy_signals)} strategies",
                confidence=avg_confidence,
                stop_loss=min(s.stop_loss for s in buy_signals if s.stop_loss),
                take_profit=max(s.take_profit for s in buy_signals if s.take_profit)
            )

        elif len(sell_signals) > len(buy_signals):
            # Average the sell signals
            avg_strength = sum(s.strength for s in sell_signals) / len(sell_signals)
            avg_confidence = sum(s.confidence for s in sell_signals) / len(sell_signals)

            return Signal(
                symbol=sell_signals[0].symbol,
                action='SELL',
                strength=avg_strength,
                strategy='consensus',
                reason=f"Consensus from {len(sell_signals)} strategies",
                confidence=avg_confidence,
                stop_loss=max(s.stop_loss for s in sell_signals if s.stop_loss),
                take_profit=min(s.take_profit for s in sell_signals if s.take_profit)
            )

        return None

    def backtest_strategy(self, strategy_name: str, symbol: str,
                         df: pd.DataFrame, initial_balance: float = 10000) -> Dict:
        """Backtest a strategy on historical data"""
        if strategy_name not in self.strategies:
            if not self.load_strategy(strategy_name):
                return {}

        strategy = self.strategies[strategy_name]
        balance = initial_balance
        position = None
        trades = []

        for i in range(100, len(df)):
            current_df = df.iloc[:i+1].copy()
            signal = strategy.analyze(symbol, current_df)

            if signal:
                current_price = df.iloc[i]['close']

                if signal.action == 'BUY' and not position:
                    # Open position
                    position = {
                        'entry_price': current_price,
                        'entry_time': df.index[i],
                        'quantity': balance * 0.95 / current_price,
                        'stop_loss': signal.stop_loss,
                        'take_profit': signal.take_profit
                    }

                elif signal.action == 'SELL' and position:
                    # Close position
                    pnl = (current_price - position['entry_price']) * position['quantity']
                    balance += pnl

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': df.index[i],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'pnl': pnl,
                        'return': pnl / (position['entry_price'] * position['quantity']) * 100
                    })

                    position = None

        # Calculate metrics
        if trades:
            winning_trades = [t for t in trades if t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] < 0]

            metrics = {
                'initial_balance': initial_balance,
                'final_balance': balance,
                'total_return': ((balance - initial_balance) / initial_balance) * 100,
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(trades) * 100) if trades else 0,
                'avg_win': sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0,
                'avg_loss': sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0,
                'best_trade': max(t['pnl'] for t in trades),
                'worst_trade': min(t['pnl'] for t in trades),
                'trades': trades[:10]  # First 10 trades
            }

            return metrics

        return {
            'initial_balance': initial_balance,
            'final_balance': balance,
            'total_return': 0,
            'total_trades': 0,
            'message': 'No trades executed'
        }