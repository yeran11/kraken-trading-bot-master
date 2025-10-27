#!/usr/bin/env python3
"""
Quick status check for Kraken Trading Bot
"""
import os
import sys

print("\n" + "="*60)
print("🦑 KRAKEN TRADING BOT - STATUS CHECK")
print("="*60 + "\n")

# Check Python version
print(f"✅ Python {sys.version.split()[0]} installed")

# Check if main files exist
files_to_check = [
    'start_app.py',
    'templates/dashboard.html',
    'static/css/dashboard.css',
    'static/js/dashboard.js',
    'config.py',
    'requirements.txt'
]

all_good = True
for file in files_to_check:
    if os.path.exists(file):
        print(f"✅ {file} exists")
    else:
        print(f"❌ {file} missing")
        all_good = False

# Check environment
print(f"\n📊 Environment Settings:")
print(f"  - Paper Trading: {os.environ.get('PAPER_TRADING', 'True')}")
print(f"  - Port: {os.environ.get('PORT', '5000')}")
print(f"  - Environment: {os.environ.get('ENVIRONMENT', 'development')}")

print("\n" + "="*60)
if all_good:
    print("✅ SYSTEM READY!")
    print("\n📌 TO START THE BOT:")
    print("  1. Click the RUN button at the top")
    print("  2. Wait for 'System ready' message")
    print("  3. Open the Webview to see dashboard")
    print("\n⚠️ IMPORTANT:")
    print("  - Bot starts in PAPER TRADING mode (safe)")
    print("  - No real money will be used")
    print("  - Configure .env file for live trading")
else:
    print("⚠️ Some files are missing")
    print("Run: pip install -r requirements-minimal.txt")

print("="*60 + "\n")