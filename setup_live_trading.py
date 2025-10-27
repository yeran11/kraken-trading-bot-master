#!/usr/bin/env python3
"""
Interactive Setup Wizard for Live Trading
This script helps you configure the bot for live trading step by step.
"""
import os
import sys
import secrets
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_warning():
    """Print critical warning"""
    print("\n" + "⚠️ "*25)
    print("\n  WARNING: LIVE TRADING WITH REAL MONEY")
    print("\n  You can and WILL lose money with automated trading!")
    print("  Cryptocurrency markets are extremely volatile.")
    print("  Only proceed if you:")
    print("    - Understand the risks completely")
    print("    - Can afford to lose the money you're trading")
    print("    - Have tested in paper trading mode first")
    print("\n" + "⚠️ "*25 + "\n")

def confirm(question):
    """Ask for yes/no confirmation"""
    while True:
        response = input(f"{question} (yes/no): ").lower().strip()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        print("Please answer 'yes' or 'no'")

def get_input(prompt, default=None, required=True):
    """Get input from user"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    while True:
        value = input(prompt).strip()
        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print("This field is required. Please enter a value.")

def generate_secret():
    """Generate a secure random secret"""
    return secrets.token_hex(32)

def validate_api_key(key):
    """Basic validation of API key format"""
    if not key or len(key) < 20:
        return False
    if key == 'your_kraken_api_key_here' or key == 'your_kraken_api_secret_here':
        return False
    return True

def main():
    """Main setup wizard"""
    print_header("🦑 KRAKEN TRADING BOT - LIVE TRADING SETUP WIZARD")

    # Warning
    print_warning()

    if not confirm("Have you read and understood the LIVE_TRADING_SETUP.md guide?"):
        print("\n❌ Please read LIVE_TRADING_SETUP.md first before proceeding.")
        print("   It contains critical information about risks and setup.\n")
        sys.exit(1)

    if not confirm("Have you tested this bot in paper trading mode first?"):
        print("\n❌ You MUST test in paper trading mode first!")
        print("   Set PAPER_TRADING=True in .env and test for at least 1 week.\n")
        sys.exit(1)

    if not confirm("Do you understand you can lose all your money?"):
        print("\n❌ Setup cancelled. Consider testing more before going live.\n")
        sys.exit(1)

    print("\n✅ Proceeding with setup...\n")

    # Step 1: Kraken API Credentials
    print_header("STEP 1: Kraken API Credentials")

    print("To get your API keys:")
    print("1. Log into Kraken.com")
    print("2. Go to: Account → Security → API")
    print("3. Create a new API key with these permissions:")
    print("   ✅ Query Funds")
    print("   ✅ Query Open Orders & Trades")
    print("   ✅ Query Closed Orders & Trades")
    print("   ✅ Create & Modify Orders")
    print("   ✅ Cancel/Close Orders")
    print("   ❌ DO NOT enable withdraw funds!\n")

    if not confirm("Have you created your API key with the correct permissions?"):
        print("\n❌ Please create the API key first, then run this script again.\n")
        sys.exit(1)

    while True:
        api_key = get_input("Enter your Kraken API Key")
        if validate_api_key(api_key):
            break
        print("❌ API key appears invalid. Please check and try again.")

    while True:
        api_secret = get_input("Enter your Kraken Private Key (Secret)")
        if validate_api_key(api_secret):
            break
        print("❌ Private key appears invalid. Please check and try again.")

    print("✅ API credentials received\n")

    # Step 2: Risk Management
    print_header("STEP 2: Risk Management Settings")

    print("Configure your risk limits. START SMALL!")
    print("You can increase these later after gaining confidence.\n")

    max_order = get_input("Maximum order size in USD", "100")
    max_position = get_input("Maximum position size in USD", "500")
    max_exposure = get_input("Maximum total exposure in USD", "2000")
    max_daily_loss = get_input("Maximum daily loss in USD", "100")
    stop_loss = get_input("Stop loss percentage", "2.0")
    take_profit = get_input("Take profit percentage", "3.0")

    print("\n✅ Risk settings configured\n")

    # Step 3: Security
    print_header("STEP 3: Security Settings")

    print("Generating secure random secrets for your application...\n")
    secret_key = generate_secret()
    jwt_secret = generate_secret()
    print("✅ Secure secrets generated\n")

    # Step 4: Alerts (optional)
    print_header("STEP 4: Alert Configuration (Recommended)")

    enable_email = confirm("Do you want to enable email alerts?")
    email_config = {}
    if enable_email:
        email_config['smtp_server'] = get_input("SMTP server", "smtp.gmail.com")
        email_config['smtp_port'] = get_input("SMTP port", "587")
        email_config['smtp_user'] = get_input("SMTP username (email)")
        email_config['smtp_pass'] = get_input("SMTP password (app password for Gmail)")
        email_config['alert_to'] = get_input("Alert recipient email")
        print("✅ Email alerts configured\n")

    enable_telegram = confirm("Do you want to enable Telegram alerts?")
    telegram_config = {}
    if enable_telegram:
        print("\nTo get Telegram credentials:")
        print("1. Chat with @BotFather to create a bot and get the token")
        print("2. Chat with @userinfobot to get your chat ID\n")
        telegram_config['token'] = get_input("Telegram bot token")
        telegram_config['chat_id'] = get_input("Telegram chat ID")
        print("✅ Telegram alerts configured\n")

    # Step 5: Generate .env file
    print_header("STEP 5: Generating Configuration")

    env_content = f"""# Kraken Trading Bot - Live Trading Configuration
