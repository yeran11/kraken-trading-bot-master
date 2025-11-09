# 🚀 How to Start Your Kraken Trading Bot

## Quick Start (Windows Command Prompt)

### 1. Open Command Prompt
- Press `Windows Key + R`
- Type `cmd` and press Enter

### 2. Navigate to Your Project Folder
```cmd
cd C:\path\to\kraken-trading-bot-master
```
(Replace with your actual folder path)

### 3. Install Dependencies (First Time Only)
```cmd
pip install -r requirements.txt
```

### 4. Start the Bot
```cmd
python run.py
```

### 5. Access the Dashboard
Open your web browser and go to:
```
http://localhost:5001
```

---

## Alternative: Using Python 3

If the above doesn't work, try:
```cmd
python3 run.py
```

---

## What You Should See

When the bot starts successfully, you'll see:
```
🦑 Kraken Trading Bot Starting...
============================================================
✅ Flask is installed
✅ Starting web server on port 5001
🌐 Dashboard will be available at http://0.0.0.0:5001
============================================================
⚠️  LIVE TRADING MODE ENABLED ⚠️
💰 REAL TRADES will be executed with REAL MONEY
🔑 API credentials detected and loaded
🚨 Monitor your positions closely!
============================================================
 * Running on http://127.0.0.1:5001
```

---

## 🔧 Troubleshooting

### Issue: "Python is not recognized"
**Solution:** Install Python from https://www.python.org/downloads/
- Make sure to check "Add Python to PATH" during installation

### Issue: "Module not found"
**Solution:** Install dependencies:
```cmd
pip install flask python-dotenv ccxt krakenex
```

### Issue: "Port already in use"
**Solution:** Change the port in `.env` file:
```
PORT=5002
```

### Issue: "Cannot connect to Kraken"
**Solution:** Check your API keys in `.env` file:
- Make sure `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` are correct
- Verify API permissions on Kraken.com

---

## 🛑 How to Stop the Bot

In the command prompt window, press:
```
CTRL + C
```

---

## 📊 Current Configuration

Your bot is currently set to:
- **Mode:** LIVE TRADING (Real Money)
- **Max Order Size:** $10 per trade
- **Stop Loss:** 2%
- **Take Profit:** 3.3%
- **AI Enabled:** Yes (DeepSeek with 50% weight)
- **Port:** 5001

---

## ⚠️ Important Notes

1. **Live Trading is Enabled** - Real trades will execute with real money
2. **Monitor Closely** - Check the dashboard frequently at http://localhost:5001
3. **API Keys** - Never share your `.env` file or commit it to GitHub
4. **Start Small** - Your max order size is $10, which is good for testing

---

## 🎯 Next Steps

1. Start the bot using the command above
2. Open http://localhost:5001 in your browser
3. Monitor the dashboard for trades
4. Check positions and P&L regularly
5. Adjust settings as needed through the Settings page

---

## 📞 Need Help?

If you encounter any issues:
1. Check the command prompt for error messages
2. Look at the `bot_output.log` file for detailed logs
3. Verify your `.env` file has correct API credentials
4. Make sure your internet connection is stable

---

**Happy Trading! 🚀📈**
