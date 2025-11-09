"""
Data Manager - Fetch and manage historical market data
"""
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import ccxt
import os
import json


class DataManager:
    """
    Manages historical market data for backtesting
    
    Features:
    - Fetch data from Kraken via CCXT
    - Cache data locally to avoid repeated API calls
    - Support multiple timeframes
    - Data quality validation
    """
    
    def __init__(self, cache_dir: str = 'data_cache'):
        self.cache_dir = cache_dir
        self.exchange = ccxt.kraken({'enableRateLimit': True})
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info(f"✓ Data Manager initialized (cache: {cache_dir})")
    
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USD')
            timeframe: Candle timeframe ('1m', '5m', '1h', '4h', '1d')
            start_date: Start date (default: 90 days ago)
            end_date: End date (default: now)
            use_cache: Whether to use cached data
        
        Returns:
            DataFrame with OHLCV data
        """
        # Default dates
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=90)
        
        # Check cache
        cache_file = self._get_cache_filename(symbol, timeframe, start_date, end_date)
        
        if use_cache and os.path.exists(cache_file):
            logger.info(f"📂 Loading cached data: {cache_file}")
            return self._load_from_cache(cache_file)
        
        # Fetch from exchange
        logger.info(f"📡 Fetching {symbol} {timeframe} data from {start_date} to {end_date}")
        
        try:
            # Convert to milliseconds
            since = int(start_date.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)
            
            all_candles = []
            current_since = since
            
            # Fetch in batches (CCXT limit is usually 720 candles)
            while current_since < end_ms:
                candles = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=current_since,
                    limit=500
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                # Update since to last candle timestamp
                current_since = candles[-1][0] + 1
                
                logger.debug(f"Fetched {len(candles)} candles, total: {len(all_candles)}")
            
            # Convert to DataFrame
            df = pd.DataFrame(
                all_candles,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # Validate data
            if self._validate_data(df):
                # Save to cache
                self._save_to_cache(df, cache_file)
                logger.success(f"✅ Fetched {len(df)} candles for {symbol}")
                return df
            else:
                logger.error("❌ Data validation failed")
                return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return pd.DataFrame()
    
    def _get_cache_filename(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """Generate cache filename"""
        symbol_clean = symbol.replace('/', '_')
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        
        return os.path.join(
            self.cache_dir,
            f"{symbol_clean}_{timeframe}_{start_str}_{end_str}.parquet"
        )
    
    def _save_to_cache(self, df: pd.DataFrame, cache_file: str):
        """Save DataFrame to cache"""
        try:
            df.to_parquet(cache_file)
            logger.debug(f"💾 Saved to cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def _load_from_cache(self, cache_file: str) -> pd.DataFrame:
        """Load DataFrame from cache"""
        try:
            df = pd.read_parquet(cache_file)
            logger.debug(f"✅ Loaded {len(df)} candles from cache")
            return df
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return pd.DataFrame()
    
    def _validate_data(self, df: pd.DataFrame) -> bool:
        """Validate data quality"""
        if df.empty:
            logger.error("Data is empty")
            return False
        
        # Check for required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            logger.error("Missing required columns")
            return False
        
        # Check for NaN values
        if df[required_columns].isnull().any().any():
            logger.warning("Data contains NaN values")
            # Fill NaN with forward fill
            df.fillna(method='ffill', inplace=True)
        
        # Check for zero/negative prices
        if (df[['open', 'high', 'low', 'close']] <= 0).any().any():
            logger.error("Data contains zero or negative prices")
            return False
        
        # Check high >= low
        if (df['high'] < df['low']).any():
            logger.error("Data contains invalid high/low values")
            return False
        
        return True
    
    def get_multiple_timeframes(
        self,
        symbol: str,
        timeframes: list,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple timeframes
        
        Args:
            symbol: Trading pair
            timeframes: List of timeframes ['5m', '1h', '4h']
            start_date: Start date
            end_date: End date
        
        Returns:
            Dictionary of {timeframe: DataFrame}
        """
        data = {}
        
        for tf in timeframes:
            df = self.fetch_ohlcv(symbol, tf, start_date, end_date)
            if not df.empty:
                data[tf] = df
        
        return data
    
    def clear_cache(self, symbol: Optional[str] = None):
        """Clear cached data"""
        if symbol:
            # Clear specific symbol
            symbol_clean = symbol.replace('/', '_')
            pattern = f"{symbol_clean}_*"
            
            import glob
            files = glob.glob(os.path.join(self.cache_dir, pattern))
            for file in files:
                os.remove(file)
                logger.info(f"🗑️  Removed cache: {file}")
        else:
            # Clear all cache
            import shutil
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir)
            logger.info("🗑️  Cleared all cache")
