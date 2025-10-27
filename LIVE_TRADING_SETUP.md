# Live Trading Setup Guide

## ⚠️ CRITICAL WARNING

**THIS BOT WILL EXECUTE REAL TRADES WITH REAL MONEY!**

- You can and WILL lose money
- Cryptocurrency markets are extremely volatile
- Past performance does NOT guarantee future results
- NEVER risk more than you can afford to lose
- The authors are NOT responsible for any losses

## Prerequisites

Before setting up live trading, ensure you:

1. ✅ Understand cryptocurrency trading and technical analysis
2. ✅ Have experience with trading bots (preferably tested in paper trading first)
3. ✅ Understand the risks of automated trading
4. ✅ Have funds you can afford to lose
5. ✅ Have a verified Kraken account

## Step 1: Create Kraken API Keys

### 1.1 Log into Kraken
Go to https://www.kraken.com and log into your account

### 1.2 Navigate to API Settings
Go to: Account → Security → API

### 1.3 Create New API Key
Click "Generate New Key" and configure:

**Key Description:** `Trading Bot - [Date]` (for easy identification)

**Required Permissions:**
- ✅ Query Funds
- ✅ Query Open Orders & Trades
- ✅ Query Closed Orders & Trades
- ✅ Create & Modify Orders
- ✅ Cancel/Close Orders

**IMPORTANT - DO NOT ENABLE:**
- ❌ Withdraw Funds (NEVER enable this)
- ❌ Deposit Funds
- ❌ Export Data (not needed)

### 1.4 Security Settings (Recommended)
- Enable "Nonce Window" for additional security
- Add IP whitelist if you have a static IP
- Set a custom rate limit (optional)

### 1.5 Save Your Credentials
After creating the key, you'll see:
- **API Key** (public key)
- **Private Key** (secret - shown only once!)

⚠️ **IMPORTANT**: Copy both keys immediately! The Private Key is shown only once.

**Store them securely:**
- Use a password manager
- Never share them with anyone
- Never commit them to git
- Never post them online

## Step 2: Configure the Bot

### 2.1 Edit the .env File

Open the `.env` file in the project root and configure:

```bash
# Set to False for LIVE trading
PAPER_TRADING=False
ENVIRONMENT=production

# Add your Kraken credentials
KRAKEN_API_KEY=your_actual_api_key_here
KRAKEN_API_SECRET=your_actual_private_key_here

# Generate secure secrets (run this command):
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_generated_secret_here
JWT_SECRET_KEY=your_generated_jwt_secret_here
```

### 2.2 Configure Risk Management

**START SMALL!** Use conservative limits when starting:

```bash
# Recommended starting values:
MAX_ORDER_SIZE_USD=100          # Max $100 per order
MAX_POSITION_SIZE_USD=500       # Max $500 per position
MAX_TOTAL_EXPOSURE_USD=2000     # Max $2000 total
MAX_DAILY_LOSS_USD=100          # Stop after $100 daily loss
STOP_LOSS_PERCENT=2.0           # 2% stop loss
TAKE_PROFIT_PERCENT=3.0         # 3% take profit
```

**You can adjust these later** after gaining confidence, but NEVER skip starting with small amounts.

### 2.3 Enable Alerts (Highly Recommended)

Configure at least one alert method to monitor your bot:

**Email Alerts:**
```bash
ENABLE_EMAIL_ALERTS=True
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # Use app-specific password for Gmail
ALERT_EMAIL_TO=your_email@gmail.com
```

**Telegram Alerts** (easier to set up):
```bash
ENABLE_TELEGRAM_ALERTS=True
TELEGRAM_BOT_TOKEN=your_bot_token  # Get from @BotFather
TELEGRAM_CHAT_ID=your_chat_id      # Get from @userinfobot
```

## Step 3: Test API Connection

**Before starting live trading**, verify your API credentials work:

```bash
python test_api_connection.py
```

This script will:
- ✅ Test connection to Kraken servers
- ✅ Verify API authentication
- ✅ Display your account balance
- ✅ Check API permissions
- ✅ Show your risk settings

**All tests must PASS** before proceeding!

### Common Issues:

**Error: "API authentication failed"**
- Check your API key and secret are correct
- Ensure no extra spaces when copying keys
- Verify the API key is active on Kraken

**Error: "Permission denied"**
- Check you enabled all required permissions
- Verify the API key hasn't expired

**Error: "Invalid nonce"**
- Your system clock may be wrong
- Sync your system time: `sudo ntpdate -s time.nist.gov`

## Step 4: Start Small and Test

### 4.1 Initial Test Run

For your first live run:

1. **Reduce risk limits even further:**
   ```bash
   MAX_ORDER_SIZE_USD=50
   MAX_TOTAL_EXPOSURE_USD=500
   MAX_DAILY_LOSS_USD=50
   ```

2. **Enable only ONE simple strategy:**
   Edit `config.py` and set:
   ```python
   ENABLED_STRATEGIES = ['mean_reversion']  # Start with one strategy
   ```

3. **Start the bot:**
   ```bash
   python main.py
   ```

4. **When prompted, type:**
   ```
   I_UNDERSTAND_LIVE_TRADING
   ```

### 4.2 Monitor Closely

