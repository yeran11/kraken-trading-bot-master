# Master Trader Deployment Guide

This guide will walk you through deploying the upgraded Master Trader bot safely and effectively.

---

## Pre-Deployment Checklist

### ✅ 1. System Requirements
- [ ] Python 3.9+ installed
- [ ] 2GB+ RAM available
- [ ] 2GB+ disk space
- [ ] Stable internet connection
- [ ] Linux/macOS/Windows OS

### ✅ 2. API Keys Ready
- [ ] Kraken API key and secret
- [ ] DeepSeek API key
- [ ] API keys have correct permissions
- [ ] API keys tested and working

### ✅ 3. Knowledge Requirements
- [ ] Understand crypto trading basics
- [ ] Understand technical indicators (RSI, MACD, etc.)
- [ ] Understand risk management
- [ ] Understand position sizing
- [ ] Read all documentation

### ✅ 4. Risk Understanding
- [ ] Understand you can lose money
- [ ] Only trade with money you can afford to lose
- [ ] Start with minimal capital ($500-1000)
- [ ] Paper trade first (2-4 weeks minimum)

---

## Phase 1: Installation (5-10 minutes)

### Step 1: Clone Repository

```bash
git clone https://github.com/yeran11/kraken-trading-bot.git
cd kraken-trading-bot
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements-master.txt
```

**Expected output:**
```
Successfully installed ccxt-4.2.25 pandas-2.1.4 ... (20+ packages)
```

**Time:** 5-10 minutes depending on internet speed

### Step 4: Verify Installation

```bash
python3 -c "import ccxt, pandas, ta, flask; print('✅ Installation successful')"
```

---

## Phase 2: Configuration (10-15 minutes)

### Step 1: Create Environment File

```bash
cp .env.example .env
```

### Step 2: Edit Configuration

```bash
nano .env  # or use your favorite editor
```

### Step 3: Add API Keys

**Minimum required configuration:**

```env
# Kraken API
KRAKEN_API_KEY=your_kraken_api_key_here
KRAKEN_API_SECRET=your_kraken_secret_here

# DeepSeek API
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Trading Mode (ALWAYS start with false!)
LIVE_TRADING=false

# Risk Management
MAX_POSITION_SIZE_USD=2500
MAX_TOTAL_EXPOSURE_USD=10000
MAX_DAILY_LOSS_USD=500

# Logging
LOG_LEVEL=INFO
```

### Step 4: Get Kraken API Keys

1. Go to https://www.kraken.com/u/security/api
2. Click "Generate New Key"
3. Set description: "Trading Bot"
4. Enable permissions:
   - ✅ Query Funds
   - ✅ Query Open Orders & Trades
   - ✅ Query Closed Orders & Trades
   - ✅ Create & Modify Orders (for live trading only)
5. Click "Generate Key"
6. Copy API Key and Private Key to `.env`

### Step 5: Get DeepSeek API Key

1. Go to https://platform.deepseek.com
2. Sign up / Log in
3. Navigate to API Keys section
4. Click "Create new secret key"
5. Copy key to `.env`

### Step 6: Initialize Database

```bash
python3 init_db.py
```

**Expected output:**
```
✅ Database initialized successfully
✅ Tables created: trades, positions, performance_metrics
```

---

## Phase 3: Testing (2-4 weeks)

### Step 1: Run Backtests

```bash
python3 run_backtest.py
```

**What this does:**
- Fetches 90 days of BTC/USD historical data
- Tests all 5 advanced strategies
- Shows performance comparison
- Identifies best strategy

**Expected output:**
```
STRATEGY COMPARISON
============================================================
Strategy             Return       Win Rate  Trades   Sharpe
------------------------------------------------------------
Breakout             +22.67%      65.0%     40       1.85
Trend Following      +18.90%      70.2%     32       1.67
Support/Resistance   +12.34%      68.1%     44       1.23
...
============================================================
🏆 Best Strategy: Breakout (+22.67%)
```

**Action:** Review results, understand which strategies work best.

### Step 2: Start Paper Trading

```bash
python3 main.py
```

**What this does:**
- Starts bot in paper trading mode (no real money)
- Uses fake $10,000 balance
- Simulates real trades
- Tracks performance

**Expected output:**
```
🚀 Kraken Trading Bot - Master Trader Edition
✓ DeepSeek Master initialized
✓ Strategy Manager initialized with 10 strategies
✓ Risk Calculator initialized
✓ Performance Tracker initialized
📊 Paper Trading Mode: ACTIVE
🌐 Dashboard: http://localhost:5000
```

### Step 3: Monitor Dashboard

Open browser to: `http://localhost:5000`

