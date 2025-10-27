"""
Kraken Trading Bot Configuration
"""
import os
from datetime import timedelta
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# ====================
# ENVIRONMENT SETTINGS
# ====================
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
DEBUG_MODE = os.getenv('DEBUG_MODE', 'True').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ====================
# KRAKEN API SETTINGS
# ====================
KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY', '')
KRAKEN_API_SECRET = os.getenv('KRAKEN_API_SECRET', '')
KRAKEN_BASE_URL = 'https://api.kraken.com'
KRAKEN_WS_URL = 'wss://ws.kraken.com'
KRAKEN_FUTURES_URL = 'https://futures.kraken.com'

# ====================
# TRADING CONFIGURATION
# ====================
# SAFETY FIRST - Paper trading by default
PAPER_TRADING = os.getenv('PAPER_TRADING', 'True').lower() == 'true'
REQUIRE_CONFIRMATION = True  # Require confirmation for live trading

# Trading Pairs
TRADING_PAIRS = [
    'XBT/USD',  # Bitcoin
    'ETH/USD',  # Ethereum
    'SOL/USD',  # Solana
    'MATIC/USD',  # Polygon
    'LINK/USD',  # Chainlink
]

# Futures Pairs
FUTURES_PAIRS = [
    'PF_XBTUSD',  # Bitcoin perpetual
    'PF_ETHUSD',  # Ethereum perpetual
]

# Timeframes
DEFAULT_TIMEFRAME = '5m'
AVAILABLE_TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

# ====================
# RISK MANAGEMENT
# ====================
# Position Sizing
MIN_ORDER_SIZE_USD = 50.0  # Minimum order size in USD
MAX_ORDER_SIZE_USD = 1000.0  # Maximum single order size
MAX_POSITION_SIZE_USD = 2500.0  # Maximum position size per asset
MAX_TOTAL_EXPOSURE_USD = 10000.0  # Maximum total portfolio exposure

# Risk Limits
MAX_DAILY_LOSS_USD = 500.0  # Maximum daily loss
MAX_DRAWDOWN_PERCENT = 15.0  # Maximum drawdown percentage
STOP_LOSS_PERCENT = 2.0  # Default stop loss percentage
TAKE_PROFIT_PERCENT = 3.0  # Default take profit percentage

# Leverage (Futures)
MAX_LEVERAGE = 3  # Maximum leverage for futures
DEFAULT_LEVERAGE = 1  # Default leverage

# ====================
# STRATEGY SETTINGS
# ====================
ENABLED_STRATEGIES = [
    'momentum',
    'mean_reversion',
    'scalping',
    'grid',
    'arbitrage'
]

# Strategy Parameters
MOMENTUM_THRESHOLD = 0.02
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MACD_SIGNAL_THRESHOLD = 0.0001
VOLUME_SPIKE_MULTIPLIER = 2.0

# ====================
# DATABASE SETTINGS
# ====================
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///kraken_bot.db')
DB_POOL_SIZE = 10
DB_POOL_RECYCLE = 3600

# ====================
# WEB DASHBOARD
# ====================
FLASK_HOST = '0.0.0.0'
FLASK_PORT = int(os.getenv('PORT', 5000))
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

# WebSocket Settings
SOCKETIO_ASYNC_MODE = 'eventlet'
SOCKETIO_CORS_ALLOWED_ORIGINS = '*'

# ====================
# MONITORING & ALERTS
# ====================
# Email Alerts
ENABLE_EMAIL_ALERTS = os.getenv('ENABLE_EMAIL_ALERTS', 'False').lower() == 'true'
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
ALERT_EMAIL_TO = os.getenv('ALERT_EMAIL_TO', '')

# Telegram Alerts
ENABLE_TELEGRAM_ALERTS = os.getenv('ENABLE_TELEGRAM_ALERTS', 'False').lower() == 'true'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Discord Alerts
ENABLE_DISCORD_ALERTS = os.getenv('ENABLE_DISCORD_ALERTS', 'False').lower() == 'true'
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '')

# ====================
# PERFORMANCE SETTINGS
# ====================
# API Rate Limits
API_RATE_LIMIT = 10  # Requests per second
WS_RECONNECT_INTERVAL = 5  # Seconds
MAX_RECONNECT_ATTEMPTS = 10

# Cache Settings
CACHE_TTL = 60  # Cache time-to-live in seconds
PRICE_CACHE_TTL = 5  # Price cache TTL

# Update Intervals
PRICE_UPDATE_INTERVAL = 1  # Seconds
PORTFOLIO_UPDATE_INTERVAL = 5  # Seconds
STRATEGY_RUN_INTERVAL = 10  # Seconds
HEALTH_CHECK_INTERVAL = 30  # Seconds

