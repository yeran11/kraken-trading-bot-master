"""
Advanced Trading Strategies for Master Trader
Professional-grade strategies for experienced traders
"""
from typing import Dict, Optional
import pandas as pd
import numpy as np
from loguru import logger
import ta as ta_lib

from strategies import Signal, TechnicalIndicators


class BreakoutStrategy:
    """
    Breakout Strategy - Trade consolidation breakouts with volume confirmation
    
    Best for: Ranging markets transitioning to trends
    Timeframe: 15m, 1h, 4h
    Win rate target: 55-65%
    """
    
    def __init__(self):
        self.name = "breakout"
        self.consolidation_periods = 20  # Periods to detect consolidation
        self.breakout_threshold = 1.5  # ATR multiplier for breakout
        self.volume_multiplier = 1.5  # Volume must be 1.5x average
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Detect and trade breakouts from consolidation"""
        try:
            if len(df) < 50:
                return None
            
            # Calculate indicators
            df = TechnicalIndicators.calculate_all(df)
            
            current_price = df['close'].iloc[-1]
            atr = df['ATR'].iloc[-1]
            
            # Detect consolidation (low volatility)
            recent_high = df['high'].iloc[-self.consolidation_periods:].max()
            recent_low = df['low'].iloc[-self.consolidation_periods:].min()
            consolidation_range = recent_high - recent_low
            
            is_consolidating = consolidation_range < (atr * 2)
            
            if not is_consolidating:
                return None
            
            # Check for breakout
            breakout_level_high = recent_high
            breakout_level_low = recent_low
            
            # Volume confirmation
            avg_volume = df['volume'].iloc[-20:-1].mean()
            current_volume = df['volume'].iloc[-1]
            volume_surge = current_volume > (avg_volume * self.volume_multiplier)
            
            # Bullish breakout
            if current_price > breakout_level_high and volume_surge:
                strength = min(0.9, 0.6 + (current_volume / avg_volume - 1.5) * 0.1)
                
                return Signal(
                    symbol=symbol,
                    action='BUY',
                    strength=strength,
                    strategy=self.name,
                    reason=f"Bullish breakout above ${breakout_level_high:.2f} with {current_volume/avg_volume:.1f}x volume",
                    indicators={
                        'breakout_level': breakout_level_high,
                        'volume_ratio': current_volume / avg_volume,
                        'consolidation_range': consolidation_range
                    },
                    stop_loss=breakout_level_high * 0.98,  # 2% below breakout
                    take_profit=current_price + (consolidation_range * 2),  # 2x range target
                    confidence=strength
                )
            
            # Bearish breakout
            elif current_price < breakout_level_low and volume_surge:
                strength = min(0.9, 0.6 + (current_volume / avg_volume - 1.5) * 0.1)
                
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    strength=strength,
                    strategy=self.name,
                    reason=f"Bearish breakdown below ${breakout_level_low:.2f} with {current_volume/avg_volume:.1f}x volume",
                    indicators={
                        'breakout_level': breakout_level_low,
                        'volume_ratio': current_volume / avg_volume,
                        'consolidation_range': consolidation_range
                    },
                    stop_loss=breakout_level_low * 1.02,  # 2% above breakdown
                    take_profit=current_price - (consolidation_range * 2),
                    confidence=strength
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Breakout strategy error: {e}")
            return None


class TrendFollowingStrategy:
    """
    Trend Following Strategy - Multi-timeframe trend alignment
    
    Best for: Strong trending markets
    Timeframe: 1h, 4h, 1d
    Win rate target: 60-70%
    """
    
    def __init__(self):
        self.name = "trend_following"
        self.fast_ma = 20
        self.slow_ma = 50
        self.trend_strength_threshold = 25  # ADX threshold
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Follow strong trends with pullback entries"""
        try:
            if len(df) < 100:
                return None
            
            df = TechnicalIndicators.calculate_all(df)
            
            current_price = df['close'].iloc[-1]
            sma_20 = df['SMA_20'].iloc[-1]
            sma_50 = df['SMA_50'].iloc[-1]
            adx = df['ADX'].iloc[-1]
            rsi = df['RSI'].iloc[-1]
            
            # Determine trend direction
            uptrend = sma_20 > sma_50 and adx > self.trend_strength_threshold
            downtrend = sma_20 < sma_50 and adx > self.trend_strength_threshold
            
            if not (uptrend or downtrend):
                return None
            
            # Wait for pullback in uptrend
            if uptrend and current_price < sma_20 and rsi < 50:
                strength = min(0.9, 0.5 + (adx - 25) / 100)
                
                return Signal(
                    symbol=symbol,
                    action='BUY',
                    strength=strength,
                    strategy=self.name,
                    reason=f"Uptrend pullback to SMA20, ADX {adx:.1f} shows strong trend",
                    indicators={
                        'sma_20': sma_20,
                        'sma_50': sma_50,
                        'adx': adx,
                        'rsi': rsi
                    },
                    stop_loss=sma_50 * 0.98,  # Below slow MA
                    take_profit=current_price * 1.05,  # 5% target
                    confidence=strength
                )
            
            # Wait for pullback in downtrend
            elif downtrend and current_price > sma_20 and rsi > 50:
                strength = min(0.9, 0.5 + (adx - 25) / 100)
                
                return Signal(
                    symbol=symbol,
                    action='SELL',
                    strength=strength,
                    strategy=self.name,
                    reason=f"Downtrend pullback to SMA20, ADX {adx:.1f} shows strong trend",
                    indicators={
                        'sma_20': sma_20,
                        'sma_50': sma_50,
                        'adx': adx,
                        'rsi': rsi
                    },
                    stop_loss=sma_50 * 1.02,
                    take_profit=current_price * 0.95,
                    confidence=strength
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Trend following strategy error: {e}")
            return None


class SupportResistanceStrategy:
    """
    Support/Resistance Strategy - Trade bounces and breaks at key levels
    
    Best for: All market conditions
    Timeframe: 15m, 1h, 4h
    Win rate target: 65-75%
    """
    
    def __init__(self):
        self.name = "support_resistance"
        self.lookback_periods = 100
        self.level_threshold = 0.002  # 0.2% tolerance for level
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Identify and trade key support/resistance levels"""
        try:
            if len(df) < self.lookback_periods:
                return None
            
            df = TechnicalIndicators.calculate_all(df)
            
            current_price = df['close'].iloc[-1]
            
            # Find support and resistance levels
            support_levels = self._find_support_levels(df)
            resistance_levels = self._find_resistance_levels(df)
            
            # Check if price is near support
            for support in support_levels:
                distance_to_support = abs(current_price - support) / support
                
                if distance_to_support < self.level_threshold:
                    # Price at support, look for bounce
                    rsi = df['RSI'].iloc[-1]
                    
                    if rsi < 40:  # Oversold at support
                        strength = 0.7 + (40 - rsi) / 100
                        
                        return Signal(
                            symbol=symbol,
                            action='BUY',
                            strength=min(0.9, strength),
                            strategy=self.name,
                            reason=f"Price at support ${support:.2f}, RSI {rsi:.1f} oversold",
                            indicators={
                                'support_level': support,
                                'distance_to_support': distance_to_support,
                                'rsi': rsi
                            },
                            stop_loss=support * 0.98,  # 2% below support
                            take_profit=current_price * 1.03,  # 3% target
                            confidence=min(0.9, strength)
                        )
            
            # Check if price is near resistance
            for resistance in resistance_levels:
                distance_to_resistance = abs(current_price - resistance) / resistance
                
                if distance_to_resistance < self.level_threshold:
                    # Price at resistance
                    rsi = df['RSI'].iloc[-1]
                    
                    if rsi > 60:  # Overbought at resistance
                        strength = 0.6 + (rsi - 60) / 100
                        
                        return Signal(
                            symbol=symbol,
                            action='SELL',
                            strength=min(0.9, strength),
                            strategy=self.name,
                            reason=f"Price at resistance ${resistance:.2f}, RSI {rsi:.1f} overbought",
                            indicators={
                                'resistance_level': resistance,
                                'distance_to_resistance': distance_to_resistance,
                                'rsi': rsi
                            },
                            stop_loss=resistance * 1.02,
                            take_profit=current_price * 0.97,
                            confidence=min(0.9, strength)
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Support/Resistance strategy error: {e}")
            return None
    
    def _find_support_levels(self, df: pd.DataFrame) -> list:
        """Find significant support levels"""
        lows = df['low'].iloc[-self.lookback_periods:].values
        support_levels = []
        
        # Find local minima
        for i in range(5, len(lows) - 5):
            if lows[i] == min(lows[i-5:i+5]):
                support_levels.append(lows[i])
        
        # Cluster nearby levels
        if support_levels:
            support_levels = self._cluster_levels(support_levels)
        
        return support_levels[-3:]  # Return top 3 most recent
    
    def _find_resistance_levels(self, df: pd.DataFrame) -> list:
        """Find significant resistance levels"""
        highs = df['high'].iloc[-self.lookback_periods:].values
        resistance_levels = []
        
        # Find local maxima
        for i in range(5, len(highs) - 5):
            if highs[i] == max(highs[i-5:i+5]):
                resistance_levels.append(highs[i])
        
        # Cluster nearby levels
        if resistance_levels:
            resistance_levels = self._cluster_levels(resistance_levels)
        
        return resistance_levels[-3:]  # Return top 3 most recent
    
    def _cluster_levels(self, levels: list) -> list:
        """Cluster nearby price levels"""
        if not levels:
            return []
        
        levels = sorted(levels)
        clustered = []
        current_cluster = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < 0.01:  # Within 1%
                current_cluster.append(level)
            else:
                clustered.append(np.mean(current_cluster))
                current_cluster = [level]
        
        clustered.append(np.mean(current_cluster))
        return clustered


class VolumeProfileStrategy:
    """
    Volume Profile Strategy - Trade based on volume at price levels
    
    Best for: All market conditions
    Timeframe: 1h, 4h
    Win rate target: 60-70%
    """
    
    def __init__(self):
        self.name = "volume_profile"
        self.lookback_periods = 100
        self.num_bins = 20  # Price bins for volume profile
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Analyze volume profile and trade high-volume nodes"""
        try:
            if len(df) < self.lookback_periods:
                return None
            
            df = TechnicalIndicators.calculate_all(df)
            
            current_price = df['close'].iloc[-1]
            
            # Calculate volume profile
            recent_df = df.iloc[-self.lookback_periods:]
            price_range = recent_df['high'].max() - recent_df['low'].min()
            bin_size = price_range / self.num_bins
            
            # Create price bins
            min_price = recent_df['low'].min()
            volume_profile = {}
            
            for i in range(self.num_bins):
                bin_low = min_price + (i * bin_size)
                bin_high = bin_low + bin_size
                bin_mid = (bin_low + bin_high) / 2
                
                # Sum volume in this price range
                mask = (recent_df['low'] <= bin_high) & (recent_df['high'] >= bin_low)
                bin_volume = recent_df.loc[mask, 'volume'].sum()
                
                volume_profile[bin_mid] = bin_volume
            
            # Find high-volume node (HVN) and low-volume node (LVN)
            sorted_profile = sorted(volume_profile.items(), key=lambda x: x[1], reverse=True)
            hvn_price = sorted_profile[0][0]  # Highest volume node
            lvn_price = sorted_profile[-1][0]  # Lowest volume node
            
            # Trade logic: Price approaching HVN from below = support
            distance_to_hvn = abs(current_price - hvn_price) / hvn_price
            
            if distance_to_hvn < 0.01 and current_price < hvn_price:  # Within 1% below HVN
                rsi = df['RSI'].iloc[-1]
                
                if rsi < 50:
                    strength = 0.65 + (50 - rsi) / 100
                    
                    return Signal(
                        symbol=symbol,
                        action='BUY',
                        strength=min(0.85, strength),
                        strategy=self.name,
                        reason=f"Price approaching high-volume node at ${hvn_price:.2f} (support)",
                        indicators={
                            'hvn_price': hvn_price,
                            'current_price': current_price,
                            'distance_to_hvn': distance_to_hvn
                        },
                        stop_loss=hvn_price * 0.98,
                        take_profit=current_price * 1.025,
                        confidence=min(0.85, strength)
                    )
            
            # Price approaching HVN from above = resistance
            elif distance_to_hvn < 0.01 and current_price > hvn_price:
                rsi = df['RSI'].iloc[-1]
                
                if rsi > 50:
                    strength = 0.6 + (rsi - 50) / 100
                    
                    return Signal(
                        symbol=symbol,
                        action='SELL',
                        strength=min(0.85, strength),
                        strategy=self.name,
                        reason=f"Price approaching high-volume node at ${hvn_price:.2f} (resistance)",
                        indicators={
                            'hvn_price': hvn_price,
                            'current_price': current_price,
                            'distance_to_hvn': distance_to_hvn
                        },
                        stop_loss=hvn_price * 1.02,
                        take_profit=current_price * 0.975,
                        confidence=min(0.85, strength)
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Volume profile strategy error: {e}")
            return None


class MarketStructureStrategy:
    """
    Market Structure Strategy - Trade based on higher highs/lower lows
    
    Best for: Trending markets
    Timeframe: 1h, 4h
    Win rate target: 65-75%
    """
    
    def __init__(self):
        self.name = "market_structure"
        self.swing_lookback = 10  # Periods to identify swing points
    
    def analyze(self, df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """Identify market structure and trade structure breaks"""
        try:
            if len(df) < 50:
                return None
            
            df = TechnicalIndicators.calculate_all(df)
            
            # Find swing highs and lows
            swing_highs = self._find_swing_highs(df)
            swing_lows = self._find_swing_lows(df)
            
            if len(swing_highs) < 2 or len(swing_lows) < 2:
                return None
            
            current_price = df['close'].iloc[-1]
            
            # Determine market structure
            # Uptrend: Higher highs and higher lows
            if swing_highs[-1] > swing_highs[-2] and swing_lows[-1] > swing_lows[-2]:
                # Look for pullback to buy
                if current_price < swing_highs[-1] * 0.98:  # 2% below recent high
                    strength = 0.7
                    
                    return Signal(
                        symbol=symbol,
                        action='BUY',
                        strength=strength,
                        strategy=self.name,
                        reason=f"Uptrend structure (HH/HL), pullback entry at ${current_price:.2f}",
                        indicators={
                            'last_swing_high': swing_highs[-1],
                            'last_swing_low': swing_lows[-1],
                            'structure': 'UPTREND'
                        },
                        stop_loss=swing_lows[-1] * 0.99,
                        take_profit=swing_highs[-1] * 1.02,
                        confidence=strength
                    )
            
            # Downtrend: Lower highs and lower lows
            elif swing_highs[-1] < swing_highs[-2] and swing_lows[-1] < swing_lows[-2]:
                # Look for rally to sell
                if current_price > swing_lows[-1] * 1.02:  # 2% above recent low
                    strength = 0.7
                    
                    return Signal(
                        symbol=symbol,
                        action='SELL',
                        strength=strength,
                        strategy=self.name,
                        reason=f"Downtrend structure (LH/LL), rally entry at ${current_price:.2f}",
                        indicators={
                            'last_swing_high': swing_highs[-1],
                            'last_swing_low': swing_lows[-1],
                            'structure': 'DOWNTREND'
                        },
                        stop_loss=swing_highs[-1] * 1.01,
                        take_profit=swing_lows[-1] * 0.98,
                        confidence=strength
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Market structure strategy error: {e}")
            return None
    
    def _find_swing_highs(self, df: pd.DataFrame) -> list:
        """Find swing high points"""
        highs = []
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            if df['high'].iloc[i] == df['high'].iloc[i-self.swing_lookback:i+self.swing_lookback].max():
                highs.append(df['high'].iloc[i])
        return highs[-5:]  # Return last 5
    
    def _find_swing_lows(self, df: pd.DataFrame) -> list:
        """Find swing low points"""
        lows = []
        for i in range(self.swing_lookback, len(df) - self.swing_lookback):
            if df['low'].iloc[i] == df['low'].iloc[i-self.swing_lookback:i+self.swing_lookback].min():
                lows.append(df['low'].iloc[i])
        return lows[-5:]  # Return last 5


# Strategy registry for easy access
ADVANCED_STRATEGIES = {
    'breakout': BreakoutStrategy,
    'trend_following': TrendFollowingStrategy,
    'support_resistance': SupportResistanceStrategy,
    'volume_profile': VolumeProfileStrategy,
    'market_structure': MarketStructureStrategy
}