For the first few hours:
- ✅ Watch the dashboard constantly
- ✅ Monitor for any errors in logs
- ✅ Verify trades are executing correctly
- ✅ Check your Kraken account trade history
- ✅ Keep your phone nearby for alerts

### 4.3 First Day Checklist

- [ ] Bot started successfully
- [ ] Dashboard is accessible
- [ ] Alerts are working
- [ ] First trade executed correctly
- [ ] Stop loss is being set
- [ ] Daily loss limit is being tracked
- [ ] No errors in logs

## Step 5: Scaling Up (If Successful)

**Only after 1-2 weeks of successful operation**, you can:

1. Gradually increase position sizes by 20-30%
2. Enable additional strategies one at a time
3. Add more trading pairs
4. Adjust risk parameters based on performance

**NEVER:**
- ❌ Increase limits by more than 50% at once
- ❌ Remove stop losses
- ❌ Disable risk management
- ❌ Enable all strategies at once without testing
- ❌ Turn off monitoring/alerts

## Safety Features Built Into the Bot

The bot includes multiple safety layers:

1. **Confirmation Required**: Must type `I_UNDERSTAND_LIVE_TRADING` to start
2. **Position Size Limits**: Enforced maximum per trade and per position
3. **Daily Loss Limits**: Bot stops if daily loss exceeds limit
4. **Drawdown Protection**: Pauses trading if portfolio drops too much
5. **Stop Loss/Take Profit**: Every position has risk management
6. **Order Validation**: All orders checked before execution
7. **API Rate Limiting**: Prevents API abuse and bans
8. **Error Recovery**: Automatic retry with exponential backoff

## Emergency Procedures

### Stop Trading Immediately

**Option 1: Stop Button**
- Click "EMERGENCY STOP" in the dashboard
- This closes all positions immediately

**Option 2: Ctrl+C**
- Press Ctrl+C in the terminal
- Bot will stop gracefully

**Option 3: Kill Process**
```bash
pkill -f main.py
```

### Cancel All Orders on Kraken

If the bot becomes unresponsive:
1. Log into Kraken.com
2. Go to Trade → Orders
3. Click "Cancel All Orders"

### Disable API Key

In case of emergency:
1. Log into Kraken.com
2. Go to Account → Security → API
3. Delete or disable the bot's API key

## Monitoring and Maintenance

### Daily Tasks
- [ ] Check dashboard for errors
- [ ] Review trade history
- [ ] Verify account balance on Kraken
- [ ] Check alert notifications
- [ ] Review logs for warnings

### Weekly Tasks
- [ ] Analyze performance metrics
- [ ] Review strategy performance
- [ ] Adjust risk limits if needed
- [ ] Backup database
- [ ] Update dependencies if needed

### Monthly Tasks
- [ ] Rotate API keys for security
- [ ] Review and optimize strategies
- [ ] Analyze market conditions
- [ ] Adjust for new market regimes

## Performance Expectations

**Be realistic about returns:**

- Most profitable trading bots make 1-5% per month (not per day!)
- Many months will be break-even or small losses
- Consistency is more important than big wins
- Expect drawdowns of 10-20% even with good strategies

**Red flags to stop immediately:**
- 🚩 Daily losses exceeding 5%
- 🚩 Consistent losses for 1+ week
- 🚩 Unusual API errors
- 🚩 Unexpected trades executing
- 🚩 Bot behavior different than paper trading

## Security Best Practices

1. **Never share your API keys**
2. **Use strong, unique passwords**
3. **Enable 2FA on Kraken**
4. **Keep bot software updated**
5. **Use a secure server/computer**
6. **Monitor account activity**
7. **Regular security audits**
8. **Rotate keys every 3 months**

## Getting Help

**Before asking for help:**
1. Check logs: `tail -f logs/kraken_bot.log`
2. Verify API connection: `python test_api_connection.py`
3. Check Kraken status: https://status.kraken.com/
4. Review this guide again

**If you need support:**
- Check GitHub issues for similar problems
- Provide error logs (remove API keys!)
- Describe what you tried already
- Include your configuration (remove secrets!)

## Legal Disclaimer

This software is provided "as is" without warranty of any kind. The authors and contributors:
- Are NOT responsible for any financial losses
- Do NOT guarantee profitability
- Do NOT provide financial advice
- Do NOT offer technical support for live trading

**You use this software entirely at your own risk.**

Cryptocurrency trading is highly risky and not suitable for everyone. Only trade with money you can afford to lose completely.

---

## Final Checklist Before Going Live

- [ ] I have read and understood this entire guide
- [ ] I have tested in paper trading mode for at least 1 week
- [ ] I understand I can lose all my money
- [ ] I have created Kraken API keys with correct permissions
- [ ] I have configured the .env file correctly
- [ ] I have tested the API connection successfully
- [ ] I have enabled alerts and verified they work
- [ ] I am starting with small position sizes
- [ ] I will monitor the bot closely for the first week
- [ ] I have emergency stop procedures ready
- [ ] I understand this is NOT a get-rich-quick scheme
- [ ] I am prepared to stop if performance is poor

**If you checked all boxes above, you may proceed with live trading.**

**If you have ANY doubts, test more in paper trading mode first!**

---

*Remember: The best traders are patient, disciplined, and risk-averse. Start small, learn continuously, and never risk more than you can afford to lose.*
