#!/usr/bin/env python3
"""
Quick test script to verify your bot setup is working correctly
Run this before starting the bot to catch common issues
"""

import sys
import os

def test_python_version():
    """Check Python version"""
    print("🐍 Testing Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 9:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} - TOO OLD")
        print("   Please install Python 3.9 or higher")
        return False

def test_imports():
    """Test if critical packages can be imported"""
    print("\n📦 Testing package imports...")

    packages = {
        'flask': 'Flask',
        'dotenv': 'python-dotenv',
        'ccxt': 'ccxt',
        'pandas': 'pandas',
        'numpy': 'numpy',
    }

    all_ok = True
    for module, package_name in packages.items():
        try:
            __import__(module)
            print(f"   ✅ {package_name} - OK")
        except ImportError:
            print(f"   ❌ {package_name} - MISSING")
            print(f"      Install with: pip install {package_name}")
            all_ok = False

    return all_ok

def test_env_file():
    """Check if .env file exists and has required keys"""
    print("\n🔐 Testing .env configuration...")

    if not os.path.exists('.env'):
        print("   ❌ .env file NOT FOUND")
        print("      Create it from .env.example")
        return False

    print("   ✅ .env file exists")

    # Load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()

        required_keys = [
            'KRAKEN_API_KEY',
            'KRAKEN_API_SECRET',
        ]

        all_ok = True
        for key in required_keys:
            value = os.getenv(key)
            if value and len(value) > 10:
                print(f"   ✅ {key} - Set ({len(value)} chars)")
            else:
                print(f"   ❌ {key} - Missing or too short")
                all_ok = False

        # Check optional keys
        deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        if deepseek_key and len(deepseek_key) > 10:
            print(f"   ✅ DEEPSEEK_API_KEY - Set (AI enabled)")
        else:
            print(f"   ⚠️  DEEPSEEK_API_KEY - Not set (AI will run in demo mode)")

        return all_ok

    except Exception as e:
        print(f"   ❌ Error reading .env: {e}")
        return False

def test_files():
    """Check if critical files exist"""
    print("\n📁 Testing critical files...")

    files = [
        'run.py',
        'trading_engine.py',
        'ai_ensemble.py',
        'deepseek_validator.py',
        'requirements.txt',
    ]

    all_ok = True
    for file in files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} - MISSING")
            all_ok = False

    return all_ok

def test_kraken_connection():
    """Test connection to Kraken API"""
    print("\n🦑 Testing Kraken API connection...")

    try:
        import ccxt
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv('KRAKEN_API_KEY')
        api_secret = os.getenv('KRAKEN_API_SECRET')

        if not api_key or not api_secret:
            print("   ⚠️  API keys not configured - skipping connection test")
            return True

        # Create exchange instance
        exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True
        })

        # Test connection
        balance = exchange.fetch_balance()
        usd_balance = balance.get('USD', {}).get('free', 0)

        print(f"   ✅ Connected to Kraken successfully!")
        print(f"   💰 Available balance: ${usd_balance:.2f} USD")

        if usd_balance < 10:
            print(f"   ⚠️  Balance is low (${usd_balance:.2f})")
            print(f"      You may not be able to execute trades")

        return True

    except Exception as e:
        print(f"   ❌ Connection failed: {str(e)}")
        if 'Invalid key' in str(e) or 'EAPI:Invalid key' in str(e):
            print("      Your API keys appear to be invalid or expired")
            print("      Generate new keys at: https://www.kraken.com/u/security/api")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Kraken Trading Bot - Setup Test")
    print("=" * 60)

    results = {
        'Python Version': test_python_version(),
        'Package Imports': test_imports(),
        'Configuration File': test_env_file(),
        'Critical Files': test_files(),
        'Kraken Connection': test_kraken_connection(),
    }

    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Your bot is ready to run!")
        print("\n🚀 Start the bot with: python run.py")
        print("🌐 Dashboard will be at: http://localhost:5001")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("❌ Fix the issues above before starting the bot")
        print("\n📚 See WINDOWS_QUICKSTART.md for help")
        return 1

if __name__ == '__main__':
    sys.exit(main())
