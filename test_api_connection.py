#!/usr/bin/env python3
"""
Test Kraken API Connection and Validate Credentials
Run this script before enabling live trading to ensure your API keys work correctly.
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Configure simple logging for this test
logger.remove()
logger.add(sys.stdout, format="<level>{level: <8}</level> | {message}", level="INFO")

load_dotenv()

def test_api_connection():
    """Test API connection and validate credentials"""

    print("\n" + "="*60)
    print("KRAKEN API CONNECTION TEST")
    print("="*60 + "\n")

    # Check if API keys are set
    api_key = os.getenv('KRAKEN_API_KEY', '')
    api_secret = os.getenv('KRAKEN_API_SECRET', '')
    paper_trading = os.getenv('PAPER_TRADING', 'True').lower() == 'true'

    if not api_key or not api_secret:
        logger.error("API keys not found in .env file")
        logger.info("Please edit .env and add your KRAKEN_API_KEY and KRAKEN_API_SECRET")
        return False

    if api_key == 'your_kraken_api_key_here' or api_secret == 'your_kraken_api_secret_here':
        logger.error("Please replace placeholder API keys with your actual Kraken API credentials")
        return False

    logger.info(f"Paper Trading Mode: {paper_trading}")
    logger.info(f"API Key Found: {api_key[:8]}...{api_key[-4:]}")
    logger.info("Testing API connection...\n")

    try:
        # Import Kraken client
        from kraken_client import KrakenClient

        # Initialize client
        kraken = KrakenClient()

        # Test 1: Get Server Time
        logger.info("Test 1: Checking server connectivity...")
        server_time = kraken.get_server_time()
        if server_time:
            logger.success("✓ Server connection successful")
        else:
            logger.error("✗ Server connection failed")
            return False

        # Test 2: Get Account Balance
        logger.info("\nTest 2: Checking API authentication...")
        balance = kraken.get_balance()
        if balance is not None:
            logger.success("✓ API authentication successful")

            # Display balance
            if balance:
                logger.info("\nAccount Balance:")
                for currency, amount in balance.items():
                    if float(amount) > 0:
                        logger.info(f"  {currency}: {amount}")
            else:
                logger.warning("  Account balance is empty or zero")
        else:
            logger.error("✗ API authentication failed")
            logger.error("Please check your API key and secret")
            return False

        # Test 3: Get Trading Pairs
        logger.info("\nTest 3: Checking market data access...")
        pairs = kraken.get_trading_pairs()
        if pairs:
            logger.success(f"✓ Market data access successful ({len(pairs)} pairs available)")
        else:
            logger.warning("✗ Could not fetch trading pairs")

        # Test 4: Check API Key Permissions
        logger.info("\nTest 4: Verifying API key permissions...")
        try:
            # Try to get open orders (requires permission)
            open_orders = kraken.get_open_orders()
            logger.success("✓ Query orders permission: OK")
        except Exception as e:
            logger.warning(f"⚠ Query orders permission may be missing: {str(e)}")

        # Success summary
        print("\n" + "="*60)
        logger.success("API CONNECTION TEST PASSED!")
        print("="*60)

        if paper_trading:
            logger.warning("\nNote: Paper trading is currently ENABLED")
            logger.info("To enable live trading:")
            logger.info("  1. Edit .env file")
            logger.info("  2. Set PAPER_TRADING=False")
            logger.info("  3. Review all risk management settings")
            logger.info("  4. Type 'I_UNDERSTAND_LIVE_TRADING' when starting the bot")
        else:
            logger.warning("\n⚠ WARNING: LIVE TRADING IS ENABLED ⚠")
            logger.warning("The bot will execute REAL trades with REAL money!")
            logger.warning("Make sure you understand the risks before proceeding.")

        print("\n")
        return True

    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        logger.info("Please install dependencies: pip install -r requirements.txt")
        return False

    except Exception as e:
        logger.error(f"Connection test failed: {str(e)}")
        logger.info("\nTroubleshooting:")
        logger.info("  1. Verify your API keys are correct")
        logger.info("  2. Check your Kraken account has API access enabled")
        logger.info("  3. Ensure your IP is not blocked (if IP whitelisting is enabled)")
        logger.info("  4. Check Kraken API status: https://status.kraken.com/")
        return False


def check_risk_settings():
    """Display current risk management settings"""
    print("\n" + "="*60)
    print("RISK MANAGEMENT SETTINGS")
    print("="*60)

    settings = {
        'MAX_ORDER_SIZE_USD': os.getenv('MAX_ORDER_SIZE_USD', '100'),
        'MAX_POSITION_SIZE_USD': os.getenv('MAX_POSITION_SIZE_USD', '500'),
        'MAX_TOTAL_EXPOSURE_USD': os.getenv('MAX_TOTAL_EXPOSURE_USD', '2000'),
        'MAX_DAILY_LOSS_USD': os.getenv('MAX_DAILY_LOSS_USD', '100'),
        'STOP_LOSS_PERCENT': os.getenv('STOP_LOSS_PERCENT', '2.0'),
        'TAKE_PROFIT_PERCENT': os.getenv('TAKE_PROFIT_PERCENT', '3.0'),
    }

    for key, value in settings.items():
        print(f"{key}: ${value}" if 'USD' in key else f"{key}: {value}%")

    print("\nThese limits will help protect your account from excessive losses.")
    print("You can adjust them in the .env file.")
    print("="*60 + "\n")


if __name__ == '__main__':
    # Display risk settings
    check_risk_settings()

    # Run connection test
    success = test_api_connection()

    if success:
        sys.exit(0)
    else:
        logger.error("Please fix the issues above before starting the bot")
        sys.exit(1)
