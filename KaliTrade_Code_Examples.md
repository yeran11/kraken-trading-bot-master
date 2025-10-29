# KaliTrade - Key Code Examples & Implementation Details

## 1. AI Ensemble Signal Generation

### Complete Signal Pipeline
```python
# Location: trading-bot/src/strategies/advanced_ai_strategy.py
class AdvancedAIStrategy:
    async def generate_signal(self, symbol: str) -> TradingSignal:
        """Main signal generation using 4-model ensemble"""
        
        # 1. Get market condition
        market_condition = await self.analyze_market(symbol)
        
        # 2. Extract features for ML models
        market_data = await self.market_data_service.get_market_data(symbol)
        features = self._extract_features(market_data)
        
        # 3. Get AI predictions
        sentiment_result = await self.ai_service.analyze_sentiment(symbol)
        price_prediction = await self.ai_service.predict_price_movement(features)
        macro_result = await self.ai_service.analyze_macro_conditions()
        
        # 4. Generate individual signals
        signals = {
            'sentiment': self._generate_sentiment_signal(sentiment_result, market_condition),
            'technical': self._generate_technical_signal(market_data, features),
            'microstructure': self._generate_microstructure_signal(market_data),
            'macro': self._generate_macro_signal(macro_result, market_condition)
        }
        
        # 5. Combine signals using ensemble weights
        final_signal = self._combine_signals(signals, market_condition)
        
        # 6. Apply risk management
        final_signal = await self._apply_risk_management(final_signal, symbol, market_data)
        
        return final_signal
```

### Ensemble Combination Logic
```python
def _combine_signals(self, signals: Dict[str, TradingSignal], 
                    market_condition: MarketCondition) -> TradingSignal:
    """Weighted ensemble voting"""
    buy_weight = 0
    sell_weight = 0
    total_confidence = 0
    reasoning_parts = []
    
    for signal_name, signal in signals.items():
        weight = self.ensemble_weights.get(signal_name, 0.25)
        
        if signal.signal_type == SignalType.BUY:
            buy_weight += weight * signal.confidence
        elif signal.signal_type == SignalType.SELL:
            sell_weight += weight * signal.confidence
        
        total_confidence += weight * signal.confidence
        reasoning_parts.append(f"{signal_name}: {signal.reasoning}")
    
    # Final decision based on weighted votes
    if buy_weight > sell_weight and buy_weight > self.min_confidence:
        signal_type = SignalType.BUY
        confidence = buy_weight
    elif sell_weight > buy_weight and sell_weight > self.min_confidence:
        signal_type = SignalType.SELL
        confidence = sell_weight
    else:
        signal_type = SignalType.HOLD
        confidence = total_confidence * 0.5
    
    return TradingSignal(
        signal_type=signal_type,
        confidence=confidence,
        reasoning=" | ".join(reasoning_parts)
    )
```

## 2. HuggingFace Sentiment Analysis

```python
# Location: trading-bot/src/services/ai_service.py
async def _initialize_sentiment_analyzer(self):
    """Initialize HuggingFace sentiment model"""
    try:
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            device=0 if torch.cuda.is_available() else -1
        )
        logger.info("Sentiment analyzer initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize sentiment analyzer: {e}")
        self.sentiment_analyzer = None

async def analyze_sentiment(self, symbol: str) -> Dict[str, Any]:
    """Analyze market sentiment for symbol"""
    
    # Get data sources
    news_data = await self._get_news_data(symbol)
    social_data = await self._get_social_data(symbol)
    
    sentiment_score = 0.5  # Neutral baseline
    confidence = 0.5
    
    if self.sentiment_analyzer and (news_data or social_data):
        # Analyze news sentiment
        if news_data:
            news_sentiment = await self._analyze_text_sentiment(news_data)
            sentiment_score = (sentiment_score + news_sentiment) / 2
            confidence = max(confidence, 0.7)
        
        # Analyze social sentiment
        if social_data:
            social_sentiment = await self._analyze_text_sentiment(social_data)
            sentiment_score = (sentiment_score + social_sentiment) / 2
            confidence = max(confidence, 0.6)
    
    return {
        'score': sentiment_score,
        'confidence': confidence,
        'sources': ['news', 'social_media'],
        'reasoning': f'Sentiment analysis based on data sources'
    }

async def _analyze_text_sentiment(self, texts: List[str]) -> float:
    """Analyze sentiment of multiple texts"""
    sentiments = []
    
    for text in texts:
        # Limit text length to 512 tokens
        result = self.sentiment_analyzer(text[:512])
        
        # Convert label to 0-1 scale
        if result[0]['label'] == 'LABEL_0':  # Negative
            sentiment = 0.0
        elif result[0]['label'] == 'LABEL_1':  # Neutral
            sentiment = 0.5
        else:  # LABEL_2 - Positive
            sentiment = 1.0
        
        # Weight by model confidence
        weighted_sentiment = sentiment * result[0]['score']
        sentiments.append(weighted_sentiment)
    
    return np.mean(sentiments) if sentiments else 0.5
```

