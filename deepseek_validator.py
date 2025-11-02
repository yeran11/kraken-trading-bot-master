"""
DeepSeek Validator - LLM-Based Signal Validation
Uses DeepSeek AI to validate trading signals with natural language reasoning
"""
import requests
import json
from loguru import logger
import os
from datetime import datetime

class DeepSeekValidator:
    """
    DeepSeek AI validator for trading signals
    Provides intelligent validation with natural language explanations
    """

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.base_url = "https://api.deepseek.com/v1"

        # 🧠 UPGRADED: Using DeepSeek-R1 Reasoning Model for superior trading analysis
        self.model = "deepseek-reasoner"  # Advanced reasoning with Chain-of-Thought
        self.temperature = 0.3  # Lower = more consistent
        self.max_tokens = 2000  # Increased for reasoning output (thinking + answer)

        if not self.api_key:
            logger.warning("⚠️  DeepSeek API key not found. Set DEEPSEEK_API_KEY in .env")
            logger.info("Validator will run in demo mode")
        else:
            logger.success("✓ DeepSeek-R1 Reasoning Model initialized")
            logger.info("🧠 Using advanced Chain-of-Thought reasoning for trading decisions")

    async def validate_signal(
        self,
        symbol: str,
        current_price: float,
        technical_signals: dict,
        sentiment: dict,
        market_data: dict,
        portfolio_context: dict = None,
        volatility_metrics: dict = None
    ):
        """
        Validate trading signal using DeepSeek AI with full market context
        Returns: {'action': str, 'confidence': float, 'position_size': float, 'reasoning': str, 'risks': list}
        """
        try:
            if not self.api_key:
                # Return demo response if no API key
                return self._demo_response(symbol, technical_signals)

            # Build comprehensive prompt with portfolio and volatility context
            prompt = self._build_prompt(
                symbol, current_price, technical_signals,
                sentiment, market_data, portfolio_context or {}, volatility_metrics or {}
            )

            # Call DeepSeek API
            response = await self._call_deepseek_api(prompt)

            # Parse response
            result = self._parse_ai_response(response)

            logger.info(f"🤖 DeepSeek: {result['action']} {symbol} (confidence: {result['confidence']}%)")
            logger.debug(f"Reasoning: {result['reasoning']}")

            return result

        except Exception as e:
            logger.error(f"DeepSeek validation error: {e}")
            return self._fallback_response(technical_signals)

    def _build_prompt(
        self,
        symbol: str,
        current_price: float,
        technical_signals: dict,
        sentiment: dict,
        market_data: dict,
        portfolio_context: dict,
        volatility_metrics: dict
    ):
        """Build comprehensive prompt for DeepSeek with full context"""

        # Format technical signals
        tech_summary = []
        if technical_signals.get('rsi'):
            rsi = technical_signals['rsi']
            if rsi > 70:
                tech_summary.append(f"RSI: {rsi:.1f} (OVERBOUGHT)")
            elif rsi < 30:
                tech_summary.append(f"RSI: {rsi:.1f} (OVERSOLD)")
            else:
                tech_summary.append(f"RSI: {rsi:.1f} (NEUTRAL)")

        if technical_signals.get('macd_signal'):
            tech_summary.append(f"MACD: {technical_signals['macd_signal']}")

        if technical_signals.get('supertrend'):
            tech_summary.append(f"Supertrend: {technical_signals['supertrend']}")

        if technical_signals.get('volume_ratio'):
            vol_ratio = technical_signals['volume_ratio']
            tech_summary.append(f"Volume: {vol_ratio:.2f}x average")

        # Format recent price action
        price_action = ""
        if market_data.get('recent_candles'):
            candles = market_data['recent_candles'][-5:]
            price_action = "Recent price action (last 5 periods):\n"
            for i, candle in enumerate(candles):
                change = ((candle['close'] - candle['open']) / candle['open'] * 100)
                emoji = "🟢" if change > 0 else "🔴"
                price_action += f"  {emoji} ${candle['close']:.6f} ({change:+.2f}%)\n"

        prompt = f"""You are an expert cryptocurrency trader with deep analytical reasoning capabilities. Analyze {symbol} and provide a trading recommendation.

**CURRENT MARKET DATA:**
- Current Price: ${current_price:.6f}
- Trading Pair: {symbol}
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC

**TECHNICAL ANALYSIS:**
{chr(10).join('- ' + s for s in tech_summary)}

**MARKET SENTIMENT:**
- Sentiment Score: {sentiment.get('label', 'NEUTRAL')} ({sentiment.get('score', 0.5):.2f})
- Confidence: {sentiment.get('confidence', 0.5):.0%}

{price_action}
"""

        # Add portfolio context if available
        if portfolio_context:
            total_positions = portfolio_context.get('total_positions', 0)
            max_positions = portfolio_context.get('max_positions', 10)
            positions_list = portfolio_context.get('positions', [])
            daily_pnl = portfolio_context.get('daily_pnl', 0)
            total_exposure = portfolio_context.get('total_exposure_usd', 0)

            strategy_breakdown = portfolio_context.get('strategy_breakdown', {})
            strategy_text = "\n".join([f"  * {strategy}: {count} positions" for strategy, count in strategy_breakdown.items()])

            prompt += f"""
**CURRENT PORTFOLIO:**
- Active Positions: {total_positions}/{max_positions}
- Total Exposure: ${total_exposure:.2f}
- Today's P&L: ${daily_pnl:.2f} ({(daily_pnl/max(total_exposure, 1))*100:+.2f}%)
- Strategy Allocation:
{strategy_text}
- Pairs Held: {', '.join(positions_list[:5])}{'...' if len(positions_list) > 5 else ''}

**PORTFOLIO CONSIDERATIONS:**
- Assess if adding this position improves diversification
- Consider if you're over-allocated to one strategy
- Factor in total portfolio risk exposure
"""

        # Add volatility context if available
        if volatility_metrics:
            atr = volatility_metrics.get('atr', 0)
            atr_percent = volatility_metrics.get('atr_percent', 0)
            volatility_regime = volatility_metrics.get('regime', 'NORMAL')
            avg_range = volatility_metrics.get('avg_daily_range', 0)

            prompt += f"""
**VOLATILITY ANALYSIS:**
- ATR (14-period): ${atr:.8f} ({atr_percent:.2f}% of price)
- Market Condition: {volatility_regime}
- Average Daily Range: {avg_range:.2f}%

**VOLATILITY GUIDANCE:**
- High volatility (>5%): Use wider stops (3-5%), smaller position sizes
- Medium volatility (2-5%): Standard risk parameters
- Low volatility (<2%): Tighter stops acceptable (1-2%)
"""

        prompt += """
**REASONING INSTRUCTIONS:**
Think step-by-step through the following:

1. **Technical Signal Strength**: Are the technical indicators showing clear consensus or conflict?
2. **Sentiment Alignment**: Does market sentiment support or contradict the technical signals?
3. **Portfolio Impact**: How does this trade affect overall portfolio diversification and risk?
4. **Volatility Adjustment**: Given current market volatility, what are appropriate position size and stops?
5. **Risk Assessment**: What could go wrong with each potential action (BUY/SELL/HOLD)?
6. **Historical Context**: Based on the recent price action, what's the momentum?
7. **Probability Weighting**: What's the likelihood of success for each action?
8. **Risk/Reward Calculation**: Calculate optimal position size, stop-loss, and take-profit levels
9. **Final Decision**: Which action offers the best risk/reward ratio considering all factors?

After your reasoning, provide your final recommendation in this JSON format:
{{
    "action": "BUY" or "SELL" or "HOLD",
    "confidence": 0-100,
    "position_size_percent": 1-20,
    "stop_loss_percent": 0.5-5.0,
    "take_profit_percent": 1.0-15.0,
    "reasoning": "2-3 sentences explaining your decision based on your analysis",
    "risks": ["risk1", "risk2", "risk3"]
}}

**POSITION SIZING GUIDANCE:**
- High conviction (75%+): 12-20% position size
- Medium conviction (65-75%): 8-12% position size
- Low conviction (55-65%): 3-8% position size

**STOP-LOSS/TAKE-PROFIT GUIDANCE:**
- Set stop-loss based on volatility and support levels (not arbitrary %)
- Set take-profit based on resistance and risk/reward ratio (aim for 2:1 minimum)
- For volatile markets: Wider stops (2-5%)
- For stable markets: Tighter stops (0.5-2%)

**IMPORTANT GUIDELINES:**
- ULTRA-AGGRESSIVE MODE: Look for ANY profitable opportunity above 50% confidence
- Recommend BUY if confidence exceeds 50% (lowered from 55% for more opportunities)
- For high-conviction setups (70%+), consider larger position sizes (15-20%)
- For moderate setups (55-70%), use medium position sizes (8-12%)
- For acceptable setups (50-55%), use smaller position sizes (3-8%)
- This is REAL MONEY but we want to MAXIMIZE profitable trades
- Small consistent profits compound into large gains
- Even moderate signals (50-60% confidence) can be profitable with proper risk management
- Factor in upside potential FIRST, then manage downside risk with stops
- BE AGGRESSIVE: Find opportunities, don't be overly cautious
"""

        return prompt

    async def _call_deepseek_api(self, prompt: str):
        """Call DeepSeek-R1 Reasoning API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional cryptocurrency trading analyst with deep reasoning capabilities. Think through the analysis step-by-step, considering all factors before making a recommendation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
                # NOTE: Reasoning model doesn't use response_format - it thinks first, then responds
            }

            logger.debug(f"🧠 Calling DeepSeek-R1 reasoning model...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60  # Increased timeout for reasoning (thinking takes time)
            )

            response.raise_for_status()
            data = response.json()

            message = data['choices'][0]['message']

            # Extract reasoning process (Chain-of-Thought)
            reasoning_content = message.get('reasoning_content', '')
            final_answer = message.get('content', '')

            # Log the reasoning process
            if reasoning_content:
                logger.debug(f"🤔 AI Thinking Process:\n{reasoning_content[:500]}...")  # First 500 chars

            logger.debug(f"💡 AI Final Answer: {final_answer[:200]}...")

            # Return both reasoning and answer
            return {
                'reasoning': reasoning_content,
                'answer': final_answer
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek-R1 API error: {e}")
            raise

    def _parse_ai_response(self, response_data):
        """Parse AI response from DeepSeek-R1 reasoning model"""
        try:
            # Handle dict response from reasoning model
            if isinstance(response_data, dict):
                reasoning_process = response_data.get('reasoning', '')
                answer_text = response_data.get('answer', '')
            else:
                # Fallback for string response
                reasoning_process = ''
                answer_text = response_data

            # Try to parse JSON from answer
            try:
                # Look for JSON in the answer
                data = json.loads(answer_text)
            except json.JSONDecodeError:
                # Try to extract JSON if wrapped in markdown or text
                import re
                json_match = re.search(r'\{[^}]+\}', answer_text)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    raise ValueError("No JSON found in response")

            action = data.get('action', 'HOLD').upper()
            confidence = float(data.get('confidence', 50))
            reasoning = data.get('reasoning', 'No reasoning provided')
            risks = data.get('risks', [])

            # Extract new autonomous trading parameters
            position_size = float(data.get('position_size_percent', 10))
            stop_loss = float(data.get('stop_loss_percent', 2.0))
            take_profit = float(data.get('take_profit_percent', 3.5))

            # Validate action
            if action not in ['BUY', 'SELL', 'HOLD']:
                action = 'HOLD'

            # Clamp confidence to 0-100
            confidence = max(0, min(100, confidence))

            # Validate and clamp autonomous trading parameters
            position_size = max(1, min(20, position_size))  # 1-20%
            stop_loss = max(0.5, min(5.0, stop_loss))  # 0.5-5%
            take_profit = max(1.0, min(15.0, take_profit))  # 1-15%

            # Calculate risk/reward ratio
            risk_reward_ratio = take_profit / stop_loss if stop_loss > 0 else 0

            # Combine Chain-of-Thought reasoning with final reasoning
            full_reasoning = reasoning
            if reasoning_process:
                # Include thinking process summary
                thinking_summary = reasoning_process[:300] + "..." if len(reasoning_process) > 300 else reasoning_process
                full_reasoning = f"[Deep Analysis] {thinking_summary}\n\n[Decision] {reasoning}"

            return {
                'action': action,
                'confidence': confidence,
                'position_size_percent': position_size,
                'stop_loss_percent': stop_loss,
                'take_profit_percent': take_profit,
                'risk_reward_ratio': risk_reward_ratio,
                'reasoning': full_reasoning,
                'risks': risks,
                'source': 'deepseek-r1',
                'thinking_process': reasoning_process  # Full CoT for debugging
            }

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            # Try to extract action from text
            response_text = str(response_data)
            response_upper = response_text.upper()

            if 'BUY' in response_upper:
                action = 'BUY'
            elif 'SELL' in response_upper:
                action = 'SELL'
            else:
                action = 'HOLD'

            return {
                'action': action,
                'confidence': 50,
                'position_size_percent': 10,
                'stop_loss_percent': 2.0,
                'take_profit_percent': 3.5,
                'risk_reward_ratio': 1.75,
                'reasoning': response_text[:200] if isinstance(response_text, str) else 'Parse error',
                'risks': [],
                'source': 'deepseek-r1-fallback'
            }

    def _demo_response(self, symbol: str, technical_signals: dict):
        """Demo response when no API key"""
        # Analyze technical signals
        signal_strength = 0
        reasoning_parts = []

        if technical_signals.get('rsi'):
            rsi = technical_signals['rsi']
            if rsi < 30:
                signal_strength += 2
                reasoning_parts.append(f"RSI oversold at {rsi:.1f}")
            elif rsi > 70:
                signal_strength -= 2
                reasoning_parts.append(f"RSI overbought at {rsi:.1f}")

        if technical_signals.get('macd_signal') == 'BULLISH':
            signal_strength += 1
            reasoning_parts.append("MACD showing bullish crossover")
        elif technical_signals.get('macd_signal') == 'BEARISH':
            signal_strength -= 1
            reasoning_parts.append("MACD showing bearish crossover")

        if technical_signals.get('volume_ratio', 1.0) > 1.5:
            signal_strength += 1
            reasoning_parts.append("Strong volume confirmation")

        # Determine action
        if signal_strength >= 2:
            action = 'BUY'
            confidence = min(70 + (signal_strength * 5), 90)
        elif signal_strength <= -2:
            action = 'SELL'
            confidence = min(70 + (abs(signal_strength) * 5), 90)
        else:
            action = 'HOLD'
            confidence = 60

        reasoning = ". ".join(reasoning_parts) if reasoning_parts else "Signals are mixed or neutral"

        # Determine position sizing based on signal strength
        position_size = 5 + (abs(signal_strength) * 2)  # 5-15%
        stop_loss = 2.0
        take_profit = 3.5

        return {
            'action': action,
            'confidence': confidence,
            'position_size_percent': position_size,
            'stop_loss_percent': stop_loss,
            'take_profit_percent': take_profit,
            'risk_reward_ratio': take_profit / stop_loss,
            'reasoning': f"{reasoning}. Demo mode - get DeepSeek API key for full AI analysis.",
            'risks': ["Demo mode active", "Set DEEPSEEK_API_KEY for real AI"],
            'source': 'demo'
        }

    def _fallback_response(self, technical_signals: dict):
        """Fallback response on error"""
        return {
            'action': 'HOLD',
            'confidence': 50,
            'position_size_percent': 10,
            'stop_loss_percent': 2.0,
            'take_profit_percent': 3.5,
            'risk_reward_ratio': 1.75,
            'reasoning': 'AI validation unavailable, defaulting to HOLD for safety',
            'risks': ['AI service temporarily unavailable'],
            'source': 'fallback'
        }

    def get_market_analysis(self, symbol: str, timeframe: str = '1h'):
        """
        Get general market analysis from DeepSeek
        For educational/informational purposes
        """
        try:
            if not self.api_key:
                return f"Market analysis for {symbol} unavailable (demo mode)"

            prompt = f"""Provide a brief market analysis for {symbol} on {timeframe} timeframe.
Include:
1. Recent trend
2. Key support/resistance levels
3. Market sentiment
4. Short-term outlook

Keep it concise (3-4 sentences)."""

            # Simplified API call
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 300
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )

            response.raise_for_status()
            data = response.json()
            analysis = data['choices'][0]['message']['content']

            return analysis

        except Exception as e:
            logger.error(f"Market analysis error: {e}")
            return f"Market analysis temporarily unavailable"
