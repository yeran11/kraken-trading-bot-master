#!/usr/bin/env python3
"""
Simplified startup script for Kraken Trading Bot
Handles missing dependencies gracefully
"""
import os
import sys
import subprocess
import warnings
warnings.filterwarnings('ignore')

print("🦑 Starting Kraken Trading Bot...")

# Auto-install minimal requirements if needed
def install_if_missing(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])

# Check core dependencies
required_packages = ['flask', 'flask_cors', 'flask_socketio', 'flask_sqlalchemy', 'eventlet', 'loguru']
for pkg in required_packages:
    install_if_missing(pkg.replace('_', '-') if '_' in pkg else pkg)

# Set default environment variables
os.environ.setdefault('PAPER_TRADING', 'True')
os.environ.setdefault('ENVIRONMENT', 'development')
os.environ.setdefault('FLASK_APP', 'start_app.py')
os.environ.setdefault('PORT', '5000')

# Create necessary directories
os.makedirs('logs', exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

try:
    from flask import Flask, render_template, jsonify, request
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit
    print("✅ Flask modules loaded")
except ImportError as e:
    print(f"❌ Error loading Flask: {e}")
    print("Installing required packages...")
    os.system("pip install flask flask-cors flask-socketio eventlet --quiet")
    from flask import Flask, render_template, jsonify, request
    from flask_cors import CORS
    from flask_socketio import SocketIO, emit

# Create minimal Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Create mock components if main ones fail to load
bot_manager = None
kraken_client = None
risk_manager = None
strategy_manager = None
alert_manager = None
db_manager = None

# Try to import main components
try:
    import config
    print("✅ Config loaded")
except Exception as e:
    print(f"⚠️ Using default config: {e}")
    # Create minimal config
    class config:
        PAPER_TRADING = True
        ENVIRONMENT = 'development'
        FLASK_PORT = 5000
        FLASK_HOST = '0.0.0.0'
        TRADING_PAIRS = ['BTC/USD', 'ETH/USD', 'SOL/USD']
        ENABLED_STRATEGIES = ['momentum', 'mean_reversion']
        MAX_POSITION_SIZE_USD = 1000
        MAX_DAILY_LOSS_USD = 500
        MAX_DRAWDOWN_PERCENT = 15

try:
    from kraken_client import KrakenClient
    from bot_manager import BotManager
    from risk_manager import RiskManager
    from strategies import StrategyManager
    from alerts import AlertManager
    from database import db_manager

    kraken_client = KrakenClient()
    risk_manager = RiskManager(kraken_client)
    strategy_manager = StrategyManager(kraken_client, risk_manager)
    alert_manager = AlertManager()
    bot_manager = BotManager(kraken_client, strategy_manager, risk_manager, alert_manager)
    print("✅ Trading components loaded")

except Exception as e:
    print(f"⚠️ Trading components not fully loaded: {e}")
    print("Running in demo mode...")

    # Create mock bot manager
    class MockBotManager:
        def __init__(self):
            self.is_running = False

        def start(self, **kwargs):
            self.is_running = True
            return True

        def stop(self, **kwargs):
            self.is_running = False
            return True

        def get_status(self):
            return {
                'is_running': self.is_running,
                'paper_trading': True,
                'total_trades': 0,
                'open_positions': 0
            }

        def get_positions(self):
            return []

        def get_performance_metrics(self):
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'total_pnl': 0,
                'win_rate': 0
            }

    bot_manager = MockBotManager()

# Routes
@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/status')
def get_status():
    """Get bot status"""
    try:
        if bot_manager:
            return jsonify(bot_manager.get_status())
        else:
            return jsonify({
                'is_running': False,
                'paper_trading': True,
                'error': 'Bot manager not initialized'
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the bot"""
    try:
        if bot_manager:
            success = bot_manager.start()
            return jsonify({'success': success, 'message': 'Bot started (demo mode)'})
        return jsonify({'error': 'Bot not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the bot"""
    try:
        if bot_manager:
            success = bot_manager.stop()
            return jsonify({'success': success, 'message': 'Bot stopped'})
        return jsonify({'error': 'Bot not initialized'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/balance')
def get_balance():
    """Get mock balance"""
    return jsonify({
        'balances': {'USD': 10000, 'BTC': 0.5, 'ETH': 2},
        'total_usd': 35000,
        'timestamp': '2024-01-01T00:00:00'
    })

@app.route('/api/positions')
def get_positions():
    """Get positions"""
    if bot_manager:
        positions = bot_manager.get_positions()
        return jsonify({'positions': positions, 'count': len(positions)})
    return jsonify({'positions': [], 'count': 0})

@app.route('/api/orders')
def get_orders():
    """Get orders"""
    return jsonify({'orders': [], 'count': 0})

@app.route('/api/trades')
def get_trades():
    """Get trades"""
    return jsonify({
        'trades': [],
        'statistics': {
            'total_trades': 0,
            'profitable_trades': 0,
            'win_rate': 0,
            'total_pnl': 0
        }
    })

@app.route('/api/performance')
def get_performance():
    """Get performance metrics"""
    if bot_manager:
        metrics = bot_manager.get_performance_metrics()
        return jsonify({'metrics': metrics})
    return jsonify({
        'metrics': {
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0
        }
    })

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Handle settings"""
    if request.method == 'GET':
        return jsonify({
            'paper_trading': True,
            'enabled_strategies': ['momentum'],
            'trading_pairs': ['BTC/USD'],
            'risk_settings': {
                'max_position_size': 1000,
                'max_total_exposure': 10000
            }
        })
    return jsonify({'success': True})

@app.route('/api/logs')
def get_logs():
    """Get logs"""
    return jsonify({'logs': ['System started', 'Running in demo mode'], 'count': 2})

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle connection"""
    emit('connected', {'message': 'Connected to Kraken Bot'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle disconnection"""
    pass

@socketio.on('subscribe_ticker')
def handle_subscribe_ticker(data):
    """Subscribe to ticker"""
    emit('ticker_update', {
        'symbol': 'BTC/USD',
        'price': 45000,
        'change': 2.5
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🦑 KRAKEN TRADING BOT - DEMO MODE")
    print("="*60)
    print(f"📊 Paper Trading: ENABLED")
    print(f"🌐 Dashboard: http://0.0.0.0:5000")
    print("="*60 + "\n")

    # Run the app
    port = int(os.environ.get('PORT', 5000))

    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        print(f"Error starting server: {e}")
        # Fallback to basic Flask
        app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()