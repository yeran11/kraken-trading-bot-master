# Quick Start Guide for Live Trading

## ⚠️ Read This First

**This bot trades with REAL MONEY. You can LOSE everything. Only proceed if you:**
- Understand cryptocurrency trading
- Have tested in paper trading mode first (recommended 1+ week)
- Can afford to lose the money completely
- Accept full responsibility for any losses

## Option 1: Interactive Setup (Easiest)

Run the interactive setup wizard that guides you through every step:

```bash
python setup_live_trading.py
```

This will:
- Check you understand the risks
- Collect your Kraken API credentials
- Configure risk management settings
- Set up alerts (optional)
- Generate a secure .env configuration file

After the wizard completes, test your connection:

```bash
python test_api_connection.py
```

If all tests pass, start the bot:

```bash
python main.py
```

When prompted, type: `I_UNDERSTAND_LIVE_TRADING`

---

## Option 2: Manual Setup

### Step 1: Get Kraken API Keys

1. Log into https://www.kraken.com
2. Go to: **Account → Security → API**
3. Click **"Generate New Key"**
4. Set permissions:
   - ✅ Query Funds
   - ✅ Query Open Orders & Trades
   - ✅ Query Closed Orders & Trades
   - ✅ Create & Modify Orders
   - ✅ Cancel/Close Orders
   - ❌ **DO NOT enable Withdraw Funds**
5. Copy the API Key and Private Key (shown only once!)

### Step 2: Edit .env File

The `.env` file has been created in the project root. Edit it with your favorite text editor:

```bash
nano .env
# or
vim .env
# or use your IDE
```

**Required settings:**

```bash
# Set to False for live trading
PAPER_TRADING=False

# Add your actual Kraken credentials
KRAKEN_API_KEY=your_actual_key_here
KRAKEN_API_SECRET=your_actual_secret_here

# Generate secure secrets with:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=paste_generated_secret_here
JWT_SECRET_KEY=paste_another_generated_secret_here
```

**Risk settings (start small!):**

```bash
MAX_ORDER_SIZE_USD=100          # Max $100 per trade
MAX_POSITION_SIZE_USD=500       # Max $500 per position
MAX_TOTAL_EXPOSURE_USD=2000     # Max $2000 total
MAX_DAILY_LOSS_USD=100          # Stop if lose $100 in a day
STOP_LOSS_PERCENT=2.0           # 2% stop loss
TAKE_PROFIT_PERCENT=3.0         # 3% take profit
```

### Step 3: Test Connection

```bash
python test_api_connection.py
```

This verifies:
- Your API keys work
- You have the correct permissions
- Your account balance is accessible
- Risk settings are configured

**All tests must pass before proceeding!**

### Step 4: Start Trading

```bash
python main.py
```

When prompted, type: `I_UNDERSTAND_LIVE_TRADING`

The web dashboard will open at: http://localhost:5000

---

## What to Monitor

### First Hour
- ✅ Bot starts without errors
- ✅ Dashboard is accessible
- ✅ Strategies are running
- ✅ No error messages in logs

### First Day
- ✅ Trades are executing correctly
- ✅ Stop losses are being set
- ✅ Take profits are being set
- ✅ Position sizes are correct
- ✅ Daily loss tracking works
- ✅ Alerts are being sent (if enabled)

### First Week
- ✅ Overall performance is as expected
- ✅ No unusual behavior
- ✅ Risk limits are being respected
- ✅ Account balance on Kraken matches dashboard

---

## Emergency Stop

### Method 1: Dashboard
Click the **"EMERGENCY STOP"** button in the web dashboard

### Method 2: Terminal
Press `Ctrl+C` in the terminal running the bot

### Method 3: Kraken Website
1. Log into Kraken.com
2. Go to **Trade → Orders**
3. Click **"Cancel All Orders"**
4. Manually close positions if needed

### Method 4: Disable API Key
1. Log into Kraken.com
2. Go to **Account → Security → API**
3. Delete or disable the bot's API key

---

## Important Files

| File | Purpose |
|------|---------|
| `.env` | Your configuration (API keys, risk settings) |
| `LIVE_TRADING_SETUP.md` | Detailed setup guide |
| `test_api_connection.py` | Test your API credentials |
| `setup_live_trading.py` | Interactive setup wizard |
| `main.py` | Start the trading bot |
| `logs/kraken_bot.log` | Bot activity logs |

---

## Common Issues

### "API authentication failed"
- Check API key and secret are correct (no extra spaces)
- Verify key is active on Kraken
- Ensure you copied the full key

### "Permission denied"
- Check you enabled all required permissions
- Try creating a new API key with correct permissions

### "Invalid nonce"
- Your system clock is wrong
- Sync time: `sudo ntpdate -s time.nist.gov` (Linux)

### "Minimum order size not met"
- Kraken requires minimum $10 orders
- Increase your MAX_ORDER_SIZE_USD

### Bot won't start
- Check logs: `tail -f logs/kraken_bot.log`
- Run connection test: `python test_api_connection.py`
- Verify .env file has no syntax errors

---

## Safety Checklist

Before going live, verify:

- [ ] Tested in paper trading mode for 1+ week
- [ ] Read LIVE_TRADING_SETUP.md completely
- [ ] API keys created with correct permissions
- [ ] Withdraw permissions are DISABLED on API key
- [ ] .env file configured correctly
- [ ] Connection test passes
- [ ] Starting with small position sizes
- [ ] Alerts are configured and tested
- [ ] Monitoring plan is in place
- [ ] Emergency stop procedures are ready
- [ ] Understand I can lose all my money

---

## Getting Help

1. Check logs first: `tail -f logs/kraken_bot.log`
2. Run diagnostics: `python test_api_connection.py`
3. Check Kraken status: https://status.kraken.com/
4. Review LIVE_TRADING_SETUP.md for detailed info
5. Search GitHub issues for similar problems

---

## Risk Disclaimer

**You can and will lose money with automated trading.**

- Cryptocurrency markets are extremely volatile
- Past performance does NOT guarantee future results
- The authors are NOT responsible for any losses
- This is NOT financial advice
- Only trade what you can afford to lose completely

**By using this software, you accept full responsibility for all trading decisions and outcomes.**

---

## Quick Reference Commands

```bash
# Setup (interactive)
python setup_live_trading.py

# Test connection
python test_api_connection.py

# Start bot
python main.py

# View logs
tail -f logs/kraken_bot.log

# Stop bot
# Press Ctrl+C in terminal or use dashboard
```

---

**Remember: Start small, monitor closely, and never risk more than you can afford to lose!**

For detailed information, read **LIVE_TRADING_SETUP.md**.
