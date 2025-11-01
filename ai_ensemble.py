"""
AI Ensemble - Master Trading Intelligence
Combines 4 AI models with weighted voting for superior predictions
Architecture inspired by KaliTrade's ensemble approach
"""
import asyncio
from loguru import logger
from datetime import datetime
import numpy as np

# Import all AI components
from ai_service import AIService
from deepseek_validator import DeepSeekValidator
from macro_analyzer import MacroAnalyzer


class AIEnsemble:
    """
    Master AI Ensemble that combines:
    1. Sentiment Analysis (HuggingFace) - 20%
    2. Technical Analysis (Your indicators) - 35%
    3. Macro Analysis (Economic conditions) - 15%
    4. DeepSeek Validator (LLM reasoning) - 30%
    """

    def __init__(self, deepseek_api_key=None):
        # Initialize all AI components
        self.ai_service = AIService()
        self.deepseek = DeepSeekValidator(api_key=deepseek_api_key)
        self.macro = MacroAnalyzer()

        # Model weights (adjustable for optimization)
        self.weights = {
            'sentiment': 0.20,      # News/social sentiment
            'technical': 0.35,      # Traditional indicators
            'macro': 0.15,          # Economic conditions
            'deepseek': 0.30        # LLM validation
        }

        # Minimum confidence threshold for trading
        self.min_confidence = 0.65  # 65% minimum to trade

        # Cache for recent analyses
        self.analysis_cache = {}
        self.cache_ttl = 60  # 1 minute

        logger.success("✓ AI Ensemble initialized with 4-model architecture")

    async def generate_signal(
        self,
        symbol: str,
        current_price: float,
        candles: list,
        technical_indicators: dict,
        portfolio_context: dict = None,
        volatility_metrics: dict = None
    ):
        """
        Generate trading signal by combining all 4 AI models with full context
        Returns: {'signal': str, 'confidence': float, 'reasoning': str, 'breakdown': dict, 'parameters': dict}
        """
        try:
            logger.info(f"🤖 AI Ensemble analyzing {symbol}...")

            # Run all models in parallel for speed
            results = await asyncio.gather(
                self._get_sentiment_signal(symbol),
                self._get_technical_signal(technical_indicators),
                self._get_macro_signal(),
                self._get_deepseek_signal(symbol, current_price, technical_indicators, candles, portfolio_context, volatility_metrics),
                return_exceptions=True
            )

            sentiment_signal, technical_signal, macro_signal, deepseek_signal = results

            # Handle any failed models
            sentiment_signal = sentiment_signal if not isinstance(sentiment_signal, Exception) else self._neutral_signal()
            technical_signal = technical_signal if not isinstance(technical_signal, Exception) else self._neutral_signal()
            macro_signal = macro_signal if not isinstance(macro_signal, Exception) else self._neutral_signal()
            deepseek_signal = deepseek_signal if not isinstance(deepseek_signal, Exception) else self._neutral_signal()

            # Combine signals with weighted voting
            final_signal = self._combine_signals(
                sentiment_signal,
                technical_signal,
                macro_signal,
                deepseek_signal
            )

            logger.info(f"📊 AI Ensemble Result: {final_signal['signal']} with {final_signal['confidence']*100:.1f}% confidence")

            return final_signal

        except Exception as e:
            logger.error(f"AI Ensemble error: {e}")
            return self._fallback_signal()

    async def _get_sentiment_signal(self, symbol: str):
        """Get sentiment analysis signal"""
        try:
            # Analyze sentiment (would use real news in production)
            sentiment = await self.ai_service.analyze_sentiment(symbol)

            score = sentiment['score']  # 0-1 scale
            confidence = sentiment['confidence']

            # Convert sentiment to BUY/SELL/HOLD
            if score > 0.6 and confidence > 0.6:
                signal = 'BUY'
                signal_confidence = score * confidence
            elif score < 0.4 and confidence > 0.6:
                signal = 'SELL'
                signal_confidence = (1 - score) * confidence
            else:
                signal = 'HOLD'
                signal_confidence = 0.5

            return {
                'signal': signal,
                'confidence': signal_confidence,
                'details': sentiment,
                'source': 'sentiment'
            }

        except Exception as e:
            logger.error(f"Sentiment signal error: {e}")
            return self._neutral_signal()

    async def _get_technical_signal(self, indicators: dict):
        """Analyze technical indicators"""
        try:
            # Score based on multiple indicators
            score = 0
            confidence = 0.7

            # RSI analysis
            rsi = indicators.get('rsi', 50)
            if rsi < 30:
                score += 2  # Oversold = BUY
            elif rsi < 40:
                score += 1
            elif rsi > 70:
                score -= 2  # Overbought = SELL
            elif rsi > 60:
                score -= 1

            # MACD analysis
            macd_signal = indicators.get('macd_signal', 'NEUTRAL')
            if macd_signal == 'BULLISH':
                score += 2
            elif macd_signal == 'BEARISH':
                score -= 2

            # Volume confirmation
            volume_ratio = indicators.get('volume_ratio', 1.0)
            if volume_ratio > 1.5:
                score += 1  # High volume confirms move
                confidence += 0.1
            elif volume_ratio < 0.7:
                confidence -= 0.1  # Low volume = less confidence

            # ADX (trend strength)
            adx = indicators.get('adx', 20)
            if adx > 25:
                confidence += 0.1  # Strong trend = more confidence
            elif adx < 15:
                confidence -= 0.1  # Weak trend = less confidence

            # Determine signal
            if score >= 3:
                signal = 'BUY'
                signal_confidence = min(confidence + (score * 0.05), 0.95)
            elif score <= -3:
                signal = 'SELL'
                signal_confidence = min(confidence + (abs(score) * 0.05), 0.95)
            else:
                signal = 'HOLD'
                signal_confidence = 0.5

            return {
                'signal': signal,
                'confidence': signal_confidence,
                'details': {'score': score, 'indicators': indicators},
                'source': 'technical'
            }

        except Exception as e:
            logger.error(f"Technical signal error: {e}")
            return self._neutral_signal()

    async def _get_macro_signal(self):
        """Get macroeconomic signal"""
        try:
            macro_analysis = await self.macro.analyze_macro_conditions()

            regime = macro_analysis['regime']
            risk_appetite = macro_analysis['risk_appetite']
            crypto_correlation = macro_analysis['crypto_correlation']

            # Determine signal based on macro conditions
            if regime == 'BULL' and risk_appetite > 0.6:
                signal = 'BUY'
                confidence = 0.7
            elif regime == 'BEAR' and risk_appetite < 0.4:
                signal = 'SELL'
                confidence = 0.7
            else:
                signal = 'HOLD'
                confidence = 0.5

            # Adjust confidence based on crypto correlation
            confidence *= (0.8 + abs(crypto_correlation) * 0.2)

            return {
                'signal': signal,
                'confidence': confidence,
                'details': macro_analysis,
                'source': 'macro'
            }

        except Exception as e:
            logger.error(f"Macro signal error: {e}")
            return self._neutral_signal()

    async def _get_deepseek_signal(self, symbol, current_price, indicators, candles, portfolio_context=None, volatility_metrics=None):
        """Get DeepSeek AI validation with full context"""
        try:
            # Prepare market data
            market_data = {
                'recent_candles': candles[-10:] if len(candles) >= 10 else candles
            }

            # Get sentiment for context
            sentiment = await self.ai_service.analyze_sentiment(symbol)

            # Validate with DeepSeek (now includes portfolio and volatility context!)
            validation = await self.deepseek.validate_signal(
                symbol=symbol,
                current_price=current_price,
                technical_signals=indicators,
                sentiment=sentiment,
                market_data=market_data,
                portfolio_context=portfolio_context,
                volatility_metrics=volatility_metrics
            )

            signal = validation['action']  # BUY, SELL, or HOLD
            confidence = validation['confidence'] / 100  # Convert to 0-1

            return {
                'signal': signal,
                'confidence': confidence,
                'details': validation,  # Now includes position_size, stop_loss, take_profit!
                'source': 'deepseek'
            }

        except Exception as e:
            logger.error(f"DeepSeek signal error: {e}")
            return self._neutral_signal()

    def _combine_signals(self, sentiment, technical, macro, deepseek):
        """
        Combine all 4 signals using weighted voting
        """
        # Calculate weighted scores for BUY/SELL/HOLD
        buy_score = 0
        sell_score = 0
        hold_score = 0

        signals = [
            (sentiment, self.weights['sentiment']),
            (technical, self.weights['technical']),
            (macro, self.weights['macro']),
            (deepseek, self.weights['deepseek'])
        ]

        for signal_data, weight in signals:
            signal = signal_data['signal']
            confidence = signal_data['confidence']

            weighted_confidence = confidence * weight

            if signal == 'BUY':
                buy_score += weighted_confidence
            elif signal == 'SELL':
                sell_score += weighted_confidence
            else:  # HOLD
                hold_score += weighted_confidence

        # Determine final signal
        max_score = max(buy_score, sell_score, hold_score)

        if max_score == buy_score and buy_score > self.min_confidence:
            final_signal = 'BUY'
            final_confidence = buy_score
        elif max_score == sell_score and sell_score > self.min_confidence:
            final_signal = 'SELL'
            final_confidence = sell_score
        else:
            final_signal = 'HOLD'
            final_confidence = hold_score

        # Generate reasoning
        reasoning = self._generate_reasoning(sentiment, technical, macro, deepseek, final_signal)

        # Extract dynamic trading parameters from DeepSeek
        deepseek_details = deepseek.get('details', {})
        position_size = deepseek_details.get('position_size_percent', 10)
        stop_loss = deepseek_details.get('stop_loss_percent', 2.0)
        take_profit = deepseek_details.get('take_profit_percent', 3.5)
        risk_reward = deepseek_details.get('risk_reward_ratio', 1.75)

        # Return comprehensive result with autonomous trading parameters
        return {
            'signal': final_signal,
            'confidence': float(final_confidence),
            'reasoning': reasoning,
            # NEW: Dynamic trading parameters from DeepSeek
            'parameters': {
                'position_size_percent': position_size,
                'stop_loss_percent': stop_loss,
                'take_profit_percent': take_profit,
                'risk_reward_ratio': risk_reward
            },
            'breakdown': {
                'sentiment': {
                    'signal': sentiment['signal'],
                    'confidence': sentiment['confidence'],
                    'weight': self.weights['sentiment']
                },
                'technical': {
                    'signal': technical['signal'],
                    'confidence': technical['confidence'],
                    'weight': self.weights['technical']
                },
                'macro': {
                    'signal': macro['signal'],
                    'confidence': macro['confidence'],
                    'weight': self.weights['macro']
                },
                'deepseek': {
                    'signal': deepseek['signal'],
                    'confidence': deepseek['confidence'],
                    'weight': self.weights['deepseek'],
                    'reasoning': deepseek['details'].get('reasoning', ''),
                    # Include autonomous parameters in breakdown
                    'position_size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
            },
            'scores': {
                'buy': float(buy_score),
                'sell': float(sell_score),
                'hold': float(hold_score)
            }
        }

    def _generate_reasoning(self, sentiment, technical, macro, deepseek, final_signal):
        """Generate human-readable reasoning"""
        reasoning_parts = []

        # Add DeepSeek reasoning (most authoritative)
        if deepseek['details'].get('reasoning'):
            reasoning_parts.append(f"AI Analysis: {deepseek['details']['reasoning']}")

        # Add technical summary
        if technical['signal'] == final_signal:
            reasoning_parts.append(f"Technical indicators support {final_signal}")

        # Add sentiment if aligned
        if sentiment['signal'] == final_signal:
            sentiment_label = sentiment['details'].get('label', 'NEUTRAL')
            reasoning_parts.append(f"Market sentiment is {sentiment_label}")

        # Add macro context
        macro_regime = macro['details'].get('regime', 'NEUTRAL')
        if macro_regime != 'NEUTRAL':
            reasoning_parts.append(f"Macro conditions are {macro_regime}")

        # Combine
        if reasoning_parts:
            return ". ".join(reasoning_parts) + "."
        else:
            return f"Ensemble voted for {final_signal} with {final_signal.lower()} signals from multiple models."

    def _neutral_signal(self):
        """Neutral signal when model fails"""
        return {
            'signal': 'HOLD',
            'confidence': 0.5,
            'details': {},
            'source': 'fallback'
        }

    def _fallback_signal(self):
        """Complete fallback when ensemble fails"""
        return {
            'signal': 'HOLD',
            'confidence': 0.3,
            'reasoning': 'AI ensemble unavailable, defaulting to HOLD for safety',
            'parameters': {
                'position_size_percent': 10,
                'stop_loss_percent': 2.0,
                'take_profit_percent': 3.5,
                'risk_reward_ratio': 1.75
            },
            'breakdown': {},
            'scores': {'buy': 0, 'sell': 0, 'hold': 1}
        }

    def get_model_health(self):
        """Check health of all AI models"""
        health = {
            'sentiment': 'OK' if self.ai_service.sentiment_analyzer else 'DEGRADED',
            'technical': 'OK',
            'macro': 'OK',
            'deepseek': 'OK' if self.deepseek.api_key else 'DEMO_MODE',
            'overall': 'OPERATIONAL'
        }

        # Determine overall health
        if health['deepseek'] == 'DEMO_MODE':
            health['overall'] = 'LIMITED'
        if health['sentiment'] == 'DEGRADED':
            health['overall'] = 'DEGRADED'

        return health

    def adjust_weights(self, **new_weights):
        """Dynamically adjust model weights"""
        for model, weight in new_weights.items():
            if model in self.weights:
                self.weights[model] = weight
                logger.info(f"Updated {model} weight to {weight}")

        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        for model in self.weights:
            self.weights[model] /= total

        logger.success(f"✓ Weights adjusted: {self.weights}")
