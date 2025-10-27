#!/usr/bin/env python3
"""
Simple script to add your Kraken API credentials to the .env file
"""
import os
import sys

def main():
    print("\n" + "="*70)
    print("  KRAKEN API CREDENTIALS SETUP")
    print("="*70 + "\n")

    print("This script will help you add your Kraken API credentials.\n")
    print("To get your API keys:")
    print("  1. Go to https://www.kraken.com/u/security/api")
    print("  2. Click 'Generate New Key'")
    print("  3. Enable these permissions:")
    print("     ✅ Query Funds")
    print("     ✅ Query Open Orders & Trades")
    print("     ✅ Query Closed Orders & Trades")
    print("     ✅ Create & Modify Orders")
    print("     ✅ Cancel/Close Orders")
    print("     ❌ DO NOT enable Withdraw Funds")
    print("\n" + "="*70 + "\n")

    # Get API Key
    api_key = input("Paste your Kraken API Key here: ").strip()
    if not api_key or len(api_key) < 20:
        print("\n❌ Invalid API key. Please try again.")
        sys.exit(1)

    # Get Private Key
    private_key = input("Paste your Kraken Private Key (Secret) here: ").strip()
    if not private_key or len(private_key) < 20:
        print("\n❌ Invalid Private Key. Please try again.")
        sys.exit(1)

    print("\n✅ API credentials received!")
    print("\nUpdating .env file...")

    # Read the current .env file
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()

        # Update the API key lines
        updated_lines = []
        for line in lines:
            if line.startswith('KRAKEN_API_KEY='):
                updated_lines.append(f'KRAKEN_API_KEY={api_key}\n')
            elif line.startswith('KRAKEN_API_SECRET='):
                updated_lines.append(f'KRAKEN_API_SECRET={private_key}\n')
            else:
                updated_lines.append(line)

        # Write back to .env
        with open('.env', 'w') as f:
            f.writelines(updated_lines)

        print("✅ .env file updated successfully!\n")

        # Show current configuration
        print("="*70)
        print("  YOUR CONFIGURATION")
        print("="*70)
        print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
        print(f"Private Key: {private_key[:8]}...{private_key[-4:]}")
        print(f"Paper Trading: False (LIVE TRADING ENABLED)")
        print("="*70 + "\n")

        print("⚠️  NEXT STEPS:")
        print("  1. Test your API connection:")
        print("     python test_api_connection.py")
        print("\n  2. If the test passes, start the bot:")
        print("     python main.py")
        print("\n  3. When prompted, type: I_UNDERSTAND_LIVE_TRADING")
        print("\n" + "="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Error updating .env file: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)
