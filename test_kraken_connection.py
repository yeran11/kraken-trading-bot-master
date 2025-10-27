#!/usr/bin/env python3
"""
Test Kraken API Connection
Run this to verify your API credentials are working
"""

import os
from dotenv import load_dotenv

print("=" * 60)
print("🦑 Kraken API Connection Test")
print("=" * 60)

# Load .env file
load_dotenv()

# Check if .env file exists
if os.path.exists('.env'):
    print("✅ .env file found")
else:
    print("❌ .env file NOT found!")
    print("   Please create a .env file in the project root")
    exit(1)

# Read credentials
api_key = os.getenv('KRAKEN_API_KEY', '')
api_secret = os.getenv('KRAKEN_API_SECRET', '')
paper_trading = os.getenv('PAPER_TRADING', 'True')

print(f"\n📋 Configuration:")
print(f"   PAPER_TRADING: {paper_trading}")

# Check API key format
if not api_key or 'your_' in api_key.lower():
    print(f"❌ API Key: Not set or invalid")
    print(f"   Current value: {api_key[:20]}..." if api_key else "   (empty)")
else:
    print(f"✅ API Key: Set ({len(api_key)} characters)")
    print(f"   Starts with: {api_key[:10]}...")

# Check API secret format
if not api_secret or 'your_' in api_secret.lower():
    print(f"❌ API Secret: Not set or invalid")
    print(f"   Current value: {api_secret[:20]}..." if api_secret else "   (empty)")
else:
    print(f"✅ API Secret: Set ({len(api_secret)} characters)")
    print(f"   Starts with: {api_secret[:10]}...")

# Try to connect to Kraken
if api_key and api_secret and 'your_' not in api_key.lower():
    print("\n🔌 Testing connection to Kraken...")
    try:
        import ccxt
        exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })
        
        print("   Fetching account balance...")
        balance = exchange.fetch_balance()
        
        print("\n✅ CONNECTION SUCCESSFUL!")
        print("\n💰 Your Kraken Balance:")
        
        # Show balances
        for currency in ['USD', 'EUR', 'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT']:
            if currency in balance['free'] and balance['free'][currency] > 0:
                print(f"   {currency}: {balance['free'][currency]}")
        
        # Calculate total USD
        total_usd = balance['free'].get('USD', 0)
        print(f"\n   Total USD: ${total_usd:.2f}")
        
    except Exception as e:
        print(f"\n❌ CONNECTION FAILED!")
        print(f"   Error: {str(e)}")
        print("\n   Possible issues:")
        print("   1. API key or secret is incorrect")
        print("   2. API permissions not set correctly on Kraken")
        print("   3. IP whitelist restrictions (if enabled)")
        print("   4. ccxt library not installed (run: pip install ccxt)")
else:
    print("\n⚠️  Cannot test connection - API credentials not properly set")
    print("\n📝 To fix this:")
    print("   1. Edit your .env file")
    print("   2. Replace 'your_kraken_api_key_here' with your real API key")
    print("   3. Replace 'your_kraken_api_secret_here' with your real API secret")
    print("   4. Set PAPER_TRADING=False for live trading")

print("\n" + "=" * 60)