## 3. Random Forest Price Prediction

```python
# Location: trading-bot/src/services/ai_service.py
async def _initialize_price_predictor(self):
    """Initialize Random Forest for price prediction"""
    self.price_predictor = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    
    self.volatility_predictor = RandomForestRegressor(
        n_estimators=50,
        max_depth=8,
        random_state=42,
        n_jobs=-1
    )

async def predict_price_movement(self, features: Dict[str, Any]) -> Dict[str, Any]:
    """Predict price movement using ML models"""
    
    # Convert features to numpy array (10 dimensions)
    feature_vector = self._extract_features(features)
    
    if len(feature_vector) == 0:
        return {
            'price_prediction': 0.0,
            'volatility_prediction': 0.02,
            'confidence': 0.3
        }
    
    # Normalize features
    feature_vector_scaled = self.scaler.fit_transform([feature_vector])
    
    # Make predictions
    price_prediction = self.price_predictor.predict(feature_vector_scaled)[0]
    volatility_prediction = self.volatility_predictor.predict(feature_vector_scaled)[0]
    
    # Calculate confidence based on feature quality
    confidence = self._calculate_prediction_confidence(features)
    
    return {
        'price_prediction': float(price_prediction),
        'volatility_prediction': float(volatility_prediction),
        'confidence': confidence
    }

def _extract_features(self, features: Dict[str, Any]) -> np.ndarray:
    """Extract 10D feature vector"""
    feature_list = []
    
    # Price features (3D)
    feature_list.extend([
        features.get('price_change_1h', 0),
        features.get('price_change_4h', 0),
        features.get('price_change_24h', 0)
    ])
    
    # Volume features (2D)
    feature_list.extend([
        features.get('volume_ratio', 1.0),
        features.get('volume_trend', 0)
    ])
    
    # Volatility features (2D)
    feature_list.extend([
        features.get('volatility_1h', 0.02),
        features.get('volatility_24h', 0.02)
    ])
    
    # Technical indicators (3D)
    feature_list.extend([
        features.get('rsi', 50) / 100,  # Normalize RSI
        features.get('macd', 0),
        features.get('bollinger_position', 0.5)
    ])
    
    return np.array(feature_list)
```

## 4. Kelly Criterion Position Sizing

```python
# Location: trading-bot/src/services/risk_manager.py
async def calculate_position_size(self, symbol: str, confidence: float, 
                                 current_price: float, portfolio_value: float) -> float:
    """Calculate optimal position size using Kelly Criterion"""
    
    self.portfolio_value = portfolio_value
    current_positions = self.current_positions.copy()
    
    # Use confidence as proxy for win rate
    win_rate = confidence
    avg_win = 0.15   # 15% average win (take profit)
    avg_loss = 0.05  # 5% average loss (stop loss)
    
    # Calculate Kelly fraction
    kelly_fraction = self._calculate_kelly_fraction(win_rate, avg_win, avg_loss)
    
    # Apply risk limits
    position_size = self._apply_risk_limits(
        symbol, kelly_fraction, current_price, portfolio_value, current_positions
    )
    
    # Ensure minimum position size
    if position_size > 0 and position_size < self.min_position_size:
        position_size = self.min_position_size
    
    return position_size

def _calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Kelly Criterion: f = (bp - q) / b
    where:
        b = odds (avg_win / avg_loss)
        p = win_rate
        q = loss_rate (1 - p)
    """
    if avg_loss <= 0:
        return 0.0
    
    b = avg_win / avg_loss      # Odds
    p = win_rate                 # Win probability
    q = 1 - p                    # Loss probability
    
    kelly = (b * p - q) / b
    
    # Apply Kelly fraction limit (conservative 0.25)
    kelly = max(0, min(kelly, self.kelly_fraction))
    
    return kelly

def _apply_risk_limits(self, symbol: str, kelly_fraction: float, current_price: float,
                      portfolio_value: float, current_positions: Dict) -> float:
    """Apply multiple risk constraints to position size"""
    
    position_size = kelly_fraction
    
    # Limit by maximum position size
    position_size = min(position_size, self.max_position_size)  # 10% max
    
    # Calculate position value and risk
    position_value = position_size * portfolio_value
    max_loss = position_value * self.max_position_risk  # 0.5% risk
    
    # Adjust for stop loss
    if max_loss > 0:
        stop_loss_pct = max_loss / position_value
        position_size = min(position_size, stop_loss_pct * 2)  # 2x safety margin
    
    # Check correlation with existing positions
    position_size = self._adjust_for_correlation(symbol, position_size, current_positions)
    
    # Check portfolio risk limits
    position_size = self._adjust_for_portfolio_risk(position_size, current_positions)
    
    return max(0.0, position_size)
```

