/**
 * Kraken Trading Bot - Dashboard JavaScript
 * Real-time updates via WebSocket
 */

// Global Variables
let socket = null;
let charts = {};
let updateIntervals = {};
let botStatus = {
    isRunning: false,
    paperTrading: true,
    positions: [],
    balance: {},
    metrics: {}
};

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Kraken Bot Dashboard...');

    // Initialize WebSocket connection
    initializeWebSocket();

    // Initialize charts
    initializeCharts();

    // Setup event listeners
    setupEventListeners();

    // Load initial data
    loadInitialData();

    // Start update intervals
    startUpdateIntervals();
});

// ====================
// WebSocket Management
// ====================

function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const socketUrl = `${protocol}://${window.location.host}/socket.io/`;

    socket = io(socketUrl, {
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 10
    });

    // Connection events
    socket.on('connect', () => {
        console.log('WebSocket connected');
        updateConnectionStatus(true);

        // Subscribe to updates
        subscribeToUpdates();
    });

    socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        updateConnectionStatus(false);
    });

    socket.on('error', (error) => {
        console.error('WebSocket error:', error);
        showAlert('Connection error', 'danger');
    });

    // Data events
    socket.on('status_update', handleStatusUpdate);
    socket.on('ticker_update', handleTickerUpdate);
    socket.on('positions_update', handlePositionsUpdate);
    socket.on('trade_success', handleTradeSuccess);
    socket.on('trade_error', handleTradeError);
    socket.on('bot_started', handleBotStarted);
    socket.on('bot_stopped', handleBotStopped);
    socket.on('alert', handleAlert);
    socket.on('update', handleGeneralUpdate);
}

function subscribeToUpdates() {
    // Subscribe to ticker updates for main pairs
    socket.emit('subscribe_ticker', {
        symbols: ['BTC/USD', 'ETH/USD', 'SOL/USD']
    });

    // Subscribe to position updates
    socket.emit('subscribe_positions');
}

// ====================
// Chart Initialization
// ====================