**Dashboard shows:**
- Real-time P&L
- Open positions
- Recent trades
- Win rate by strategy
- Equity curve
- Drawdown chart

### Step 4: Paper Trade for 2-4 Weeks

**What to monitor:**
- Win rate (target: 60-70%)
- Profit factor (target: >1.5)
- Maximum drawdown (target: <15%)
- Strategy performance
- Risk management effectiveness

**Keep notes:**
- Which strategies perform best?
- What market conditions work best?
- Are stop losses appropriate?
- Is position sizing correct?

---

## Phase 4: Live Trading Preparation

### ⚠️ WARNING: Only proceed if paper trading was successful!

**Success criteria:**
- [ ] Paper traded for 2-4 weeks minimum
- [ ] Win rate >55%
- [ ] Profit factor >1.3
- [ ] Maximum drawdown <20%
- [ ] Understand all strategies
- [ ] Comfortable with risk management

### Step 1: Review Configuration

```bash
nano .env
```

**Check these settings:**
```env
# Start with SMALL amounts!
MAX_POSITION_SIZE_USD=100      # Start small!
MAX_TOTAL_EXPOSURE_USD=500     # Total at risk
MAX_DAILY_LOSS_USD=50          # Daily stop loss

# Conservative settings
LIVE_TRADING=false  # Keep false until ready
```

### Step 2: Fund Kraken Account

**Recommendations:**
- Start with $500-1000 (minimum)
- Only use money you can afford to lose
- Keep most funds in cold storage
- Only keep trading capital on exchange

### Step 3: Enable Live Trading

```bash
nano .env
```

**Change:**
```env
LIVE_TRADING=true
```

**Save and exit.**

### Step 4: Start Live Trading

```bash
python3 main.py
```

**You'll be prompted:**
```
⚠️  LIVE TRADING MODE DETECTED ⚠️
This bot will trade with REAL MONEY on your Kraken account.

Type 'I_UNDERSTAND_LIVE_TRADING' to continue:
```

**Type exactly:** `I_UNDERSTAND_LIVE_TRADING`

**Bot starts:**
```
🚀 Kraken Trading Bot - Master Trader Edition
🔴 LIVE TRADING MODE: ACTIVE
💰 Account Balance: $1,000.00
✓ All systems operational
```

---

## Phase 5: Live Trading Monitoring

### Daily Checklist

**Morning (before market opens):**
- [ ] Check overnight positions
- [ ] Review daily P&L
- [ ] Check for any errors in logs
- [ ] Verify bot is running
- [ ] Check exchange account balance

**During Trading:**
- [ ] Monitor dashboard every 2-4 hours
- [ ] Watch for unusual behavior
- [ ] Check stop losses are working
- [ ] Verify position sizes are correct

**Evening (after market closes):**
- [ ] Review daily performance
- [ ] Check win rate
- [ ] Review closed trades
- [ ] Update trading journal
- [ ] Plan for tomorrow

### Weekly Review

**Every Sunday:**
- [ ] Calculate weekly P&L
- [ ] Review strategy performance
- [ ] Identify best/worst strategies
- [ ] Adjust settings if needed
- [ ] Review risk management
- [ ] Check for any issues

### Monthly Review

**End of month:**
- [ ] Calculate monthly return
- [ ] Compare to targets
- [ ] Review all trades
- [ ] Analyze drawdowns
- [ ] Optimize strategies
- [ ] Adjust risk parameters

---

## Troubleshooting

### Bot Won't Start

**Problem:** `ModuleNotFoundError`

**Solution:**
```bash
source venv/bin/activate
pip install -r requirements-master.txt
```

### API Key Errors

**Problem:** `Invalid API key`

**Solution:**
- Check `.env` file
- Verify keys on Kraken website
- Ensure no extra spaces
- Regenerate keys if needed

### No Trades Executing

**Problem:** Bot running but no trades

**Possible causes:**
1. **DeepSeek confidence too low** - Check logs
2. **Risk limits reached** - Check daily loss limit
3. **No signals** - Market conditions not favorable
4. **API issues** - Check Kraken connection

**Solution:**
```bash
# Check logs
tail -f bot.log

# Check DeepSeek responses
grep "DeepSeek" bot.log

# Check risk limits
grep "risk" bot.log
```

### Unexpected Losses

**Problem:** Losing money quickly

**Immediate actions:**
1. **STOP THE BOT** - `Ctrl+C`
2. **Close all positions** - Manually on Kraken
3. **Review logs** - Find the issue
4. **Reduce position sizes** - Edit `.env`
5. **Return to paper trading** - Set `LIVE_TRADING=false`