## 5. Technical Indicator Calculations

```python
# Location: trading-bot/src/services/ai_service.py

def _calculate_rsi(self, prices: pd.Series) -> float:
    """Calculate RSI (14 period)"""
    if len(prices) < 14:
        return 50.0
    
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

def _calculate_macd(self, prices: pd.Series) -> float:
    """Calculate MACD"""
    if len(prices) < 26:
        return 0.0
    
    ema_12 = prices.ewm(span=12).mean()
    ema_26 = prices.ewm(span=26).mean()
    macd = ema_12 - ema_26
    
    return float(macd.iloc[-1]) if not pd.isna(macd.iloc[-1]) else 0.0

def _calculate_bollinger_position(self, data: pd.DataFrame) -> float:
    """Calculate position within Bollinger Bands (20 period, 2 std dev)"""
    if len(data) < 20:
        return 0.5
    
    close = data['close']
    sma = close.rolling(window=20).mean()
    std_dev = close.rolling(window=20).std()
    
    upper_band = sma + (std_dev * 2)
    lower_band = sma - (std_dev * 2)
    
    current_price = close.iloc[-1]
    upper = upper_band.iloc[-1]
    lower = lower_band.iloc[-1]
    
    if pd.isna(upper) or pd.isna(lower) or upper == lower:
        return 0.5
    
    position = (current_price - lower) / (upper - lower)
    return float(position)
```

## 6. Macroeconomic Analysis

```python
# Location: trading-bot/src/services/ai_service.py

async def analyze_macro_conditions(self) -> Dict[str, Any]:
    """Analyze macro economic conditions"""
    
    # Get macro economic data
    macro_data = await self._get_macro_data()
    
    # Analyze correlation with crypto markets
    crypto_correlation = self._calculate_crypto_correlation(macro_data)
    
    # Determine market regime
    market_regime = self._determine_market_regime(macro_data)
    
    # Calculate risk appetite
    risk_appetite = self._calculate_risk_appetite(macro_data)
    
    return {
        'crypto_correlation': crypto_correlation,
        'market_regime': market_regime,
        'risk_appetite': risk_appetite,
        'confidence': 0.7
    }

async def _get_macro_data(self) -> Dict[str, Any]:
    """Get macro economic indicators"""
    return {
        'dollar_index': 103.5,      # USD strength
        'gold_price': 1950.0,       # Safe haven asset
        'vix': 18.5,                # Volatility index
        'treasury_yield': 4.5,      # Risk-free rate
        'inflation_rate': 3.2       # Inflation metric
    }

def _calculate_crypto_correlation(self, macro_data: Dict[str, Any]) -> float:
    """Calculate correlation between crypto and macro conditions"""
    dollar_strength = macro_data.get('dollar_index', 100) / 100
    risk_appetite = 1.0 - (macro_data.get('vix', 20) / 100)
    
    # Crypto typically has negative correlation with dollar strength
    # and positive correlation with risk appetite
    correlation = (risk_appetite - dollar_strength) / 2 + 0.5
    
    return max(0.0, min(1.0, correlation))

def _determine_market_regime(self, macro_data: Dict[str, Any]) -> str:
    """Determine bull/bear/neutral market regime"""
    vix = macro_data.get('vix', 20)
    treasury_yield = macro_data.get('treasury_yield', 4.0)
    
    if vix < 15 and treasury_yield < 3.0:
        return 'bull'          # Low volatility, low rates
    elif vix > 25 and treasury_yield > 5.0:
        return 'bear'          # High volatility, high rates
    else:
        return 'neutral'       # Mixed conditions

def _calculate_risk_appetite(self, macro_data: Dict[str, Any]) -> float:
    """Calculate overall risk appetite (0-1 scale)"""
    vix = macro_data.get('vix', 20)
    treasury_yield = macro_data.get('treasury_yield', 4.0)
    
    # Risk appetite inversely related to VIX and Treasury yields
    risk_appetite = 1.0 - (vix / 50.0) - (treasury_yield / 20.0)
    
    return max(0.0, min(1.0, risk_appetite))
```