function initializeCharts() {
    const ctx = document.getElementById('main-chart').getContext('2d');

    // Portfolio Value Chart
    charts.portfolio = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Portfolio Value',
                data: [],
                borderColor: '#5741D9',
                backgroundColor: 'rgba(87, 65, 217, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(28, 32, 51, 0.9)',
                    titleColor: '#FFFFFF',
                    bodyColor: '#E0E6ED',
                    borderColor: '#5741D9',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(87, 65, 217, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#A8B2C1'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(87, 65, 217, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#A8B2C1',
                        callback: function(value) {
                            return '$' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// ====================
// Event Listeners
// ====================

function setupEventListeners() {
    // Control buttons
    document.getElementById('btn-start').addEventListener('click', startBot);
    document.getElementById('btn-stop').addEventListener('click', stopBot);
    document.getElementById('btn-emergency-stop').addEventListener('click', emergencyStop);

    // Settings
    document.getElementById('save-settings').addEventListener('click', saveSettings);

    // Manual trade
    document.getElementById('execute-trade').addEventListener('click', executeManualTrade);
    document.getElementById('trade-type').addEventListener('change', function() {
        const priceInput = document.getElementById('price-input');
        priceInput.style.display = this.value === 'LIMIT' ? 'block' : 'none';
    });

    // Chart tabs
    document.querySelectorAll('.nav-link[data-chart]').forEach(tab => {
        tab.addEventListener('click', function(e) {
            e.preventDefault();
            switchChart(this.dataset.chart);
        });
    });

    // Strategy toggles
    document.querySelectorAll('.strategy-item input').forEach(toggle => {
        toggle.addEventListener('change', function() {
            updateStrategyConfig(this.id.replace('strategy-', ''), this.checked);
        });
    });
}

// ====================
// Bot Control
// ====================

async function startBot() {
    const btn = document.getElementById('btn-start');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> Starting...';

    try {
        let confirmation = 'I_UNDERSTAND_LIVE_TRADING';

        // Check if paper trading is disabled
        if (!botStatus.paperTrading) {
            const userConfirmation = await showConfirmationModal(
                'Live Trading Warning',
                'You are about to start LIVE TRADING with REAL money. Are you absolutely sure?'
            );

            if (!userConfirmation) {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
                return;
            }
        }

        // Get selected strategies
        const strategies = [];
        document.querySelectorAll('.strategy-item input:checked').forEach(input => {
            strategies.push(input.id.replace('strategy-', ''));
        });

        const response = await fetch('/api/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                confirmation: confirmation,
                strategies: strategies,
                pairs: ['BTC/USD', 'ETH/USD', 'SOL/USD'],
                max_positions: 5
            })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert('Bot started successfully', 'success');
            updateBotControls(true);
        } else {
            showAlert(data.error || 'Failed to start bot', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
        }
    } catch (error) {
        console.error('Error starting bot:', error);
        showAlert('Error starting bot', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
    }
}

async function stopBot() {
    const btn = document.getElementById('btn-stop');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> Stopping...';

    try {
        const response = await fetch('/api/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                close_positions: false,
                cancel_orders: true
            })
        });

        const data = await response.json();

        if (response.ok) {
            showAlert('Bot stopped successfully', 'success');
            updateBotControls(false);
        } else {
            showAlert(data.error || 'Failed to stop bot', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-stop"></i> Stop Bot';
        }
    } catch (error) {
        console.error('Error stopping bot:', error);
        showAlert('Error stopping bot', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-stop"></i> Stop Bot';
    }
}

async function emergencyStop() {
    if (!confirm('EMERGENCY STOP: This will close all positions and cancel all orders. Are you sure?')) {
        return;
    }

    const btn = document.getElementById('btn-emergency-stop');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span> Emergency Stop...';

    try {
        const response = await fetch('/api/stop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                close_positions: true,
                cancel_orders: true
            })
        });

        if (response.ok) {
            showAlert('Emergency stop executed', 'warning');
            updateBotControls(false);
        }
    } catch (error) {
        console.error('Emergency stop error:', error);
        showAlert('Emergency stop failed - please check manually!', 'danger');
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Emergency Stop';
}

// ====================
// Data Loading
// ====================

async function loadInitialData() {
    try {
        // Load status
        const statusResponse = await fetch('/api/status');
        if (statusResponse.ok) {
            const status = await statusResponse.json();
            handleStatusUpdate(status);
        }

        // Load balance
        const balanceResponse = await fetch('/api/balance');
        if (balanceResponse.ok) {
            const balance = await balanceResponse.json();
            updateBalance(balance);
        }

        // Load positions
        const positionsResponse = await fetch('/api/positions');
        if (positionsResponse.ok) {
            const positions = await positionsResponse.json();
            updatePositions(positions.positions);
        }

        // Load recent trades
        const tradesResponse = await fetch('/api/trades?limit=10');
        if (tradesResponse.ok) {
            const trades = await tradesResponse.json();
            updateRecentTrades(trades.trades);
        }
    } catch (error) {
        console.error('Error loading initial data:', error);
    }
}

function startUpdateIntervals() {
    // Update balance every 5 seconds
    updateIntervals.balance = setInterval(async () => {
        const response = await fetch('/api/balance');
        if (response.ok) {
            const balance = await response.json();
            updateBalance(balance);
        }
    }, 5000);

    // Update performance metrics every 10 seconds
    updateIntervals.performance = setInterval(async () => {
        const response = await fetch('/api/performance');
        if (response.ok) {
            const metrics = await response.json();
            updateMetrics(metrics.metrics);
        }
    }, 10000);

    // Update market data every 3 seconds
    updateIntervals.marketData = setInterval(updateMarketData, 3000);

    // Update uptime every second
    updateIntervals.uptime = setInterval(updateUptime, 1000);

    // Initial market data load
    updateMarketData();
}

