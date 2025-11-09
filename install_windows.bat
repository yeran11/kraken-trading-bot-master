@echo off
echo ============================================================
echo Kraken Trading Bot - Master Trader Edition
echo Windows Installation Script
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Step 1: Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo Step 2: Activating virtual environment...
call venv\Scripts\activate.bat

echo Step 3: Upgrading pip...
python -m pip install --upgrade pip

echo Step 4: Installing dependencies...
echo This may take 5-10 minutes...
echo.

REM Try to install from requirements-master.txt first
pip install -r requirements-master.txt
if errorlevel 1 (
    echo.
    echo WARNING: Standard installation failed
    echo Trying simplified installation...
    echo.
    
    REM Install core packages one by one
    pip install ccxt pandas numpy
    pip install ta
    pip install flask flask-socketio flask-cors
    pip install sqlalchemy
    pip install loguru python-dotenv
    pip install requests aiohttp
    pip install plotly matplotlib
    pip install scipy
    pip install python-dateutil pytz
)

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Copy .env.example to .env
echo 2. Add your API keys to .env
echo 3. Run: python main.py
echo.
echo For detailed instructions, see INSTALL_MASTER.md
echo.
pause