# ====================
# LOGGING SETTINGS
# ====================
LOG_DIR = 'logs'
LOG_FILE = 'kraken_bot.log'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_ROTATION = '1 day'
LOG_RETENTION = '30 days'
LOG_COMPRESSION = 'zip'

# ====================
# BACKUP & RECOVERY
# ====================
ENABLE_BACKUP = True
BACKUP_INTERVAL = 3600  # Seconds (1 hour)
BACKUP_RETENTION_DAYS = 7
BACKUP_DIR = 'backups'

# ====================
# FEATURE FLAGS
# ====================
ENABLE_FUTURES_TRADING = os.getenv('ENABLE_FUTURES_TRADING', 'False').lower() == 'true'
ENABLE_MARGIN_TRADING = os.getenv('ENABLE_MARGIN_TRADING', 'False').lower() == 'true'
ENABLE_AUTO_REBALANCE = os.getenv('ENABLE_AUTO_REBALANCE', 'False').lower() == 'true'
ENABLE_ARBITRAGE = os.getenv('ENABLE_ARBITRAGE', 'False').lower() == 'true'
ENABLE_MACHINE_LEARNING = os.getenv('ENABLE_MACHINE_LEARNING', 'False').lower() == 'true'

# ====================
# SAFETY CHECKS
# ====================
def validate_config():
    """Validate configuration settings"""
    errors = []
    warnings = []

    # Live trading validation
    if not PAPER_TRADING:
        # Check API credentials
        if not KRAKEN_API_KEY or not KRAKEN_API_SECRET:
            errors.append("API keys required for live trading")
        elif KRAKEN_API_KEY == 'your_kraken_api_key_here' or KRAKEN_API_SECRET == 'your_kraken_api_secret_here':
            errors.append("Please replace placeholder API keys with real credentials")
        elif len(KRAKEN_API_KEY) < 20 or len(KRAKEN_API_SECRET) < 20:
            errors.append("API keys appear invalid (too short)")

        # Check security settings
        if SECRET_KEY == 'your-secret-key-change-in-production':
            errors.append("SECRET_KEY must be changed for live trading")
        if JWT_SECRET_KEY == 'jwt-secret-key-change-in-production':
            errors.append("JWT_SECRET_KEY must be changed for live trading")

        # Validate risk limits
        if MIN_ORDER_SIZE_USD < 10:
            errors.append("Minimum order size too low for live trading (min $10)")
        if MAX_ORDER_SIZE_USD < MIN_ORDER_SIZE_USD:
            errors.append("Max order size must be greater than min order size")
        if MAX_POSITION_SIZE_USD < MAX_ORDER_SIZE_USD:
            errors.append("Max position size must be greater than max order size")
        if MAX_TOTAL_EXPOSURE_USD < MAX_POSITION_SIZE_USD:
            errors.append("Total exposure must be greater than max position size")
        if MAX_TOTAL_EXPOSURE_USD > 50000:
            warnings.append("Maximum exposure is very high ($50k+) - ensure this is intentional")

        # Stop loss / take profit validation
        if STOP_LOSS_PERCENT <= 0 or STOP_LOSS_PERCENT > 50:
            errors.append("Stop loss percent must be between 0 and 50")
        if TAKE_PROFIT_PERCENT <= 0 or TAKE_PROFIT_PERCENT > 100:
            errors.append("Take profit percent must be between 0 and 100")
        if TAKE_PROFIT_PERCENT <= STOP_LOSS_PERCENT:
            warnings.append("Take profit is less than or equal to stop loss - check this is correct")

        # Daily loss limit
        if MAX_DAILY_LOSS_USD <= 0:
            errors.append("Max daily loss must be greater than 0")
        if MAX_DAILY_LOSS_USD > MAX_TOTAL_EXPOSURE_USD * 0.5:
            warnings.append("Daily loss limit is >50% of total exposure - very risky")

        # Environment check
        if ENVIRONMENT != 'production':
            warnings.append("ENVIRONMENT is not set to 'production' for live trading")

    # Futures trading validation
    if ENABLE_FUTURES_TRADING:
        if MAX_LEVERAGE > 10:
            errors.append("Leverage >10x is extremely dangerous - not recommended")
        elif MAX_LEVERAGE > 5:
            warnings.append("Leverage >5x is very risky - use with caution")
        if MAX_LEVERAGE < 1:
            errors.append("Leverage must be at least 1")

    # General validation
    if not TRADING_PAIRS:
        errors.append("At least one trading pair must be configured")

    # Print warnings
    if warnings:
        for warning in warnings:
            logging.warning(f"Config Warning: {warning}")

    # Print and raise errors
    if errors:
        for error in errors:
            logging.error(f"Config Error: {error}")
        raise ValueError("Configuration validation failed - see errors above")

    return True

# Run validation
if __name__ == '__main__':
    validate_config()
    print("Configuration validated successfully")