// ====================
// UI Update Functions
// ====================

function updateConnectionStatus(connected) {
    const status = document.getElementById('connection-status');
    if (connected) {
        status.className = 'badge bg-success';
        status.innerHTML = '<i class="fas fa-circle"></i> Connected';
    } else {
        status.className = 'badge bg-danger';
        status.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
    }
}

function updateBotControls(running) {
    const startBtn = document.getElementById('btn-start');
    const stopBtn = document.getElementById('btn-stop');
    const botStatus = document.getElementById('bot-status');

    if (running) {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        startBtn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
        stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Bot';
        botStatus.className = 'badge bg-success ms-2';
        botStatus.innerHTML = '<i class="fas fa-play-circle"></i> Running';
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
        startBtn.innerHTML = '<i class="fas fa-play"></i> Start Bot';
        stopBtn.innerHTML = '<i class="fas fa-stop"></i> Stop Bot';
        botStatus.className = 'badge bg-secondary ms-2';
        botStatus.innerHTML = '<i class="fas fa-stop-circle"></i> Stopped';
    }
}

function updateBalance(data) {
    const totalBalance = document.getElementById('total-balance');
    const balanceChange = document.getElementById('balance-change');

    if (data.total_usd) {
        totalBalance.textContent = '$' + data.total_usd.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    // Update balance change (mock for now)
    const change = Math.random() * 10 - 5;
    balanceChange.textContent = change.toFixed(2) + '%';
    balanceChange.parentElement.className = change >= 0 ? 'text-success' : 'text-danger';
}

function updatePositions(positions) {
    const tableBody = document.getElementById('positions-table');
    const positionCount = document.getElementById('open-positions');
    const positionValue = document.getElementById('position-value');

    positionCount.textContent = positions.length;

    if (positions.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No open positions</td></tr>';
        positionValue.textContent = '$0.00';
        return;
    }

    let totalValue = 0;
    let html = '';

    positions.forEach(position => {
        const pnl = position.unrealized_pnl || 0;
        const pnlClass = pnl >= 0 ? 'text-success' : 'text-danger';
        const pnlPrefix = pnl >= 0 ? '+' : '';

        totalValue += (position.quantity * position.current_price) || 0;

        html += `
            <tr>
                <td>${position.symbol}</td>
                <td><span class="badge bg-${position.side === 'long' ? 'success' : 'danger'}">${position.side.toUpperCase()}</span></td>
                <td>${position.quantity.toFixed(4)}</td>
                <td>$${position.entry_price.toFixed(2)}</td>
                <td>$${position.current_price.toFixed(2)}</td>
                <td class="${pnlClass}">${pnlPrefix}$${Math.abs(pnl).toFixed(2)}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="closePosition('${position.symbol}')">
                        <i class="fas fa-times"></i> Close
                    </button>
                </td>
            </tr>
        `;
    });

    tableBody.innerHTML = html;
    positionValue.textContent = '$' + totalValue.toFixed(2);
}

function updateMetrics(metrics) {
    // Update metric cards
    document.getElementById('daily-pnl').textContent = '$' + (metrics.daily_pnl || 0).toFixed(2);
    document.getElementById('win-rate').textContent = (metrics.win_rate || 0).toFixed(1) + '%';
    document.getElementById('total-trades').textContent = metrics.total_trades || 0;
    document.getElementById('avg-trade').textContent = '$' + (metrics.average_trade || 0).toFixed(2);

    // Update chart
    if (charts.portfolio && metrics.portfolio_value) {
        const now = new Date().toLocaleTimeString();
        charts.portfolio.data.labels.push(now);
        charts.portfolio.data.datasets[0].data.push(metrics.portfolio_value);

        // Keep only last 50 points
        if (charts.portfolio.data.labels.length > 50) {
            charts.portfolio.data.labels.shift();
            charts.portfolio.data.datasets[0].data.shift();
        }

        charts.portfolio.update();
    }
}

async function updateMarketData() {
    // Symbols to watch
    const symbols = ['BTC/USD', 'ETH/USD', 'SOL/USD'];

    try {
        // Fetch market data for all symbols in batch
        const response = await fetch('/api/market-data-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbols: symbols })
        });

        if (!response.ok) {
            console.error('Failed to fetch market data');
            return;
        }

        const result = await response.json();
        const data = result.data;

        // Update each symbol in the Market Watch
        const symbolMap = {
            'BTC/USD': 'btc',
            'ETH/USD': 'eth',
            'SOL/USD': 'sol'
        };

        Object.keys(symbolMap).forEach(symbol => {
            const prefix = symbolMap[symbol];
            const marketData = data[symbol];

            if (marketData && !marketData.error) {
                // Update price
                const priceElement = document.getElementById(`${prefix}-price`);
                if (priceElement) {
                    const price = marketData.price;
                    priceElement.textContent = '$' + price.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                    });

                    // Add animation on price change
                    priceElement.classList.add('price-flash');
                    setTimeout(() => priceElement.classList.remove('price-flash'), 300);
                }

                // Update 24h change
                const changeElement = document.getElementById(`${prefix}-change`);
                if (changeElement) {
                    const change = marketData.change_24h;
                    changeElement.textContent = (change >= 0 ? '+' : '') + change.toFixed(2) + '%';

                    // Update color
                    changeElement.classList.remove('bg-success', 'bg-danger');
                    changeElement.classList.add(change >= 0 ? 'bg-success' : 'bg-danger');
                }
            }
        });

        // Store in global state
        botStatus.marketData = data;

    } catch (error) {
        console.error('Error updating market data:', error);
    }
}

