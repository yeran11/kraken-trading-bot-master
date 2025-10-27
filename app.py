"""
Kraken Trading Bot - Web Dashboard
"""
import os
import json
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, session
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from loguru import logger
import pandas as pd

import config
from kraken_client import KrakenClient
from bot_manager import BotManager
from database import db, Trade, BotStatus, PerformanceMetrics
from risk_manager import RiskManager
from strategies import StrategyManager
from alerts import AlertManager

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app, origins=config.SOCKETIO_CORS_ALLOWED_ORIGINS)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize database
db.init_app(app)

# Initialize components
kraken_client = KrakenClient()
risk_manager = RiskManager(kraken_client)
strategy_manager = StrategyManager(kraken_client, risk_manager)
alert_manager = AlertManager()
bot_manager = BotManager(kraken_client, strategy_manager, risk_manager, alert_manager)

# Global state
bot_state = {
    'is_running': False,
    'start_time': None,
    'total_trades': 0,
    'profitable_trades': 0,
    'total_pnl': 0.0,
    'current_drawdown': 0.0,
    'active_positions': 0
}

# ====================
# ROUTES - Dashboard
# ====================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/settings')
def settings_page():
    """Settings page"""
    return render_template('settings.html',
                         paper_trading=config.PAPER_TRADING,
                         max_order_size=config.MAX_ORDER_SIZE_USD,
                         max_position_size=config.MAX_POSITION_SIZE_USD,
                         max_exposure=config.MAX_TOTAL_EXPOSURE_USD,
                         max_daily_loss=config.MAX_DAILY_LOSS_USD,
                         stop_loss=config.STOP_LOSS_PERCENT,
                         take_profit=config.TAKE_PROFIT_PERCENT,
                         email_alerts=config.ENABLE_EMAIL_ALERTS,
                         telegram_alerts=config.ENABLE_TELEGRAM_ALERTS,
                         discord_alerts=config.ENABLE_DISCORD_ALERTS)

@app.route('/api/status')
def get_status():
    """Get bot status"""
    try:
        # Get current bot status
        status = {
            'is_running': bot_manager.is_running,
            'paper_trading': config.PAPER_TRADING,
            'start_time': bot_state['start_time'],
            'uptime': _calculate_uptime(),
            'environment': config.ENVIRONMENT
        }

        # Add performance metrics
        if bot_manager.is_running:
            metrics = bot_manager.get_performance_metrics()
            status.update(metrics)

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the trading bot"""
    try:
        # Get parameters
        data = request.get_json() or {}

        # Safety check for live trading
        if not config.PAPER_TRADING:
            confirmation = data.get('confirmation', '')
            if confirmation != 'I_UNDERSTAND_LIVE_TRADING':
                return jsonify({
                    'error': 'Live trading requires confirmation',
                    'message': 'Please confirm you understand the risks'
                }), 400

        # Check if already running
        if bot_manager.is_running:
            return jsonify({'error': 'Bot is already running'}), 400

        # Configure strategies
        strategies = data.get('strategies', config.ENABLED_STRATEGIES)
        pairs = data.get('pairs', config.TRADING_PAIRS)

        # Start the bot
        success = bot_manager.start(
            strategies=strategies,
            trading_pairs=pairs,
            max_positions=data.get('max_positions', 5)
        )

        if success:
            bot_state['is_running'] = True
            bot_state['start_time'] = datetime.now().isoformat()

            # Emit status update
            socketio.emit('bot_started', {
                'timestamp': datetime.now().isoformat(),
                'strategies': strategies,
                'pairs': pairs
            })

            # Send alert
            alert_manager.send_alert(
                'Bot Started',
                f'Trading bot started with {len(strategies)} strategies on {len(pairs)} pairs',
                'info'
            )

            return jsonify({
                'success': True,
                'message': 'Bot started successfully',
                'strategies': strategies,
                'pairs': pairs
            })
        else:
            return jsonify({'error': 'Failed to start bot'}), 500

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot"""
    try:
        # Check if running
        if not bot_manager.is_running:
            return jsonify({'error': 'Bot is not running'}), 400

        # Get parameters
        data = request.get_json() or {}
        close_positions = data.get('close_positions', False)
        cancel_orders = data.get('cancel_orders', True)

        # Stop the bot
        success = bot_manager.stop(
            close_positions=close_positions,
            cancel_orders=cancel_orders
        )

        if success:
            bot_state['is_running'] = False

            # Emit status update
            socketio.emit('bot_stopped', {
                'timestamp': datetime.now().isoformat(),
                'runtime': _calculate_uptime()
            })

            # Send alert
            alert_manager.send_alert(
                'Bot Stopped',
                f'Trading bot stopped after {_calculate_uptime()}',
                'warning'
            )

            return jsonify({
                'success': True,
                'message': 'Bot stopped successfully'
            })
        else:
            return jsonify({'error': 'Failed to stop bot'}), 500

    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/balance')