**Analysis:**
- What went wrong?
- Were stop losses hit?
- Was position sizing too aggressive?
- Did a strategy fail?
- Was it a market event?

---

## Performance Optimization

### If Win Rate is Low (<50%)

**Actions:**
1. Increase DeepSeek confidence threshold
2. Disable underperforming strategies
3. Tighten stop losses
4. Reduce position sizes
5. Trade only during high liquidity hours

### If Drawdown is High (>15%)

**Actions:**
1. Reduce position sizes
2. Tighten stop losses
3. Enable daily loss limits
4. Reduce number of concurrent positions
5. Trade more conservatively

### If Profit Factor is Low (<1.3)

**Actions:**
1. Let winners run longer (wider take profits)
2. Cut losers faster (tighter stop losses)
3. Focus on high-confidence signals only
4. Disable low-performing strategies
5. Improve entry timing

---

## Safety Features

### Automatic Protections

**Daily Loss Limit:**
- Bot stops trading if daily loss exceeds limit
- Default: $500
- Adjust in `.env`: `MAX_DAILY_LOSS_USD`

**Maximum Drawdown:**
- Bot stops if drawdown exceeds 20%
- Protects capital from catastrophic losses

**Consecutive Loss Protection:**
- Bot stops after 5 consecutive losses
- Prevents emotional/algorithmic spirals

**Position Limits:**
- Maximum position size: $2,500 (default)
- Maximum total exposure: $10,000 (default)
- Prevents over-leveraging

### Manual Controls

**Emergency Stop:**
```bash
# Press Ctrl+C in terminal
# Or kill process:
ps aux | grep main.py
kill -9 <PID>
```

**Close All Positions:**
```bash
python3 close_all_positions.py
```

**Disable Live Trading:**
```bash
nano .env
# Change: LIVE_TRADING=false
# Restart bot
```

---

## Maintenance

### Daily

```bash
# Check logs
tail -f bot.log

# Check status
python3 check_status.py

# Backup database
cp trading_bot.db trading_bot.db.backup
```

### Weekly

```bash
# Update bot
git pull origin main

# Update dependencies
pip install -r requirements-master.txt --upgrade

# Clear old logs
find . -name "*.log" -mtime +7 -delete
```

### Monthly

```bash
# Full backup
tar -czf backup_$(date +%Y%m%d).tar.gz .

# Database maintenance
sqlite3 trading_bot.db "VACUUM;"

# Review and optimize
python3 run_backtest.py
```

---

## Scaling Up

### When to Increase Capital

**Criteria:**
- [ ] 3+ months of profitable trading
- [ ] Win rate consistently >60%
- [ ] Profit factor consistently >1.5
- [ ] Maximum drawdown <10%
- [ ] Understand all strategies
- [ ] Comfortable with risk

**How to scale:**
1. Increase slowly (10-20% per month)
2. Maintain same position size percentages
3. Keep risk per trade constant (2%)
4. Monitor performance closely
5. Scale back if performance degrades

---

## Support

**Documentation:**
- `INSTALL_MASTER.md` - Installation
- `MASTER_TRADER_UPGRADE_COMPLETE.md` - Upgrade summary
- `README.md` - Overview

**Logs:**
- `bot.log` - Main bot log
- `error.log` - Error log
- `trades.log` - Trade log

**Database:**
- `trading_bot.db` - SQLite database
- Use `sqlite3 trading_bot.db` to query

**Community:**
- GitHub Issues
- Discord (if available)
- Trading forums

---

## Final Checklist Before Live Trading

- [ ] Paper traded for 2-4 weeks minimum
- [ ] Win rate >55% in paper trading
- [ ] Profit factor >1.3 in paper trading
- [ ] Understand all strategies
- [ ] Understand risk management
- [ ] Read all documentation
- [ ] API keys configured correctly
- [ ] Database initialized
- [ ] Risk limits set appropriately
- [ ] Only trading with money you can afford to lose
- [ ] Have emergency stop plan
- [ ] Know how to close all positions
- [ ] Monitoring plan in place
- [ ] Trading journal ready

---

## Remember

1. **Start small** - $500-1000 maximum
2. **Paper trade first** - 2-4 weeks minimum
3. **Monitor constantly** - Especially first week
4. **Keep learning** - Market conditions change
5. **Manage risk** - Never risk more than 2% per trade
6. **Stay disciplined** - Follow your plan
7. **Don't panic** - Losses are part of trading
8. **Keep records** - Track everything
9. **Improve continuously** - Optimize based on data
10. **Know when to stop** - If it's not working, stop

---

**Good luck with your trading! 🚀📈💰**

**Trade safe, trade smart, trade profitably!**
