"""
Macro Analyzer - Macroeconomic Market Analysis
Monitors VIX, Dollar Index, Treasury Yields, Gold prices
Based on KaliTrade's macro analysis module
"""
import requests
from loguru import logger
from datetime import datetime
import numpy as np

class MacroAnalyzer:
    """
    Analyzes macroeconomic conditions for crypto trading
    """

    def __init__(self):
        # Fallback values (will be updated from APIs)
        self.macro_data = {
            'vix': 18.5,              # Volatility Index
            'dollar_index': 103.5,    # US Dollar strength
            'gold_price': 1950.0,     # Gold price (safe haven)
            'treasury_yield_10y': 4.5,  # 10-year Treasury yield
            'btc_dominance': 52.0,    # Bitcoin market dominance %
        }

        # Cache for API calls
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour

        logger.info("✓ Macro Analyzer initialized")

    async def analyze_macro_conditions(self):
        """
        Analyze current macroeconomic conditions
        Returns: {'regime': str, 'risk_appetite': float, 'crypto_correlation': float, 'confidence': float}
        """
        try:
            # Update macro data (from APIs or cache)
            await self._update_macro_data()

            # Analyze market regime
            market_regime = self._determine_market_regime()

            # Calculate risk appetite
            risk_appetite = self._calculate_risk_appetite()

            # Estimate crypto correlation with macros
            crypto_correlation = self._estimate_crypto_correlation()

            # Calculate confidence based on data freshness
            confidence = 0.7  # Base confidence

            return {
                'regime': market_regime,
                'risk_appetite': float(risk_appetite),
                'crypto_correlation': float(crypto_correlation),
                'confidence': float(confidence),
                'indicators': self.macro_data.copy(),
                'analysis': self._generate_analysis(market_regime, risk_appetite)
            }

        except Exception as e:
            logger.error(f"Macro analysis error: {e}")
            return self._fallback_macro_analysis()

    async def _update_macro_data(self):
        """Update macro indicators from various sources"""
        try:
            # In production, you would fetch from:
            # - Federal Reserve API (FRED)
            # - CoinGecko/CoinMarketCap
            # - Financial data providers

            # For now, use simulated/fallback data
            # These values can be manually updated or fetched from APIs

            # Simulate VIX reading (volatility index)
            # Low VIX (< 15) = complacency
            # Medium VIX (15-25) = normal
            # High VIX (> 25) = fear
            self.macro_data['vix'] = 18.5 + np.random.randn() * 2

            # Dollar Index (DXY)
            # Higher dollar = typically negative for risk assets
            self.macro_data['dollar_index'] = 103.5 + np.random.randn() * 0.5

            # Gold price (safe haven indicator)
            # Rising gold = risk-off sentiment
            self.macro_data['gold_price'] = 1950 + np.random.randn() * 10

            # 10-year Treasury yield
            # Higher yields = less attractive for risk assets
            self.macro_data['treasury_yield_10y'] = 4.5 + np.random.randn() * 0.1

            # BTC Dominance (can be fetched from CoinGecko)
            # Higher dominance = money flowing to BTC (safer crypto)
            self.macro_data['btc_dominance'] = 52.0 + np.random.randn() * 1

            logger.debug(f"Macro data updated: {self.macro_data}")

        except Exception as e:
            logger.error(f"Error updating macro data: {e}")

    def _determine_market_regime(self):
        """
        Determine overall market regime
        Returns: 'BULL', 'BEAR', 'NEUTRAL', 'CHOPPY'
        """
        vix = self.macro_data['vix']
        dollar = self.macro_data['dollar_index']
        gold = self.macro_data['gold_price']

        # Score system
        score = 0

        # VIX analysis
        if vix < 15:
            score += 2  # Low fear = bullish
        elif vix > 25:
            score -= 2  # High fear = bearish
        elif vix > 30:
            score -= 3  # Extreme fear = very bearish

        # Dollar strength
        if dollar > 105:
            score -= 1  # Strong dollar = bearish for crypto
        elif dollar < 100:
            score += 1  # Weak dollar = bullish for crypto

        # Gold (safe haven)
        if gold > 2000:
            score -= 1  # Risk-off sentiment
        elif gold < 1900:
            score += 1  # Risk-on sentiment

        # Determine regime
        if score >= 2:
            return 'BULL'
        elif score <= -2:
            return 'BEAR'
        elif abs(score) <= 1:
            return 'NEUTRAL'
        else:
            return 'CHOPPY'

    def _calculate_risk_appetite(self):
        """
        Calculate market risk appetite (0-1 scale)
        0 = Risk-off (fear)
        1 = Risk-on (greed)
        """
        vix = self.macro_data['vix']
        dollar = self.macro_data['dollar_index']
        gold = self.macro_data['gold_price']

        # VIX component (inverted - lower VIX = higher risk appetite)
        vix_component = max(0, min(1, (40 - vix) / 40))

        # Dollar component (inverted - lower dollar = higher risk appetite)
        dollar_component = max(0, min(1, (110 - dollar) / 15))

        # Gold component (inverted - lower gold = higher risk appetite)
        gold_component = max(0, min(1, (2100 - gold) / 300))

        # Weighted average
        risk_appetite = (
            vix_component * 0.5 +
            dollar_component * 0.3 +
            gold_component * 0.2
        )

        return risk_appetite

    def _estimate_crypto_correlation(self):
        """
        Estimate crypto correlation with macro conditions
        Returns: -1 to 1 (negative to positive correlation)
        """
        # Crypto typically has:
        # - Negative correlation with dollar strength
        # - Negative correlation with VIX (when VIX spikes, crypto drops)
        # - Mixed correlation with yields

        vix = self.macro_data['vix']
        dollar = self.macro_data['dollar_index']
        btc_dom = self.macro_data['btc_dominance']

        # Base correlation
        correlation = 0.0

        # VIX impact (inverse)
        if vix < 20:
            correlation += 0.2  # Low volatility = positive for crypto
        elif vix > 25:
            correlation -= 0.3  # High volatility = negative for crypto

        # Dollar impact (inverse)
        if dollar > 105:
            correlation -= 0.2  # Strong dollar = negative for crypto
        elif dollar < 100:
            correlation += 0.2  # Weak dollar = positive for crypto

        # BTC dominance (indicates crypto market health)
        if btc_dom > 55:
            correlation += 0.1  # Money in BTC = healthier crypto market
        elif btc_dom < 45:
            correlation -= 0.1  # Alt season or fear

        # Clamp to -1 to 1
        correlation = max(-1, min(1, correlation))

        return correlation

    def _generate_analysis(self, regime: str, risk_appetite: float):
        """Generate human-readable analysis"""
        risk_level = "HIGH" if risk_appetite > 0.7 else "MODERATE" if risk_appetite > 0.4 else "LOW"

        vix = self.macro_data['vix']
        dollar = self.macro_data['dollar_index']

        analysis = f"Market regime is {regime}. "
        analysis += f"Risk appetite is {risk_level} ({risk_appetite:.2f}). "

        if vix > 25:
            analysis += "Elevated volatility suggests caution. "
        elif vix < 15:
            analysis += "Low volatility indicates market complacency. "

        if dollar > 105:
            analysis += "Strong dollar may pressure crypto prices. "
        elif dollar < 100:
            analysis += "Weak dollar supports crypto upside. "

        return analysis

    def _fallback_macro_analysis(self):
        """Fallback analysis when data unavailable"""
        return {
            'regime': 'NEUTRAL',
            'risk_appetite': 0.5,
            'crypto_correlation': 0.0,
            'confidence': 0.3,
            'indicators': self.macro_data.copy(),
            'analysis': 'Macro data unavailable, using neutral baseline.'
        }

    def get_volatility_regime(self):
        """Get current volatility regime"""
        vix = self.macro_data['vix']

        if vix < 12:
            return {'level': 'EXTREMELY_LOW', 'description': 'Market complacency'}
        elif vix < 15:
            return {'level': 'LOW', 'description': 'Calm market'}
        elif vix < 20:
            return {'level': 'MODERATE', 'description': 'Normal volatility'}
        elif vix < 25:
            return {'level': 'ELEVATED', 'description': 'Increased uncertainty'}
        elif vix < 30:
            return {'level': 'HIGH', 'description': 'Market stress'}
        else:
            return {'level': 'EXTREME', 'description': 'Panic conditions'}

    def should_reduce_position_size(self):
        """Recommend position size adjustment based on macro conditions"""
        risk_appetite = self._calculate_risk_appetite()
        vix = self.macro_data['vix']

        # Reduce position size if:
        # - Low risk appetite
        # - High VIX
        # - Strong dollar

        if risk_appetite < 0.3 or vix > 30:
            return True, "High macro risk - reduce position size by 50%"
        elif risk_appetite < 0.4 or vix > 25:
            return True, "Elevated macro risk - reduce position size by 25%"
        else:
            return False, "Macro conditions acceptable for normal position sizing"

    def get_summary(self):
        """Get quick macro summary for UI display"""
        regime = self._determine_market_regime()
        risk_appetite = self._calculate_risk_appetite()
        volatility = self.get_volatility_regime()

        risk_label = "🟢 RISK-ON" if risk_appetite > 0.6 else "🔴 RISK-OFF" if risk_appetite < 0.4 else "🟡 NEUTRAL"

        return {
            'regime': regime,
            'risk_label': risk_label,
            'risk_appetite': risk_appetite,
            'volatility': volatility['level'],
            'vix': self.macro_data['vix'],
            'dollar_index': self.macro_data['dollar_index']
        }
