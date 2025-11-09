# 🚀 Windows Quick Start Guide

## The EASIEST Way to Run Your Bot (3 Simple Steps)

### Step 1: Download the Project
If you haven't already:
1. Go to: https://github.com/yeran11/kraken-trading-bot-master
2. Click the green "Code" button
3. Click "Download ZIP"
4. Extract the ZIP file to a folder (e.g., `C:\TradingBot`)

### Step 2: Run the Windows Installer
1. Open the folder where you extracted the files
2. **Double-click** `install_windows.bat`
3. Wait for it to install (5-10 minutes)
4. You'll see "Installation Complete!" when done

### Step 3: Start the Bot
1. **Double-click** `start_bot.bat` (the file I just created for you)
2. The bot will start automatically
3. Open your web browser and go to: **http://localhost:5001**

That's it! You're done! 🎉

---

## Alternative Method (Command Prompt)

If the batch files don't work, use Command Prompt:

### 1. Open Command Prompt
- Press `Windows Key + R`
- Type `cmd` and press Enter

### 2. Navigate to Your Bot Folder
```cmd
cd C:\TradingBot
```
(Replace `C:\TradingBot` with your actual folder path)

### 3. Run the Bot
```cmd
python run.py
```

### 4. Open Dashboard
Open your browser and go to: **http://localhost:5001**

---

## ✅ What You Should See

When the bot starts successfully:

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

## 🔧 If You Get Errors

### Error: "Python is not recognized"
**Fix:**
1. Install Python from https://www.python.org/downloads/
2. **IMPORTANT:** Check the box "Add Python to PATH" during installation
3. Restart Command Prompt after installing

### Error: "Module not found" or "No module named..."
**Fix:** Install dependencies
```cmd
pip install -r requirements.txt
```

### Error: "Port 5001 is already in use"
**Fix:** Something is already using that port
- Option 1: Stop the other program using that port
- Option 2: Change the port in `.env` file (change `PORT=5001` to `PORT=5002`)

### Error: "Cannot connect to Kraken"
**Fix:** Check your API keys
1. Open the `.env` file with Notepad
2. Verify your `KRAKEN_API_KEY` and `KRAKEN_API_SECRET` are correct
3. Get new keys from: https://www.kraken.com/u/security/api

---

## 🛑 How to Stop the Bot

In the Command Prompt window where the bot is running:
- Press `CTRL + C`
- Or just close the window

---

## 📊 Your Current Settings

Based on your `.env` file:
- **Trading Mode:** LIVE (Real Money) ⚠️
- **Max Order Size:** $10 per trade
- **Stop Loss:** 2%
- **Take Profit:** 3.3%
- **AI Enabled:** Yes (DeepSeek)
- **AI Min Confidence:** 50%
- **DeepSeek Weight:** 50% (Institutional Trader)

---

## ⚠️ IMPORTANT SAFETY NOTES

1. **You are in LIVE TRADING MODE**
   - Real trades will execute with real money
   - Make sure you understand the risks

2. **Start Small**
   - Your max order is $10, which is good for testing
   - Monitor the bot closely for the first few hours

3. **API Key Security**
   - Never share your `.env` file
   - Never commit `.env` to GitHub
   - Use a dedicated API key for the bot

4. **Monitor Regularly**
   - Check the dashboard at http://localhost:5001
   - Review positions and P&L frequently
   - The bot logs everything to `bot_output.log`

---

## 📞 Getting Help

If you're still having trouble:

1. **Check the log file:** `bot_output.log` in your bot folder
2. **Look at the error message** in Command Prompt
3. **Verify Python is installed:** Type `python --version` in cmd
4. **Check internet connection:** The bot needs internet to work
5. **Restart your computer** and try again

---

## 🎯 Quick Checklist

Before starting the bot, make sure:
- [ ] Python is installed (version 3.9+)
- [ ] Dependencies are installed (`pip install -r requirements.txt`)
- [ ] `.env` file exists with your API keys
- [ ] You understand you're in LIVE trading mode
- [ ] You have reviewed the risk settings

---

## 🚀 Next Steps After Starting

1. Open http://localhost:5001 in your browser
2. You should see the dashboard with:
   - Current balance
   - Active positions
   - Recent trades
   - Bot status
3. Monitor the dashboard regularly
4. The bot will automatically:
   - Scan for trading opportunities
   - Execute trades based on AI signals
   - Manage risk with stop-loss and take-profit
   - Log all activities

---

**Good luck with your trading! 📈💰**

Remember: Start small, monitor closely, and only risk what you can afford to lose!