def get_balance():
    """Get account balance"""
    try:
        balance = kraken_client.get_balance()

        # Calculate total value in USD
        total_usd = 0
        for currency, details in balance.items():
            if currency == 'USD':
                total_usd += details.get('total', details)
            else:
                # Get conversion rate
                try:
                    ticker = kraken_client.get_ticker(f"{currency}/USD")
                    rate = ticker['last']
                    total_usd += details.get('total', details) * rate
                except:
                    pass

        return jsonify({
            'balances': balance,
            'total_usd': total_usd,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting balance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions')
def get_positions():
    """Get open positions"""
    try:
        positions = bot_manager.get_positions()

        # Add current P&L
        for position in positions:
            current_price = kraken_client.get_ticker(position['symbol'])['last']
            if position['side'] == 'long':
                position['unrealized_pnl'] = (current_price - position['entry_price']) * position['quantity']
            else:
                position['unrealized_pnl'] = (position['entry_price'] - current_price) * position['quantity']
            position['current_price'] = current_price

        return jsonify({
            'positions': positions,
            'count': len(positions),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders')
def get_orders():
    """Get open orders"""
    try:
        orders = kraken_client.get_open_orders()

        return jsonify({
            'orders': orders,
            'count': len(orders),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trades')
def get_trades():
    """Get trade history"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)

        # Get trades from database
        trades = Trade.query.order_by(Trade.timestamp.desc()).limit(limit).offset(offset).all()

        trade_list = [
            {
                'id': trade.id,
                'symbol': trade.symbol,
                'side': trade.side,
                'price': trade.price,
                'quantity': trade.quantity,
                'pnl': trade.pnl,
                'strategy': trade.strategy,
                'timestamp': trade.timestamp.isoformat()
            }
            for trade in trades
        ]

        # Calculate statistics
        total_trades = len(trade_list)
        profitable_trades = sum(1 for t in trade_list if t['pnl'] and t['pnl'] > 0)
        total_pnl = sum(t['pnl'] for t in trade_list if t['pnl'])

        return jsonify({
            'trades': trade_list,
            'statistics': {
                'total_trades': total_trades,
                'profitable_trades': profitable_trades,
                'win_rate': (profitable_trades / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting trades: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance')
def get_performance():
    """Get performance metrics"""
    try:
        # Get metrics from bot manager
        metrics = bot_manager.get_performance_metrics()

        # Add additional calculations
        if metrics['total_trades'] > 0:
            metrics['average_trade'] = metrics['total_pnl'] / metrics['total_trades']
            metrics['profit_factor'] = abs(metrics.get('total_profit', 0) / metrics.get('total_loss', 1))

        return jsonify({
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting performance: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/<symbol>')
def get_market_data(symbol):
    """Get market data for a symbol"""
    try:
        # Get ticker
        ticker = kraken_client.get_ticker(symbol)

        # Get OHLCV
        timeframe = request.args.get('timeframe', '5m')
        limit = request.args.get('limit', 100, type=int)
        ohlcv = kraken_client.get_ohlcv(symbol, timeframe, limit)

        # Get orderbook
        orderbook = kraken_client.get_orderbook(symbol, depth=20)

        return jsonify({
            'ticker': ticker,
            'ohlcv': ohlcv.to_dict(),
            'orderbook': orderbook,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Get or update settings"""
    try:
        if request.method == 'GET':
            # Return current settings
            settings = {
                'paper_trading': config.PAPER_TRADING,
                'enabled_strategies': config.ENABLED_STRATEGIES,
                'trading_pairs': config.TRADING_PAIRS,
                'risk_settings': {
                    'max_position_size': config.MAX_POSITION_SIZE_USD,
                    'max_total_exposure': config.MAX_TOTAL_EXPOSURE_USD,
                    'stop_loss_percent': config.STOP_LOSS_PERCENT,
                    'take_profit_percent': config.TAKE_PROFIT_PERCENT,
                    'max_daily_loss': config.MAX_DAILY_LOSS_USD
                },
                'alerts': {
                    'email_enabled': config.ENABLE_EMAIL_ALERTS,
                    'telegram_enabled': config.ENABLE_TELEGRAM_ALERTS,
                    'discord_enabled': config.ENABLE_DISCORD_ALERTS
                }
            }
            return jsonify(settings)

        else:  # POST
            data = request.get_json()

            # Update settings (be careful with live trading changes)
            if 'risk_settings' in data:
                for key, value in data['risk_settings'].items():
                    if hasattr(config, key.upper()):
                        setattr(config, key.upper(), value)

            # Update risk manager
            risk_manager.update_limits()

            return jsonify({
                'success': True,
                'message': 'Settings updated successfully'
            })

    except Exception as e:
        logger.error(f"Error handling settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """Get recent logs"""
    try:
        limit = request.args.get('limit', 100, type=int)
        level = request.args.get('level', 'INFO')

        # Read log file
        log_file = os.path.join(config.LOG_DIR, config.LOG_FILE)
        logs = []

        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()[-limit:]
                for line in lines:
                    if level in line or level == 'ALL':
                        logs.append(line.strip())

        return jsonify({
            'logs': logs,
            'count': len(logs)
        })

    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/credentials', methods=['POST'])
def update_credentials():
    """Update API credentials in .env file"""
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()

        if not api_key or not api_secret:
            return jsonify({'error': 'API key and secret are required'}), 400

        # Check if bot is running
        if bot_manager.is_running:
            return jsonify({'error': 'Stop the bot before updating credentials'}), 400

        # Update .env file
        env_file = '.env'
        if not os.path.exists(env_file):
            return jsonify({'error': '.env file not found'}), 500

        # Read current .env content
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Update API key and secret lines
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('KRAKEN_API_KEY='):
                lines[i] = f'KRAKEN_API_KEY={api_key}\n'
                updated = True
            elif line.startswith('KRAKEN_API_SECRET='):
                lines[i] = f'KRAKEN_API_SECRET={api_secret}\n'
                updated = True

        if not updated:
            return jsonify({'error': 'Could not find API key fields in .env'}), 500

        # Write updated content
        with open(env_file, 'w') as f:
            f.writelines(lines)

        logger.info("API credentials updated successfully")

        return jsonify({
            'success': True,
            'message': 'API credentials saved. Please restart the bot.'
        })

    except Exception as e:
        logger.error(f"Error updating credentials: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-connection')
def test_connection():
    """Test API connection"""
    try:
        # Reload config to get latest credentials
        import importlib
        importlib.reload(config)

        # Create a new client instance
        test_client = KrakenClient()

        # Try to get balance (requires valid credentials)
        balance = test_client.get_balance()

        return jsonify({
            'success': True,
            'message': 'Connection successful',
            'balance': balance
        })

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/risk-settings', methods=['POST'])
def update_risk_settings():
    """Update risk management settings"""
    try:
        data = request.get_json()

        # Update .env file
        env_file = '.env'
        if not os.path.exists(env_file):
            return jsonify({'error': '.env file not found'}), 500

        # Read current .env content
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Update settings
        settings_map = {
            'max_order_size': 'MAX_ORDER_SIZE_USD',
            'max_position_size': 'MAX_POSITION_SIZE_USD',
            'max_exposure': 'MAX_TOTAL_EXPOSURE_USD',
            'max_daily_loss': 'MAX_DAILY_LOSS_USD',
            'stop_loss': 'STOP_LOSS_PERCENT',
            'take_profit': 'TAKE_PROFIT_PERCENT'
        }

        for key, env_var in settings_map.items():
            if key in data:
                value = data[key]
                for i, line in enumerate(lines):
                    if line.startswith(f'{env_var}='):
                        lines[i] = f'{env_var}={value}\n'
                        break

        # Write updated content
        with open(env_file, 'w') as f:
            f.writelines(lines)

        # Reload config
        import importlib
        importlib.reload(config)

        # Update risk manager
        risk_manager.update_limits()

        logger.info("Risk settings updated successfully")

        return jsonify({
            'success': True,
            'message': 'Risk settings updated successfully'
        })

    except Exception as e:
        logger.error(f"Error updating risk settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading-mode', methods=['POST'])
def update_trading_mode():
    """Update trading mode (paper/live)"""
    try:
        data = request.get_json()
        paper_trading = data.get('paper_trading', True)

        # Check if bot is running
        if bot_manager.is_running:
            return jsonify({'error': 'Stop the bot before changing trading mode'}), 400

        # Update .env file
        env_file = '.env'
        if not os.path.exists(env_file):
            return jsonify({'error': '.env file not found'}), 500

        # Read current .env content
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Update paper trading setting
        for i, line in enumerate(lines):
            if line.startswith('PAPER_TRADING='):
                lines[i] = f'PAPER_TRADING={str(paper_trading)}\n'
                break

        # Write updated content
        with open(env_file, 'w') as f:
            f.writelines(lines)

        logger.warning(f"Trading mode changed to: {'Paper Trading' if paper_trading else 'LIVE TRADING'}")

        return jsonify({
            'success': True,
            'message': 'Trading mode updated. Restart required.'
        })

    except Exception as e:
        logger.error(f"Error updating trading mode: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alert-settings', methods=['POST'])
def update_alert_settings():
    """Update alert notification settings"""
    try:
        data = request.get_json()

        # Update .env file
        env_file = '.env'
        if not os.path.exists(env_file):
            return jsonify({'error': '.env file not found'}), 500

        # Read current .env content
        with open(env_file, 'r') as f:
            lines = f.readlines()

        # Update alert settings
        settings_map = {
            'email_alerts': 'ENABLE_EMAIL_ALERTS',
            'telegram_alerts': 'ENABLE_TELEGRAM_ALERTS',
            'discord_alerts': 'ENABLE_DISCORD_ALERTS'
        }

        for key, env_var in settings_map.items():
            if key in data:
                value = str(data[key])
                for i, line in enumerate(lines):
                    if line.startswith(f'{env_var}='):
                        lines[i] = f'{env_var}={value}\n'
                        break

        # Write updated content
        with open(env_file, 'w') as f:
            f.writelines(lines)

        logger.info("Alert settings updated successfully")

        return jsonify({
            'success': True,
            'message': 'Alert settings updated successfully'
        })

    except Exception as e:
        logger.error(f"Error updating alert settings: {e}")
        return jsonify({'error': str(e)}), 500

# ====================
# WEBSOCKET EVENTS
# ====================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to Kraken Bot'})

    # Send initial status
    emit('status_update', {
        'is_running': bot_manager.is_running,
        'paper_trading': config.PAPER_TRADING
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('subscribe_ticker')
def handle_subscribe_ticker(data):
    """Subscribe to ticker updates"""
    symbols = data.get('symbols', config.TRADING_PAIRS)

    def ticker_callback(ticker_data):
        socketio.emit('ticker_update', ticker_data)

    # Subscribe via Kraken WebSocket
    kraken_client.subscribe_ticker(symbols, ticker_callback)

@socketio.on('subscribe_positions')
def handle_subscribe_positions():
    """Subscribe to position updates"""
    def send_positions():
        while True:
            if bot_manager.is_running:
                positions = bot_manager.get_positions()
                socketio.emit('positions_update', {
                    'positions': positions,
                    'timestamp': datetime.now().isoformat()
                })
            time.sleep(config.PORTFOLIO_UPDATE_INTERVAL)

    # Start background thread
    thread = threading.Thread(target=send_positions)
    thread.daemon = True
    thread.start()

@socketio.on('manual_trade')
def handle_manual_trade(data):
    """Execute manual trade"""
    try:
        # Validate request
        required_fields = ['symbol', 'side', 'amount']
        for field in required_fields:
            if field not in data:
                emit('trade_error', {'error': f'Missing field: {field}'})
                return

        # Check if bot is running
        if not bot_manager.is_running:
            emit('trade_error', {'error': 'Bot must be running to execute trades'})
            return

        # Execute trade
        order = kraken_client.place_order(
            symbol=data['symbol'],
            side=data['side'],
            order_type=data.get('type', 'MARKET'),
            amount=data['amount'],
            price=data.get('price')
        )

        emit('trade_success', {
            'order': order,
            'message': f"Order placed: {order['id']}"
        })

        # Broadcast to all clients
        socketio.emit('new_trade', order)

    except Exception as e:
        logger.error(f"Manual trade error: {e}")
        emit('trade_error', {'error': str(e)})

# ====================
# BACKGROUND TASKS
# ====================

def broadcast_updates():
    """Broadcast updates to all connected clients"""
    while True:
        try:
            if bot_manager.is_running:
                # Get current data
                metrics = bot_manager.get_performance_metrics()
                balance = kraken_client.get_balance()

                # Broadcast update
                socketio.emit('update', {
                    'metrics': metrics,
                    'balance': balance,
                    'timestamp': datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"Broadcast error: {e}")

        time.sleep(config.PRICE_UPDATE_INTERVAL)

# ====================
# HELPER FUNCTIONS
# ====================

def _calculate_uptime():
    """Calculate bot uptime"""
    if not bot_state['start_time']:
        return "0:00:00"

    start = datetime.fromisoformat(bot_state['start_time'])
    delta = datetime.now() - start

    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    seconds = int(delta.total_seconds() % 60)

    return f"{hours}:{minutes:02d}:{seconds:02d}"

# ====================
# INITIALIZATION
# ====================

@app.before_first_request
def initialize():
    """Initialize the application"""
    # Create database tables
    with app.app_context():
        db.create_all()

    # Start background update thread
    update_thread = threading.Thread(target=broadcast_updates)
    update_thread.daemon = True
    update_thread.start()

    logger.info("Kraken Bot Dashboard initialized")

# ====================
# MAIN ENTRY POINT
# ====================

if __name__ == '__main__':
    # Safety warning for live trading
    if not config.PAPER_TRADING:
        print("\n" + "="*60)
        print("🚨 WARNING: LIVE TRADING MODE ENABLED 🚨")
        print("This bot will execute REAL trades with REAL money!")
        print("="*60 + "\n")

        confirmation = input("Type 'I_UNDERSTAND_LIVE_TRADING' to continue: ")
        if confirmation != 'I_UNDERSTAND_LIVE_TRADING':
            print("Startup cancelled. Exiting...")
            exit(0)

    # Run the application
    socketio.run(
        app,
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.DEBUG_MODE
    )