# Generated by setup wizard on {os.popen('date').read().strip()}
# WARNING: This file contains sensitive credentials - NEVER commit to git!

# ====================
# TRADING MODE - LIVE TRADING ENABLED
# ====================
PAPER_TRADING=False
ENVIRONMENT=production

# ====================
# KRAKEN API CREDENTIALS
# ====================
KRAKEN_API_KEY={api_key}
KRAKEN_API_SECRET={api_secret}

# ====================
# RISK MANAGEMENT
# ====================
MAX_ORDER_SIZE_USD={max_order}
MAX_POSITION_SIZE_USD={max_position}
MAX_TOTAL_EXPOSURE_USD={max_exposure}
MAX_DAILY_LOSS_USD={max_daily_loss}
STOP_LOSS_PERCENT={stop_loss}
TAKE_PROFIT_PERCENT={take_profit}
MAX_DRAWDOWN_PERCENT=15.0

# ====================
# SECURITY SETTINGS
# ====================
SECRET_KEY={secret_key}
JWT_SECRET_KEY={jwt_secret}

# ====================
# DATABASE
# ====================
DATABASE_URL=sqlite:///kraken_bot.db

# ====================
# ALERT SETTINGS
# ====================
"""

    if enable_email:
        env_content += f"""# Email Alerts
ENABLE_EMAIL_ALERTS=True
SMTP_SERVER={email_config['smtp_server']}
SMTP_PORT={email_config['smtp_port']}
SMTP_USERNAME={email_config['smtp_user']}
SMTP_PASSWORD={email_config['smtp_pass']}
ALERT_EMAIL_TO={email_config['alert_to']}
"""
    else:
        env_content += "ENABLE_EMAIL_ALERTS=False\n"

    if enable_telegram:
        env_content += f"""
# Telegram Alerts
ENABLE_TELEGRAM_ALERTS=True
TELEGRAM_BOT_TOKEN={telegram_config['token']}
TELEGRAM_CHAT_ID={telegram_config['chat_id']}
"""
    else:
        env_content += "\nENABLE_TELEGRAM_ALERTS=False\n"

    env_content += """
ENABLE_DISCORD_ALERTS=False

# ====================
# FEATURE FLAGS
# ====================
ENABLE_FUTURES_TRADING=False
ENABLE_MARGIN_TRADING=False
ENABLE_AUTO_REBALANCE=False
ENABLE_ARBITRAGE=False
ENABLE_MACHINE_LEARNING=False

# ====================
# LOGGING
# ====================
LOG_LEVEL=INFO
DEBUG_MODE=False

# ====================
# WEB SERVER
# ====================
PORT=5000
"""

    # Save .env file
    env_path = Path('.env')
    if env_path.exists():
        if not confirm("\n.env file already exists. Overwrite it?"):
            print("\n❌ Setup cancelled. Your existing .env was not modified.\n")
            sys.exit(1)

    with open('.env', 'w') as f:
        f.write(env_content)

    print("✅ .env file created successfully\n")

    # Final steps
    print_header("✅ SETUP COMPLETE!")

    print("Your bot is now configured for LIVE TRADING.\n")
    print("NEXT STEPS:\n")
    print("1. Test your API connection:")
    print("   python test_api_connection.py\n")
    print("2. If the test passes, you can start the bot:")
    print("   python main.py\n")
    print("3. When prompted, type: I_UNDERSTAND_LIVE_TRADING\n")
    print("4. Monitor the dashboard closely for the first few hours\n")
    print("5. Check your Kraken account regularly\n")

    print("⚠️  IMPORTANT REMINDERS:")
    print("   - Start with small amounts")
    print("   - Monitor closely for the first week")
    print("   - Enable alerts so you're notified of issues")
    print("   - Never trade more than you can afford to lose")
    print("   - Stop immediately if you see unexpected behavior\n")

    print("📖 For more information, read:")
    print("   - LIVE_TRADING_SETUP.md (detailed guide)")
    print("   - README.md (general documentation)\n")

    print("="*70)
    print("Good luck, and trade responsibly! 🦑")
    print("="*70 + "\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during setup: {e}\n")
        sys.exit(1)