## 7. Market Data Service with CCXT

```python
# Location: trading-bot/src/services/market_data_service.py

class MarketDataService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.exchanges = {}
        self.data_cache = {}
        self.is_running = False
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize CCXT exchange connections"""
        try:
            public_exchanges = ['binance', 'coinbase', 'kraken']
            for exchange_name in public_exchanges:
                try:
                    exchange_class = getattr(ccxt, exchange_name)
                    exchange = exchange_class({
                        'enableRateLimit': True,
                    })
                    self.exchanges[exchange_name] = exchange
                    logger.info(f"Initialized {exchange_name}")
                except Exception as e:
                    logger.warning(f"Failed to initialize {exchange_name}: {e}")
        except Exception as e:
            logger.error(f"Error initializing exchanges: {e}")
    
    async def get_market_data(self, symbol: str, 
                            timeframe: str = '1h', 
                            limit: int = 100) -> Optional[pd.DataFrame]:
        """Get OHLCV data for symbol"""
        
        # Check cache first (5-minute TTL)
        if symbol in self.data_cache:
            cached_data = self.data_cache[symbol]
            if datetime.now() - cached_data['last_updated'] < timedelta(minutes=5):
                return cached_data['data'].tail(limit)
        
        # Fetch fresh data from exchange
        await self._update_market_data(symbol)
        
        if symbol in self.data_cache:
            return self.data_cache[symbol]['data'].tail(limit)
        
        return None
    
    async def _update_market_data(self, symbol: str):
        """Fetch OHLCV data from exchange"""
        for exchange_name, exchange in self.exchanges.items():
            try:
                # Fetch 1h OHLCV data (100 candles)
                ohlcv = await self._fetch_ohlcv_safe(
                    exchange, symbol, '1h', 100
                )
                
                if ohlcv and len(ohlcv) > 0:
                    # Convert to DataFrame
                    df = pd.DataFrame(
                        ohlcv, 
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    # Cache the data
                    self.data_cache[symbol] = {
                        'data': df,
                        'exchange': exchange_name,
                        'last_updated': datetime.now()
                    }
                    break
            except Exception as e:
                logger.debug(f"Failed to get {symbol} from {exchange_name}: {e}")
    
    async def _fetch_ohlcv_safe(self, exchange, symbol: str, 
                               timeframe: str = '1h', 
                               limit: int = 100) -> Optional[List]:
        """Safely fetch OHLCV data in thread pool"""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, exchange.fetch_ohlcv, symbol, timeframe, None, limit
            )
        except Exception as e:
            logger.debug(f"Error fetching OHLCV: {e}")
            return None
```

## 8. Real-Time Trading via Express/Socket.io

```typescript
// Location: backend/src/index.ts

// Initialize services
const tradingBotService = new TradingBotService(prisma, io);
const marketDataService = new MarketDataService(prisma);
const realTimeMarketDataService = new RealTimeMarketDataService(io, prisma);

// Socket.io real-time updates
io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`);

  socket.on('join-room', (userId: string) => {
    socket.join(`user-${userId}`);
  });

  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`);
  });
});

// Start services
const startServices = async () => {
  try {
    await marketDataService.start();
    await tradingBotService.start();
    await realTimeMarketDataService.start();
    console.log('All services started successfully');
  } catch (error) {
    console.error('Error starting services:', error);
    process.exit(1);
  }
};

// Trade execution endpoint
app.post('/api/trading/execute', authenticateToken, async (req, res) => {
  try {
    const { symbol, side, quantity, price } = req.body;
    
    // Execute trade
    const result = await tradingBotService.executeTrade(req.user.id, {
      symbol,
      side,
      quantity,
      price
    });
    
    // Notify user via WebSocket
    io.to(`user-${req.user.id}`).emit('tradeExecuted', result);
    
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## 9. Risk-Aware Signal Application

```python
# Location: trading-bot/src/strategies/advanced_ai_strategy.py

