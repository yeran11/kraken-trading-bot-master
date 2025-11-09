# Kraken Trading Bot - Master Trader Edition
# Windows PowerShell Installation Script

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Kraken Trading Bot - Master Trader Edition" -ForegroundColor Cyan
Write-Host "Windows Installation Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Step 1: Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Step 2: Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

Write-Host "Step 3: Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

Write-Host "Step 4: Installing dependencies..." -ForegroundColor Yellow
Write-Host "This may take 5-10 minutes..." -ForegroundColor Yellow
Write-Host ""

# Try to install from requirements-master.txt first
pip install -r requirements-master.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "WARNING: Standard installation failed" -ForegroundColor Yellow
    Write-Host "Trying simplified installation..." -ForegroundColor Yellow
    Write-Host ""
    
    # Install core packages one by one
    Write-Host "Installing core packages..." -ForegroundColor Cyan
    pip install ccxt pandas numpy
    pip install ta
    pip install flask flask-socketio flask-cors
    pip install sqlalchemy
    pip install loguru python-dotenv
    pip install requests aiohttp
    pip install plotly matplotlib
    pip install scipy
    pip install python-dateutil pytz
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Copy .env.example to .env" -ForegroundColor White
Write-Host "2. Add your API keys to .env" -ForegroundColor White
Write-Host "3. Run: python main.py" -ForegroundColor White
Write-Host ""
Write-Host "For detailed instructions, see INSTALL_MASTER.md" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit"
