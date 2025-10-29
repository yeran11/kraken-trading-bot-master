"""
AI Service - Master Trader Intelligence
Combines Sentiment Analysis + Price Prediction from KaliTrade architecture
"""
import numpy as np
import pandas as pd
from datetime import datetime
from loguru import logger
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import os

class AIService:
    """
    AI Service combining multiple ML models for market analysis
    Based on KaliTrade's ensemble approach
    """

    def __init__(self):
        self.sentiment_analyzer = None
        self.price_predictor = None
        self.volatility_predictor = None
        self.scaler = StandardScaler()

        # Model weights (from KaliTrade)
        self.model_weights = {
            'sentiment': 0.25,
            'technical': 0.35,
            'microstructure': 0.20,
            'macro': 0.20
        }

        # Cache for predictions
        self.prediction_cache = {}
        self.cache_ttl = 300  # 5 minutes

        logger.info("AI Service initialized")

        # Initialize models
        self._initialize_models()

    def _initialize_models(self):
        """Initialize ML models"""
        try:
            # Try to load HuggingFace sentiment model
            from transformers import pipeline
            logger.info("Loading HuggingFace sentiment model...")
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            logger.success("✓ Sentiment analyzer loaded")
        except Exception as e:
            logger.warning(f"Could not load sentiment analyzer: {e}")
            logger.info("Will use fallback sentiment analysis")

        # Initialize price predictor
        self.price_predictor = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        # Initialize volatility predictor
        self.volatility_predictor = RandomForestRegressor(
            n_estimators=50,
            max_depth=8,
            random_state=42,
            n_jobs=-1
        )

        logger.info("✓ Price & Volatility predictors initialized")

    async def analyze_sentiment(self, symbol: str, news_texts: list = None):
        """
        Analyze market sentiment using HuggingFace transformer
        Returns: {'score': 0-1, 'confidence': 0-1, 'label': str}
        """
        try:
            if not self.sentiment_analyzer:
                # Fallback: simple keyword-based sentiment
                return self._fallback_sentiment(symbol)

            if not news_texts or len(news_texts) == 0:
                # Use generic market sentiment
                news_texts = [
                    f"{symbol} trading analysis",
                    f"{symbol} market update",
                ]

            sentiments = []
            confidences = []

            for text in news_texts[:5]:  # Analyze up to 5 texts
                # Truncate to model's max length
                text_truncated = text[:512]

                result = self.sentiment_analyzer(text_truncated)[0]

                # Convert label to score (0-1 scale)
                label = result['label']
                score = result['score']

                if 'NEGATIVE' in label or 'LABEL_0' in label:
                    sentiment_score = (1 - score) * 0.5  # 0 - 0.5
                elif 'NEUTRAL' in label or 'LABEL_1' in label:
                    sentiment_score = 0.5  # Neutral
                else:  # POSITIVE or LABEL_2
                    sentiment_score = 0.5 + (score * 0.5)  # 0.5 - 1.0

                sentiments.append(sentiment_score)
                confidences.append(score)

            # Average sentiment
            avg_sentiment = np.mean(sentiments) if sentiments else 0.5
            avg_confidence = np.mean(confidences) if confidences else 0.5

            # Determine label
            if avg_sentiment > 0.6:
                label = "BULLISH"
            elif avg_sentiment < 0.4:
                label = "BEARISH"
            else:
                label = "NEUTRAL"

            return {
                'score': float(avg_sentiment),
                'confidence': float(avg_confidence),
                'label': label,
                'source': 'huggingface'
            }

        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return self._fallback_sentiment(symbol)

    def _fallback_sentiment(self, symbol: str):
        """Simple fallback sentiment when HuggingFace unavailable"""
        # Use basic sentiment (neutral)
        return {
            'score': 0.5,
            'confidence': 0.5,
            'label': 'NEUTRAL',
            'source': 'fallback'
        }

    def extract_features(self, candles: pd.DataFrame) -> dict:
        """
        Extract 10-dimensional feature vector from market data
        Based on KaliTrade's feature engineering
        """
        try:
            if len(candles) < 24:
                return None

            closes = candles['close'].values
            highs = candles['high'].values
            lows = candles['low'].values
            volumes = candles['volume'].values

            # Price change features (3 dimensions)
            price_change_1h = (closes[-1] - closes[-2]) / closes[-2] if len(closes) > 1 else 0
            price_change_4h = (closes[-1] - closes[-5]) / closes[-5] if len(closes) > 4 else 0
            price_change_24h = (closes[-1] - closes[-24]) / closes[-24] if len(closes) > 23 else 0

            # Volume features (2 dimensions)
            volume_ratio = volumes[-1] / np.mean(volumes[-20:]) if len(volumes) > 20 else 1.0
            volume_trend = (volumes[-1] - volumes[-2]) / volumes[-2] if len(volumes) > 1 else 0

            # Volatility features (2 dimensions)
            returns = np.diff(closes) / closes[:-1]
            volatility_1h = np.std(returns[-12:]) if len(returns) > 12 else 0
            volatility_24h = np.std(returns[-24:]) if len(returns) > 24 else 0

            # Technical indicator features (3 dimensions)
            # RSI
            rsi = self._calculate_rsi(closes)

            # MACD
            macd_value = self._calculate_macd_simple(closes)

            # Bollinger position (0-1 scale)
            bb_position = self._calculate_bb_position(closes)

            features = {
                'price_change_1h': float(price_change_1h),
                'price_change_4h': float(price_change_4h),
                'price_change_24h': float(price_change_24h),
                'volume_ratio': float(volume_ratio),
                'volume_trend': float(volume_trend),
                'volatility_1h': float(volatility_1h),
                'volatility_24h': float(volatility_24h),
                'rsi': float(rsi),
                'macd': float(macd_value),
                'bb_position': float(bb_position)
            }

            return features

        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
            return None

    def _calculate_rsi(self, closes, period=14):
        """Calculate RSI indicator"""
        if len(closes) < period + 1:
            return 50.0

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd_simple(self, closes):
        """Simple MACD calculation"""
        if len(closes) < 26:
            return 0.0

        ema_12 = self._ema(closes, 12)
        ema_26 = self._ema(closes, 26)
        macd = ema_12 - ema_26

        return macd

    def _ema(self, prices, period):
        """Calculate EMA"""
        if len(prices) < period:
            return prices[-1]

        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _calculate_bb_position(self, closes, period=20):
        """Calculate Bollinger Band position (0-1)"""
        if len(closes) < period:
            return 0.5

        sma = np.mean(closes[-period:])
        std = np.std(closes[-period:])

        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)

        current = closes[-1]

        if upper_band == lower_band:
            return 0.5

        # Position within bands (0 = lower, 1 = upper)
        position = (current - lower_band) / (upper_band - lower_band)
        position = max(0, min(1, position))  # Clamp to 0-1

        return position

    async def predict_price_movement(self, features: dict, historical_data: pd.DataFrame = None):
        """
        Predict price movement using Random Forest
        Returns: {'prediction': float, 'volatility': float, 'confidence': float}
        """
        try:
            if not features:
                return {'prediction': 0, 'volatility': 0, 'confidence': 0}

            # Convert features to array
            feature_vector = np.array([list(features.values())])

            # Check if model is trained
            if not hasattr(self.price_predictor, 'estimators_') or len(self.price_predictor.estimators_) == 0:
                # Train on historical data if available
                if historical_data is not None and len(historical_data) > 100:
                    self._train_models(historical_data)
                else:
                    # Return neutral prediction if not trained
                    return {
                        'prediction': 0.0,
                        'volatility': 0.02,
                        'confidence': 0.5,
                        'status': 'untrained'
                    }

            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)

            # Predict
            price_prediction = self.price_predictor.predict(feature_vector_scaled)[0]
            volatility_prediction = abs(self.volatility_predictor.predict(feature_vector_scaled)[0])

            # Calculate confidence based on feature quality
            confidence = self._calculate_prediction_confidence(features)

            return {
                'prediction': float(price_prediction),
                'volatility': float(volatility_prediction),
                'confidence': float(confidence),
                'status': 'trained'
            }

        except Exception as e:
            logger.error(f"Price prediction error: {e}")
            return {
                'prediction': 0.0,
                'volatility': 0.02,
                'confidence': 0.3,
                'status': 'error'
            }

    def _train_models(self, historical_data: pd.DataFrame):
        """Train price and volatility predictors on historical data"""
        try:
            logger.info("Training AI models on historical data...")

            # Prepare training data
            features_list = []
            price_targets = []
            volatility_targets = []

            for i in range(30, len(historical_data) - 1):
                # Get features for window
                window = historical_data.iloc[i-30:i]
                features = self.extract_features(window)

                if features:
                    features_list.append(list(features.values()))

                    # Target: next period price change %
                    current_price = historical_data.iloc[i]['close']
                    next_price = historical_data.iloc[i+1]['close']
                    price_change = (next_price - current_price) / current_price
                    price_targets.append(price_change)

                    # Target: volatility
                    recent_closes = historical_data.iloc[i-12:i]['close'].values
                    returns = np.diff(recent_closes) / recent_closes[:-1]
                    volatility = np.std(returns)
                    volatility_targets.append(volatility)

            if len(features_list) < 50:
                logger.warning("Not enough data to train models")
                return

            X = np.array(features_list)
            y_price = np.array(price_targets)
            y_vol = np.array(volatility_targets)

            # Fit scaler
            self.scaler.fit(X)
            X_scaled = self.scaler.transform(X)

            # Train models
            self.price_predictor.fit(X_scaled, y_price)
            self.volatility_predictor.fit(X_scaled, y_vol)

            logger.success(f"✓ Models trained on {len(X)} samples")

        except Exception as e:
            logger.error(f"Model training error: {e}")

    def _calculate_prediction_confidence(self, features: dict):
        """Calculate prediction confidence based on feature quality"""
        confidence = 0.5  # Baseline

        # Add confidence for each available feature
        if features.get('price_change_1h') is not None:
            confidence += 0.05
        if features.get('volume_ratio') is not None:
            confidence += 0.05
        if features.get('rsi') is not None:
            confidence += 0.1
        if features.get('volatility_24h') is not None and features['volatility_24h'] > 0:
            confidence += 0.1

        # Bonus for complete feature set
        if all(v is not None and v != 0 for v in features.values()):
            confidence += 0.2

        return min(confidence, 1.0)  # Cap at 1.0

    def save_models(self, filepath='ai_models.pkl'):
        """Save trained models to disk"""
        try:
            models = {
                'price_predictor': self.price_predictor,
                'volatility_predictor': self.volatility_predictor,
                'scaler': self.scaler
            }
            joblib.dump(models, filepath)
            logger.info(f"✓ Models saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving models: {e}")

    def load_models(self, filepath='ai_models.pkl'):
        """Load trained models from disk"""
        try:
            if os.path.exists(filepath):
                models = joblib.load(filepath)
                self.price_predictor = models['price_predictor']
                self.volatility_predictor = models['volatility_predictor']
                self.scaler = models['scaler']
                logger.success(f"✓ Models loaded from {filepath}")
                return True
        except Exception as e:
            logger.error(f"Error loading models: {e}")
        return False