async def _apply_risk_management(self, signal: TradingSignal, 
                                symbol: str, 
                                market_data: pd.DataFrame) -> TradingSignal:
    """Apply risk management to trading signal"""
    
    if signal.signal_type == SignalType.HOLD:
        return signal
    
    # Calculate volatility-adjusted position size
    volatility = self._calculate_volatility(market_data)
    risk_adjusted_size = min(
        self.max_position_size,
        self.max_position_size * (0.02 / volatility)  # Inverse volatility scaling
    )
    
    # Get current price
    if 'close' in market_data.columns:
        current_price = market_data['close'].iloc[-1]
    else:
        current_price = market_data.iloc[-1, -1]
    
    # Calculate stop loss and take profit
    if signal.signal_type == SignalType.BUY:
        stop_loss = current_price * (1 - self.stop_loss_pct)      # 5% below
        take_profit = current_price * (1 + self.take_profit_pct)  # 15% above
    else:  # SELL
        stop_loss = current_price * (1 + self.stop_loss_pct)      # 5% above
        take_profit = current_price * (1 - self.take_profit_pct)  # 15% below
    
    return TradingSignal(
        signal_type=signal.signal_type,
        confidence=signal.confidence,
        reasoning=signal.reasoning,
        stop_loss=stop_loss,
        take_profit=take_profit,
        position_size=risk_adjusted_size
    )
```

## 10. Prisma Database Schema (Key Models)

```prisma
// Location: backend/prisma/schema.prisma

model Trade {
  id           String     @id @default(cuid())
  userId       String
  strategyId   String?
  symbol       String
  side         TradeSide   // BUY/SELL
  type         TradeType   // MARKET/LIMIT/STOP
  amount       Decimal
  price        Decimal
  fee          Decimal    @default(0)
  status       TradeStatus
  exchangeName String
  executedAt   DateTime?
  createdAt    DateTime   @default(now())
  updatedAt    DateTime   @updatedAt

  user     User             @relation(fields: [userId], references: [id])
  strategy TradingStrategy? @relation(fields: [strategyId], references: [id])
  
  @@map("trades")
}

model TradingStrategy {
  id          String       @id @default(cuid())
  userId      String
  name        String
  description String?
  type        StrategyType
  config      Json         // Strategy parameters
  isActive    Boolean      @default(false)
  isDefault   Boolean      @default(false)
  createdAt   DateTime     @default(now())
  updatedAt   DateTime     @updatedAt

  user   User    @relation(fields: [userId], references: [id])
  trades Trade[]
  
  @@map("trading_strategies")
}

model Portfolio {
  id           String  @id @default(cuid())
  userId       String
  name         String
  totalValue   Decimal @default(0)
  totalCost    Decimal @default(0)
  totalProfit  Decimal @default(0)
  profitMargin Decimal @default(0)
  positions    Json    // Array of positions
  createdAt    DateTime @default(now())
  updatedAt    DateTime @updatedAt

  user User @relation(fields: [userId], references: [id])
  
  @@map("portfolios")
}

enum StrategyType {
  MOVING_AVERAGE_CROSSOVER
  RSI_DIVERGENCE
  BOLLINGER_BANDS
  MACD_SIGNAL
  CUSTOM_AI
  SENTIMENT_ANALYSIS
  ARBITRAGE
  MARKET_MAKING
  GRID_TRADING
  DCA
}

enum TradeSide {
  BUY
  SELL
}

enum TradeType {
  MARKET
  LIMIT
  STOP
  STOP_LIMIT
}

enum TradeStatus {
  PENDING
  FILLED
  CANCELLED
  REJECTED
  PARTIALLY_FILLED
}
```

---

## Key Takeaways

1. **Ensemble Approach**: 4 independent models combined with weighted voting
2. **Kelly Criterion**: Mathematical approach to position sizing with risk constraints
3. **HuggingFace Integration**: Pre-trained NLP models for sentiment analysis
4. **CCXT Abstraction**: Unified interface for 140+ cryptocurrency exchanges
5. **Async/Await**: Efficient concurrent operations for real-time trading
6. **Real-time Updates**: Socket.io integration for live dashboard
7. **Risk Limits**: Multiple layers of risk constraints (position, portfolio, correlation)
8. **Data Caching**: 5-minute TTL to reduce API calls
9. **Type Safety**: TypeScript + Prisma for database-level type safety
10. **Modular Architecture**: Services easily extended with new strategies

