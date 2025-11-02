#!/usr/bin/env python3
"""
Auto-Start Script for Master Trader Bot
Starts both web dashboard and trading engine automatically
"""

import os
import sys
import time
from dotenv import load_dotenv

print("=" * 70)
print("🦑 KRAKEN MASTER TRADER - AUTO-START SCRIPT")
print("=" * 70)

# Load environment variables
load_dotenv()

# Check credentials
api_key = os.getenv('KRAKEN_API_KEY', '')
api_secret = os.getenv('KRAKEN_API_SECRET', '')
paper_trading = os.getenv('PAPER_TRADING', 'True').lower() in ('true', '1', 'yes')

if not api_key or not api_secret or 'YOUR_' in api_key.upper():
    print("❌ ERROR: API credentials not configured!")
    print("Please set KRAKEN_API_KEY and KRAKEN_API_SECRET in .env file")
    sys.exit(1)

print("✅ API credentials found")

# Show trading mode
if paper_trading:
    print("📊 Mode: PAPER TRADING (Safe)")
else:
    print("⚠️  Mode: LIVE TRADING (Real Money!)")

print("=" * 70)

# Import trading engine
try:
    from trading_engine import TradingEngine
    print("✅ Trading engine imported successfully")
except ImportError as e:
    print(f"❌ Failed to import trading engine: {e}")
    sys.exit(1)

# Initialize and start trading engine
try:
    print("\n🚀 Starting trading engine...")
    engine = TradingEngine(api_key, api_secret)
    engine.start()
    print("✅ Trading engine started successfully!")
    print("\n" + "=" * 70)
    print("🎯 MASTER TRADER IS NOW RUNNING")
    print("=" * 70)
    print("\n📊 Monitoring:")
    print("   - 3 trading pairs (PUMP, BTC, ETH)")
    print("   - AI ensemble validation (50% confidence threshold)")
    print("   - Momentum, Mean Reversion, Scalping strategies")
    print("   - Advanced reasoning modes available")
    print("\n📈 The bot will:")
    print("   ✓ Check for signals every 30 seconds")
    print("   ✓ Validate all trades with AI before execution")
    print("   ✓ Track performance in SQLite database")
    print("   ✓ Send Telegram alerts (if configured)")
    print("   ✓ Automatically optimize model weights every 100 trades")
    print("\n💡 Logs will appear below...")
    print("=" * 70)
    print()

    # Keep script running
    while True:
        time.sleep(60)

except KeyboardInterrupt:
    print("\n\n🛑 Stopping trading engine...")
    engine.stop()
    print("✅ Trading engine stopped")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
