# Installation Guide - Master Trader Edition

This guide will help you install and set up the Kraken Trading Bot Master Trader edition.

## System Requirements

- **Python:** 3.9 or higher
- **RAM:** 2GB minimum, 4GB recommended
- **Disk Space:** 2GB (down from 10GB+ in original version)
- **OS:** Linux, macOS, or Windows

---

## Quick Install (5 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/yeran11/kraken-trading-bot.git
cd kraken-trading-bot
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

**Master Trader (Optimized):**
```bash
pip install -r requirements-master.txt
```

**Original Version (if you prefer):**
```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your API keys
```

**Required API Keys:**
- `KRAKEN_API_KEY` - Your Kraken API key
- `KRAKEN_API_SECRET` - Your Kraken API secret
- `DEEPSEEK_API_KEY` - Your DeepSeek API key

**Optional Settings:**
- `LIVE_TRADING=false` - Start in paper trading mode (recommended)
- `LOG_LEVEL=INFO` - Logging verbosity

### 5. Initialize Database

```bash
python3 init_db.py
```

### 6. Run Bot

**Paper Trading (Safe):**
```bash
python3 main.py
```

**Live Trading (Risky):**
```bash
# Edit .env and set LIVE_TRADING=true
# Then confirm by typing the safety phrase
python3 main.py
```

---

## Detailed Installation

### Prerequisites

#### Install Python 3.9+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install python@3.9
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/)

#### Install Git

**Ubuntu/Debian:**
```bash
sudo apt install git
```

**macOS:**
```bash
brew install git
```

**Windows:**
Download from [git-scm.com](https://git-scm.com/)

---

### Step-by-Step Setup

#### 1. Clone and Navigate

```bash
git clone https://github.com/yeran11/kraken-trading-bot.git
cd kraken-trading-bot
```

#### 2. Create Virtual Environment

```bash
python3 -m venv venv
```

Activate it:
- **Linux/macOS:** `source venv/bin/activate`
- **Windows:** `venv\Scripts\activate`

You should see `(venv)` in your terminal prompt.

#### 3. Upgrade pip

```bash
pip install --upgrade pip
```

#### 4. Install Dependencies

**For Master Trader (Recommended):**
```bash
pip install -r requirements-master.txt
```

This will install:
- Core trading libraries (~200MB)
- Technical analysis tools (~50MB)
- Web dashboard (~100MB)
- Database and utilities (~150MB)

**Total:** ~500MB (vs 5GB+ in original)

**Installation time:** 5-10 minutes depending on internet speed

#### 5. Verify Installation

```bash
python3 -c "import ccxt, pandas, ta, flask; print('✅ All dependencies installed')"
```

---

### Configuration

#### 1. Create Environment File

```bash
cp .env.example .env
```

#### 2. Edit Configuration

```bash
nano .env  # or use your favorite editor
```

**Minimum Required:**
```env
# Kraken API (get from kraken.com/u/security/api)
KRAKEN_API_KEY=your_kraken_api_key_here
KRAKEN_API_SECRET=your_kraken_secret_here

# DeepSeek API (get from platform.deepseek.com)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Trading Mode
LIVE_TRADING=false  # ALWAYS start with false!

# Risk Management
MAX_POSITION_SIZE_USD=2500
MAX_TOTAL_EXPOSURE_USD=10000
MAX_DAILY_LOSS_USD=500

# Logging
LOG_LEVEL=INFO
```

#### 3. Get API Keys

**Kraken API:**
1. Go to [kraken.com/u/security/api](https://www.kraken.com/u/security/api)
2. Create new API key
3. Enable permissions:
   - Query Funds
   - Query Open Orders & Trades
   - Query Closed Orders & Trades
   - Create & Modify Orders (for live trading)
4. Copy key and secret to `.env`

**DeepSeek API:**
1. Go to [platform.deepseek.com](https://platform.deepseek.com)
2. Sign up / log in
3. Navigate to API Keys
4. Create new API key
5. Copy to `.env`

---

### Database Setup

#### Initialize Database

```bash
python3 init_db.py
```

This creates:
- SQLite database (`trading_bot.db`)
- Tables for trades, positions, performance
- Initial configuration

#### Verify Database

```bash
sqlite3 trading_bot.db "SELECT name FROM sqlite_master WHERE type='table';"
```

You should see tables like:
- `trades`
- `positions`
- `performance_metrics`
- `strategy_performance`

---

## Running the Bot

### Paper Trading (Recommended First)

```bash
python3 main.py
```

This will:
- Start in paper trading mode (no real money)
- Simulate trades with fake balance
- Track performance
- Test strategies safely

**Access Dashboard:**
Open browser to `http://localhost:5000`

### Live Trading (After Testing)

**⚠️ WARNING: Live trading risks real money!**

1. **Test thoroughly in paper mode first** (2-4 weeks minimum)
2. **Start with minimal capital** ($500-1000)
3. **Monitor constantly** for first week

**Enable live trading:**
```bash
# Edit .env
nano .env

# Change to:
LIVE_TRADING=true

# Save and exit
```

**Run with confirmation:**
```bash
python3 main.py
```

You'll be prompted to type: `I_UNDERSTAND_LIVE_TRADING`

---

## Running Backtests

### Quick Backtest

```bash
python3 run_backtest.py
```

This tests 5 strategies on 90 days of BTC/USD data.

### Custom Backtest

```python
from backtesting.backtest_engine import BacktestEngine, BacktestConfig
from backtesting.data_manager import DataManager
from strategies_advanced import BreakoutStrategy

# Fetch data
data_manager = DataManager()
df = data_manager.fetch_ohlcv('BTC/USD', '1h', days_back=180)

# Configure
config = BacktestConfig(initial_balance=10000.0)

# Run
engine = BacktestEngine(config)
strategy = BreakoutStrategy()
results = engine.run_backtest(df, strategy, 'BTC/USD')

# Print
engine.print_results(results)
```

---

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'ccxt'`

**Solution:**
```bash
source venv/bin/activate  # Activate venv first!
pip install -r requirements-master.txt
```

### API Key Errors

**Problem:** `Invalid API key`

**Solution:**
- Check `.env` file has correct keys
- Verify keys on exchange website
- Ensure no extra spaces in `.env`

### Database Errors

**Problem:** `sqlite3.OperationalError: no such table`

**Solution:**
```bash
rm trading_bot.db  # Delete old database
python3 init_db.py  # Recreate
```

### Port Already in Use

**Problem:** `Address already in use: 5000`

**Solution:**
```bash
# Find process using port 5000
lsof -i :5000

# Kill it
kill -9 <PID>

# Or use different port
export FLASK_PORT=5001
python3 main.py
```

---

## Updating

### Pull Latest Changes

```bash
git pull origin main
```

### Update Dependencies

```bash
pip install -r requirements-master.txt --upgrade
```

### Migrate Database

```bash
alembic upgrade head
```

---

## Uninstall

```bash
# Deactivate virtual environment
deactivate

# Remove directory
cd ..
rm -rf kraken-trading-bot
```

---

## Next Steps

1. ✅ Read `MASTER_TRADER_README.md` for features
2. ✅ Read `STRATEGY_GUIDE.md` for strategy details
3. ✅ Run backtests on historical data
4. ✅ Paper trade for 2-4 weeks
5. ✅ Start live with minimal capital
6. ✅ Monitor and adjust

---

## Support

- **Documentation:** See `docs/` folder
- **Issues:** GitHub Issues
- **Community:** Discord (link in README)

**Happy Trading! 🚀**
