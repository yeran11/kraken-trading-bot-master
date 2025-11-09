"""
DeepSeek Master - The Ultimate Trading Intelligence
Single AI model with maximum power - DeepSeek-R1 Reasoning
"""
import asyncio
from loguru import logger
from datetime import datetime
import numpy as np
import json
import os
from typing import Dict, Optional, List

from deepseek_validator import DeepSeekValidator


class DeepSeekMaster:
    """
    Master Trading Intelligence powered solely by DeepSeek-R1
    
    This replaces the multi-model AI ensemble with a single, powerful
    DeepSeek reasoning model that makes all trading decisions.
    
    Features:
    - Ultra-aggressive profit-hunting protocol
    - Multi-timeframe analysis
    - Portfolio-aware decision making
    - Dynamic position sizing
    - Risk-reward optimization
    - Confidence calibration
    """

    def __init__(self, deepseek_api_key=None):
        # Initialize DeepSeek validator
        self.deepseek = DeepSeekValidator(api_key=deepseek_api_key)
        
        # Load configuration
        config = self._load_config()
        
        # Minimum confidence threshold for trading
        self.min_confidence = config['settings']['min_confidence']
        
        # Performance tracking
        self.total_predictions = 0
        self.correct_predictions = 0
        self.total_profit = 0.0
        self.trade_history = []
        
        # Calibration settings
        self.calibration_enabled = config['settings'].get('enable_calibration', True)
        self.calibration_window = 100  # Recalibrate every 100 trades
        
        logger.success("✓ DeepSeek Master initialized")
        logger.info(f"🧠 Single AI Model: DeepSeek-R1 Reasoning")
        logger.info(f"🎯 Min confidence threshold: {self.min_confidence:.0%}")
        logger.info(f"⚡ Ultra-aggressive profit-hunting protocol: ACTIVE")

    def _load_config(self) -> Dict:
        """Load DeepSeek configuration from ai_config.json"""
        config_file = 'ai_config.json'
        
        # Default configuration
        default_config = {
            'settings': {
                'min_confidence': 0.50,  # 50% minimum confidence
                'enable_calibration': True,
                'enable_multi_timeframe': True,
                'enable_portfolio_context': True,
                'enable_risk_optimization': True
            }
        }
        
        # Try to load from file
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                logger.success(f"✅ Loaded DeepSeek configuration from {config_file}")
                return config
            except Exception as e:
                logger.warning(f"Failed to load {config_file}: {e}, using defaults")
                return default_config
        else:
            logger.warning(f"{config_file} not found, using default configuration")
            return default_config

    async def generate_signal(
        self,
        symbol: str,
        current_price: float,
        market_data: Dict,
        technical_indicators: Dict,
        portfolio_state: Optional[Dict] = None,
        timeframe: str = '5m'
    ) -> Dict:
        """
        Generate trading signal using DeepSeek Master Intelligence
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            current_price: Current market price
            market_data: Recent candles and market info
            technical_indicators: RSI, MACD, etc.
            portfolio_state: Current portfolio context
            timeframe: Trading timeframe (5m, 1h, 4h)
        
        Returns:
            {
                'action': 'BUY' | 'SELL' | 'HOLD',
                'confidence': 0.0-1.0,
                'position_size': 0.0-1.0,
                'stop_loss': float,
                'take_profit': float,
                'reasoning': str,
                'risks': List[str],
                'timeframe': str
            }
        """
        try:
            logger.info(f"🧠 DeepSeek Master analyzing {symbol} on {timeframe}...")
            
            # Prepare sentiment data (neutral default since we removed sentiment analysis)
            sentiment = {
                'label': 'NEUTRAL',
                'score': 0.5,
                'confidence': 0.5
            }
            
            # Calculate volatility metrics
            volatility_metrics = self._calculate_volatility(market_data, current_price)
            
            # Get DeepSeek analysis
            result = await self.deepseek.validate_signal(
                symbol=symbol,
                current_price=current_price,
                technical_signals=technical_indicators,
                sentiment=sentiment,
                market_data=market_data,
                portfolio_context=portfolio_state or {},
                volatility_metrics=volatility_metrics
            )
            
            # Convert confidence from 0-100 to 0-1
            confidence = result['confidence'] / 100.0
            
            # Apply confidence threshold
            if confidence < self.min_confidence:
                logger.info(f"⚠️  Confidence {confidence:.0%} below threshold {self.min_confidence:.0%} - HOLD")
                result['action'] = 'HOLD'
            
            # Calculate position size based on confidence
            position_size = self._calculate_position_size(confidence, volatility_metrics)
            
            # Calculate stop loss and take profit
            stop_loss, take_profit = self._calculate_risk_levels(
                current_price,
                result.get('stop_loss_percent', 2.0),
                result.get('take_profit_percent', 3.0),
                result['action']
            )
            
            # Build final signal
            signal = {
                'action': result['action'],
                'confidence': confidence,
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reasoning': result['reasoning'],
                'risks': result.get('risks', []),
                'timeframe': timeframe,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Track prediction
            self.total_predictions += 1
            
            # Log decision
            if signal['action'] != 'HOLD':
                logger.success(
                    f"🎯 {signal['action']} {symbol} | "
                    f"Confidence: {confidence:.0%} | "
                    f"Size: {position_size:.1%} | "
                    f"SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}"
                )
            else:
                logger.info(f"⏸️  HOLD {symbol} | Confidence: {confidence:.0%}")
            
            return signal
            
        except Exception as e:
            logger.error(f"DeepSeek Master error: {e}")
            return self._fallback_signal(symbol, current_price)

    def _calculate_volatility(self, market_data: Dict, current_price: float) -> Dict:
        """Calculate volatility metrics from market data"""
        try:
            candles = market_data.get('recent_candles', [])
            if len(candles) < 14:
                return {
                    'atr': 0,
                    'atr_percent': 0,
                    'regime': 'UNKNOWN',
                    'avg_daily_range': 0
                }
            
            # Calculate ATR (Average True Range)
            true_ranges = []
            for i in range(1, len(candles)):
                high = candles[i]['high']
                low = candles[i]['low']
                prev_close = candles[i-1]['close']
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                true_ranges.append(tr)
            
            atr = np.mean(true_ranges[-14:]) if true_ranges else 0
            atr_percent = (atr / current_price * 100) if current_price > 0 else 0
            
            # Calculate average daily range
            daily_ranges = [(c['high'] - c['low']) / c['close'] * 100 for c in candles[-20:]]
            avg_daily_range = np.mean(daily_ranges) if daily_ranges else 0
            
            # Determine volatility regime
            if atr_percent > 5:
                regime = 'HIGH_VOLATILITY'
            elif atr_percent > 2:
                regime = 'MEDIUM_VOLATILITY'
            else:
                regime = 'LOW_VOLATILITY'
            
            return {
                'atr': atr,
                'atr_percent': atr_percent,
                'regime': regime,
                'avg_daily_range': avg_daily_range
            }
            
        except Exception as e:
            logger.error(f"Volatility calculation error: {e}")
            return {
                'atr': 0,
                'atr_percent': 0,
                'regime': 'UNKNOWN',
                'avg_daily_range': 0
            }

    def _calculate_position_size(self, confidence: float, volatility_metrics: Dict) -> float:
        """
        Calculate optimal position size based on confidence and volatility
        
        Returns: Position size as percentage (0.0-1.0)
        """
        # Base position size from confidence
        # 50% confidence = 5% position
        # 75% confidence = 15% position
        # 90% confidence = 20% position
        base_size = confidence * 0.25  # Max 25% at 100% confidence
        
        # Adjust for volatility
        volatility_regime = volatility_metrics.get('regime', 'MEDIUM_VOLATILITY')
        
        if volatility_regime == 'HIGH_VOLATILITY':
            # Reduce size in high volatility
            size_multiplier = 0.6
        elif volatility_regime == 'LOW_VOLATILITY':
            # Increase size in low volatility
            size_multiplier = 1.2
        else:
            # Normal volatility
            size_multiplier = 1.0
        
        final_size = base_size * size_multiplier
        
        # Enforce limits
        final_size = max(0.05, min(0.20, final_size))  # 5% to 20%
        
        return final_size

    def _calculate_risk_levels(
        self,
        current_price: float,
        stop_loss_percent: float,
        take_profit_percent: float,
        action: str
    ) -> tuple:
        """Calculate stop loss and take profit levels"""
        if action == 'BUY':
            stop_loss = current_price * (1 - stop_loss_percent / 100)
            take_profit = current_price * (1 + take_profit_percent / 100)
        elif action == 'SELL':
            stop_loss = current_price * (1 + stop_loss_percent / 100)
            take_profit = current_price * (1 - take_profit_percent / 100)
        else:  # HOLD
            stop_loss = 0
            take_profit = 0
        
        return stop_loss, take_profit

    def _fallback_signal(self, symbol: str, current_price: float) -> Dict:
        """Return safe fallback signal on error"""
        return {
            'action': 'HOLD',
            'confidence': 0.0,
            'position_size': 0.0,
            'stop_loss': 0,
            'take_profit': 0,
            'reasoning': 'Error occurred, defaulting to HOLD for safety',
            'risks': ['System error'],
            'timeframe': 'unknown',
            'timestamp': datetime.utcnow().isoformat()
        }

    def update_performance(self, trade_result: Dict):
        """
        Update performance tracking after trade closes
        
        Args:
            trade_result: {
                'symbol': str,
                'action': str,
                'entry_price': float,
                'exit_price': float,
                'profit': float,
                'confidence': float,
                'was_correct': bool
            }
        """
        self.trade_history.append(trade_result)
        
        if trade_result.get('was_correct'):
            self.correct_predictions += 1
        
        self.total_profit += trade_result.get('profit', 0)
        
        # Recalibrate if needed
        if self.calibration_enabled and len(self.trade_history) % self.calibration_window == 0:
            self._recalibrate()

    def _recalibrate(self):
        """Recalibrate confidence threshold based on performance"""
        if len(self.trade_history) < self.calibration_window:
            return
        
        recent_trades = self.trade_history[-self.calibration_window:]
        win_rate = sum(1 for t in recent_trades if t.get('was_correct', False)) / len(recent_trades)
        
        logger.info(f"📊 Recalibrating after {len(recent_trades)} trades...")
        logger.info(f"📈 Win rate: {win_rate:.1%}")
        
        # Adjust confidence threshold based on win rate
        if win_rate < 0.55:
            # Performing poorly, increase threshold (be more selective)
            self.min_confidence = min(0.65, self.min_confidence + 0.05)
            logger.warning(f"⬆️  Increasing confidence threshold to {self.min_confidence:.0%}")
        elif win_rate > 0.70:
            # Performing well, decrease threshold (trade more)
            self.min_confidence = max(0.45, self.min_confidence - 0.05)
            logger.success(f"⬇️  Decreasing confidence threshold to {self.min_confidence:.0%}")
        else:
            logger.info(f"✓ Confidence threshold remains at {self.min_confidence:.0%}")

    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        if self.total_predictions == 0:
            return {
                'total_predictions': 0,
                'accuracy': 0,
                'total_profit': 0,
                'avg_profit_per_trade': 0,
                'win_rate': 0
            }
        
        accuracy = self.correct_predictions / self.total_predictions
        avg_profit = self.total_profit / len(self.trade_history) if self.trade_history else 0
        win_rate = sum(1 for t in self.trade_history if t.get('was_correct', False)) / len(self.trade_history) if self.trade_history else 0
        
        return {
            'total_predictions': self.total_predictions,
            'accuracy': accuracy,
            'total_profit': self.total_profit,
            'avg_profit_per_trade': avg_profit,
            'win_rate': win_rate,
            'current_threshold': self.min_confidence
        }


# Backward compatibility alias
AIEnsemble = DeepSeekMaster