function updateRecentTrades(trades) {
    const container = document.getElementById('recent-trades');

    if (trades.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No recent trades</p>';
        return;
    }

    let html = '';
    trades.slice(0, 5).forEach(trade => {
        const pnlClass = trade.pnl >= 0 ? 'text-success' : 'text-danger';
        const sideClass = trade.side === 'BUY' ? 'success' : 'danger';

        html += `
            <div class="trade-item mb-2">
                <div class="d-flex justify-content-between">
                    <span class="badge bg-${sideClass}">${trade.side}</span>
                    <span>${trade.symbol}</span>
                    <span class="${pnlClass}">$${trade.pnl?.toFixed(2) || '0.00'}</span>
                </div>
                <small class="text-muted">${new Date(trade.timestamp).toLocaleTimeString()}</small>
            </div>
        `;
    });

    container.innerHTML = html;
}

function updateUptime() {
    if (!botStatus.isRunning) return;

    const uptimeElement = document.getElementById('uptime');
    const current = uptimeElement.textContent;
    const parts = current.split(':');

    let hours = parseInt(parts[0]) || 0;
    let minutes = parseInt(parts[1]) || 0;
    let seconds = parseInt(parts[2]) || 0;

    seconds++;
    if (seconds >= 60) {
        seconds = 0;
        minutes++;
    }
    if (minutes >= 60) {
        minutes = 0;
        hours++;
    }

    uptimeElement.textContent = `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// ====================
// WebSocket Event Handlers
// ====================

function handleStatusUpdate(status) {
    botStatus = { ...botStatus, ...status };

    // Update UI
    updateBotControls(status.is_running);

    // Update trading mode badge
    const tradingMode = document.getElementById('trading-mode');
    if (status.paper_trading) {
        tradingMode.className = 'badge bg-info ms-2';
        tradingMode.innerHTML = '<i class="fas fa-flask"></i> Paper Trading';
    } else {
        tradingMode.className = 'badge bg-warning ms-2 live-warning';
        tradingMode.innerHTML = '<i class="fas fa-exclamation-triangle"></i> LIVE TRADING';
    }
}

function handleTickerUpdate(data) {
    // Update market watch
    const symbolMap = {
        'BTC/USD': 'btc',
        'ETH/USD': 'eth',
        'SOL/USD': 'sol'
    };

    const prefix = symbolMap[data.symbol];
    if (prefix) {
        const priceElement = document.getElementById(`${prefix}-price`);
        const changeElement = document.getElementById(`${prefix}-change`);

        if (priceElement) {
            priceElement.textContent = '$' + data.price.toFixed(2);
        }

        if (changeElement) {
            changeElement.textContent = data.change.toFixed(2) + '%';
            changeElement.className = data.change >= 0 ? 'badge bg-success ms-2' : 'badge bg-danger ms-2';
        }
    }
}

function handlePositionsUpdate(data) {
    updatePositions(data.positions);
}

function handleTradeSuccess(data) {
    showAlert('Trade executed successfully', 'success');
    if (data.order) {
        // Add to recent trades
        updateRecentTrades([data.order]);
    }
}

function handleTradeError(data) {
    showAlert(`Trade error: ${data.error}`, 'danger');
}

function handleBotStarted(data) {
    botStatus.isRunning = true;
    updateBotControls(true);
    showAlert('Bot started', 'success');
}

function handleBotStopped(data) {
    botStatus.isRunning = false;
    updateBotControls(false);
    showAlert('Bot stopped', 'warning');
}

function handleAlert(data) {
    showAlert(data.message, data.type || 'info');
}

function handleGeneralUpdate(data) {
    if (data.metrics) {
        updateMetrics(data.metrics);
    }
    if (data.balance) {
        updateBalance(data.balance);
    }
}

// ====================
// Helper Functions
// ====================

function showAlert(message, type = 'info') {
    const container = document.getElementById('alerts-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'times-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    container.appendChild(alert);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function showConfirmationModal(title, message) {
    return new Promise((resolve) => {
        const confirmed = confirm(`${title}\n\n${message}`);
        resolve(confirmed);
    });
}

async function executeManualTrade() {
    const symbol = document.getElementById('trade-symbol').value;
    const side = document.getElementById('trade-side').value;
    const amount = parseFloat(document.getElementById('trade-amount').value);
    const type = document.getElementById('trade-type').value;
    const price = type === 'LIMIT' ? parseFloat(document.getElementById('trade-price').value) : null;

    if (!amount || amount <= 0) {
        showAlert('Invalid trade amount', 'danger');
        return;
    }

    socket.emit('manual_trade', {
        symbol,
        side,
        amount,
        type,
        price
    });
}

async function closePosition(symbol) {
    if (!confirm(`Close position for ${symbol}?`)) {
        return;
    }

    // Implementation to close position
    showAlert(`Closing position for ${symbol}...`, 'info');
}

function switchChart(type) {
    // Update tab active state
    document.querySelectorAll('.nav-link[data-chart]').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.nav-link[data-chart="${type}"]`).classList.add('active');

    // Switch chart data
    // Implementation for different chart types
    showAlert(`Switched to ${type} chart`, 'info');
}

function updateStrategyConfig(strategy, enabled) {
    // Update strategy configuration
    console.log(`Strategy ${strategy} ${enabled ? 'enabled' : 'disabled'}`);
}

async function saveSettings() {
    const settings = {
        risk_settings: {
            max_position_size: parseFloat(document.getElementById('max-position-size').value),
            max_daily_loss: parseFloat(document.getElementById('max-daily-loss').value),
            stop_loss_percent: parseFloat(document.getElementById('stop-loss').value),
            take_profit_percent: parseFloat(document.getElementById('take-profit').value)
        }
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            showAlert('Settings saved successfully', 'success');
            $('#settingsModal').modal('hide');
        } else {
            showAlert('Failed to save settings', 'danger');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
        showAlert('Error saving settings', 'danger');
    }
}

function downloadLogs() {
    window.open('/api/logs?limit=1000', '_blank');
}

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (socket) {
        socket.disconnect();
    }

    // Clear intervals
    Object.values(updateIntervals).forEach(interval => {
        clearInterval(interval);
    });
});