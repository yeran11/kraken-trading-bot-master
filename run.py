#!/usr/bin/env python3
"""
Main runner for Kraken Trading Bot
This file will work with minimal dependencies
"""

import os
import sys

print("🦑 Kraken Trading Bot Starting...")
print("="*60)

# First, ensure Flask is installed
try:
    import flask
    print("✅ Flask is installed")
except ImportError:
    print("📦 Installing Flask...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "--quiet"])
    print("✅ Flask installed")

# Now import and run the app
from flask import Flask, render_template, jsonify, request

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'kraken-bot-secret-key'

# Bot state tracking
bot_state = {
    'is_running': False,
    'start_time': None,
    'paper_trading': True
}

# Routes
@app.route('/')
def home():
    """Serve the dashboard HTML"""
    try:
        return render_template('dashboard.html')
    except:
        # If template fails, return simple HTML
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Kraken Bot</title>
            <style>
                body { background: #0B0E11; color: #fff; font-family: Arial; padding: 20px; }
                .container { max-width: 800px; margin: 0 auto; text-align: center; }
                h1 { color: #5741D9; }
                .status { background: rgba(87, 65, 217, 0.1); padding: 20px; border-radius: 10px; margin: 20px 0; }
                button { background: #5741D9; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
                button:hover { background: #7B68EE; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🦑 Kraken Trading Bot</h1>
                <div class="status">
                    <h2>Status: Ready</h2>
                    <p>Paper Trading Mode: ENABLED</p>
                    <p>The bot is running in demo mode.</p>
                    <button onclick="alert('Bot started!')">Start Bot</button>
                    <button onclick="alert('Bot stopped!')">Stop Bot</button>
                </div>
            </div>
        </body>
        </html>
        """

@app.route('/api/status')
def api_status():
    """Return bot status as JSON"""
    from dotenv import load_dotenv
    from datetime import datetime
    load_dotenv()

    # Check actual paper trading setting
    paper_trading_str = os.getenv('PAPER_TRADING', 'True')
    paper_trading = paper_trading_str.lower() in ('true', '1', 'yes')

    # Check if API keys are configured
    api_key = os.getenv('KRAKEN_API_KEY', '')
    api_secret = os.getenv('KRAKEN_API_SECRET', '')
    has_real_keys = api_key and api_secret and 'YOUR_API_KEY' not in api_key and 'YOUR_PRIVATE_KEY' not in api_secret

    # If PAPER_TRADING is False but no real keys, force paper trading for safety
    if not paper_trading and not has_real_keys:
        paper_trading = True
        message = 'Paper trading mode (no valid API keys detected)'
    elif not paper_trading and has_real_keys:
        message = 'LIVE TRADING MODE - Real trades will be executed'
    else:
        message = 'Bot is operational in demo mode'

    # Calculate uptime
    uptime_seconds = 0
    if bot_state['is_running'] and bot_state['start_time']:
        uptime_seconds = int((datetime.now() - bot_state['start_time']).total_seconds())

    return jsonify({
        'status': 'running',
        'paper_trading': paper_trading,
        'version': '1.0.0',
        'message': message,
        'is_running': bot_state['is_running'],
        'uptime_seconds': uptime_seconds,
        'start_time': bot_state['start_time'].isoformat() if bot_state['start_time'] else None
    })

@app.route('/api/balance')
def api_balance():
    """Get real balance from Kraken"""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_API_SECRET', '')

        # Check if we have valid credentials
        if not api_key or not api_secret or 'your_' in api_key.lower():
            # Return mock balance if no valid credentials
            return jsonify({
                'USD': 10000.00,
                'BTC': 0.0,
                'ETH': 0.0,
                'total_usd': 10000.00,
                'mock': True
            })

        # Fetch real balance from Kraken
        import ccxt
        exchange = ccxt.kraken({
            'apiKey': api_key,
            'secret': api_secret
        })

        balance = exchange.fetch_balance()

        # Get individual balances
        usd_balance = float(balance.get('USD', {}).get('free', 0))
        btc_balance = float(balance.get('BTC', {}).get('free', 0))
        eth_balance = float(balance.get('ETH', {}).get('free', 0))
        sol_balance = float(balance.get('SOL', {}).get('free', 0))

        # Calculate total in USD (need to fetch prices)
        total_usd = usd_balance

        try:
            # Fetch current prices to convert crypto to USD
            if btc_balance > 0:
                btc_ticker = exchange.fetch_ticker('BTC/USD')
                total_usd += btc_balance * btc_ticker['last']

            if eth_balance > 0:
                eth_ticker = exchange.fetch_ticker('ETH/USD')
                total_usd += eth_balance * eth_ticker['last']

            if sol_balance > 0:
                sol_ticker = exchange.fetch_ticker('SOL/USD')
                total_usd += sol_balance * sol_ticker['last']
        except:
            pass  # If price fetch fails, just use USD balance

        # Return relevant balances
        return jsonify({
            'USD': usd_balance,
            'BTC': btc_balance,
            'ETH': eth_balance,
            'SOL': sol_balance,
            'total_usd': total_usd,
            'mock': False
        })

    except Exception as e:
        # Return mock balance on error
        return jsonify({
            'USD': 10000.00,
            'BTC': 0.0,
            'ETH': 0.0,
            'total_usd': 10000.00,
            'mock': True,
            'error': str(e)
        })

@app.route('/api/market-data/<symbol>')
def get_market_data(symbol):
    """Get real-time market data for a symbol from Kraken"""
    try:
        import ccxt

        # Create Kraken exchange instance
        exchange = ccxt.kraken()

        # Replace URL format to CCXT format if needed
        symbol = symbol.replace('-', '/')

        # Fetch ticker
        ticker = exchange.fetch_ticker(symbol)

        # Fetch recent OHLCV for sparkline (last 24 hours, 1h candles)
        ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=24)

        # Extract sparkline prices
        sparkline = [candle[4] for candle in ohlcv]  # closing prices

        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': {
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'high_24h': ticker['high'],
                'low_24h': ticker['low'],
                'volume_24h': ticker['quoteVolume'],
                'change_24h': ticker['percentage'],
                'change_amount': ticker['change'],
                'timestamp': ticker['timestamp'],
                'sparkline': sparkline
            }
        })

    except Exception as e:
        # Fallback to mock data if error
        return jsonify({
            'success': False,
            'error': str(e),
            'symbol': symbol,
            'data': {
                'price': 0,
                'bid': 0,
                'ask': 0,
                'high_24h': 0,
                'low_24h': 0,
                'volume_24h': 0,
                'change_24h': 0,
                'change_amount': 0,
                'timestamp': 0,
                'sparkline': []
            }
        })

@app.route('/api/market-data-batch', methods=['POST'])
def get_market_data_batch():
    """Get real-time market data for multiple symbols"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])

        if not symbols:
            return jsonify({'error': 'No symbols provided'}), 400

        import ccxt
        exchange = ccxt.kraken()

        results = {}

        for symbol in symbols:
            try:
                # Fetch ticker
                ticker = exchange.fetch_ticker(symbol)

                results[symbol] = {
                    'price': ticker['last'],
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'high_24h': ticker['high'],
                    'low_24h': ticker['low'],
                    'volume_24h': ticker['quoteVolume'],
                    'change_24h': ticker['percentage'],
                    'change_amount': ticker['change'],
                    'timestamp': ticker['timestamp']
                }
            except Exception as e:
                # Add error entry but continue with other symbols
                results[symbol] = {
                    'error': str(e),
                    'price': 0,
                    'change_24h': 0
                }

        return jsonify({
            'success': True,
            'data': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ohlcv/<symbol>')
def get_ohlcv(symbol):
    """Get OHLCV candlestick data for charts"""
    try:
        import ccxt

        # Get parameters
        timeframe = request.args.get('timeframe', '1h')
        limit = request.args.get('limit', 100, type=int)

        # Create exchange
        exchange = ccxt.kraken()

        # Replace URL format
        symbol = symbol.replace('-', '/')

        # Fetch OHLCV
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        # Format data
        formatted_data = {
            'symbol': symbol,
            'timeframe': timeframe,
            'data': [
                {
                    'timestamp': candle[0],
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                }
                for candle in ohlcv
            ]
        }

        return jsonify({
            'success': True,
            **formatted_data
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orderbook/<symbol>')
def get_orderbook(symbol):
    """Get orderbook data"""
    try:
        import ccxt

        depth = request.args.get('depth', 10, type=int)

        exchange = ccxt.kraken()
        symbol = symbol.replace('-', '/')

        orderbook = exchange.fetch_order_book(symbol, limit=depth)

        return jsonify({
            'success': True,
            'symbol': symbol,
            'bids': orderbook['bids'][:depth],
            'asks': orderbook['asks'][:depth],
            'timestamp': orderbook['timestamp']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/positions')
def api_positions():
    """Return empty positions"""
    return jsonify([])

@app.route('/api/start', methods=['POST'])
def api_start():
    """Start the trading bot"""
    from datetime import datetime
    from dotenv import load_dotenv
    load_dotenv()

    if bot_state['is_running']:
        return jsonify({'success': False, 'message': 'Bot is already running'})

    # Update bot state
    bot_state['is_running'] = True
    bot_state['start_time'] = datetime.now()
    bot_state['paper_trading'] = os.getenv('PAPER_TRADING', 'True').lower() in ('true', '1', 'yes')

    mode = 'paper trading' if bot_state['paper_trading'] else 'LIVE TRADING'
    return jsonify({
        'success': True,
        'message': f'Bot started in {mode} mode',
        'start_time': bot_state['start_time'].isoformat()
    })

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Stop the trading bot"""
    if not bot_state['is_running']:
        return jsonify({'success': False, 'message': 'Bot is not running'})

    bot_state['is_running'] = False
    bot_state['start_time'] = None

    return jsonify({'success': True, 'message': 'Bot stopped'})

@app.route('/settings')
def settings_page():
    """Settings page"""
    try:
        # Load current settings from .env
        from dotenv import load_dotenv
        load_dotenv()

        paper_trading = os.getenv('PAPER_TRADING', 'True') == 'True'
        max_order_size = os.getenv('MAX_ORDER_SIZE_USD', '100')
        max_position_size = os.getenv('MAX_POSITION_SIZE_USD', '500')
        max_exposure = os.getenv('MAX_TOTAL_EXPOSURE_USD', '2000')
        max_daily_loss = os.getenv('MAX_DAILY_LOSS_USD', '100')
        stop_loss = os.getenv('STOP_LOSS_PERCENT', '2.0')
        take_profit = os.getenv('TAKE_PROFIT_PERCENT', '3.0')
        email_alerts = os.getenv('ENABLE_EMAIL_ALERTS', 'False') == 'True'
        telegram_alerts = os.getenv('ENABLE_TELEGRAM_ALERTS', 'False') == 'True'
        discord_alerts = os.getenv('ENABLE_DISCORD_ALERTS', 'False') == 'True'

        return render_template('settings.html',
                             paper_trading=paper_trading,
                             max_order_size=max_order_size,
                             max_position_size=max_position_size,
                             max_exposure=max_exposure,
                             max_daily_loss=max_daily_loss,
                             stop_loss=stop_loss,
                             take_profit=take_profit,
                             email_alerts=email_alerts,
                             telegram_alerts=telegram_alerts,
                             discord_alerts=discord_alerts)
    except Exception as e:
        return f"Error loading settings: {e}", 500

@app.route('/api/credentials', methods=['POST'])
def update_credentials():
    """Update API credentials in .env file"""
    try:
        data = request.get_json()
        api_key = data.get('api_key', '').strip()
        api_secret = data.get('api_secret', '').strip()

        if not api_key or not api_secret:
            return jsonify({'error': 'API key and secret are required'}), 400

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

        return jsonify({
            'success': True,
            'message': 'API credentials saved. Please restart the bot.'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-connection')
def test_connection():
    """Test API connection"""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        api_key = os.getenv('KRAKEN_API_KEY', '')
        api_secret = os.getenv('KRAKEN_API_SECRET', '')

        if not api_key or not api_secret or 'YOUR_API_KEY' in api_key or 'YOUR_PRIVATE_KEY' in api_secret:
            return jsonify({'error': 'API credentials not configured yet'}), 400

        # Try to import and test kraken client
        try:
            from kraken_client import KrakenClient
            client = KrakenClient()
            balance = client.get_balance()

            return jsonify({
                'success': True,
                'message': 'Connection successful',
                'balance': balance
            })
        except ImportError:
            return jsonify({'error': 'Kraken client not available. Install dependencies first.'}), 500

    except Exception as e:
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

        return jsonify({
            'success': True,
            'message': 'Risk settings updated successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading-mode', methods=['POST'])
def update_trading_mode():
    """Update trading mode (paper/live)"""
    try:
        data = request.get_json()
        paper_trading = data.get('paper_trading', True)

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

        return jsonify({
            'success': True,
            'message': 'Trading mode updated. Restart required.'
        })

    except Exception as e:
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

        return jsonify({
            'success': True,
            'message': 'Alert settings updated successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# In-memory cache for available pairs
_pairs_cache = {
    'data': None,
    'timestamp': 0,
    'cache_duration': 300  # 5 minutes
}

@app.route('/api/available-pairs')
def get_available_pairs():
    """Get available trading pairs from Kraken (FAST with caching)"""
    try:
        import time

        # Check cache first
        current_time = time.time()
        if _pairs_cache['data'] and (current_time - _pairs_cache['timestamp']) < _pairs_cache['cache_duration']:
            return jsonify(_pairs_cache['data'])

        # Hardcoded popular pairs for INSTANT response
        popular_pairs = [
            {'symbol': 'BTC/USD', 'base': 'BTC', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'ETH/USD', 'base': 'ETH', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'SOL/USD', 'base': 'SOL', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'XRP/USD', 'base': 'XRP', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'ADA/USD', 'base': 'ADA', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'DOT/USD', 'base': 'DOT', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'AVAX/USD', 'base': 'AVAX', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'MATIC/USD', 'base': 'MATIC', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'LINK/USD', 'base': 'LINK', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'UNI/USD', 'base': 'UNI', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'LTC/USD', 'base': 'LTC', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'BCH/USD', 'base': 'BCH', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'ATOM/USD', 'base': 'ATOM', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'ALGO/USD', 'base': 'ALGO', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
            {'symbol': 'DOGE/USD', 'base': 'DOGE', 'quote': 'USD', 'price': 0, 'change_24h': 0, 'priority': True},
        ]

        # Try to get more pairs from Kraken (but don't block on it)
        try:
            import ccxt
            exchange = ccxt.kraken()

            # Load markets (this is cached by ccxt after first call)
            markets = exchange.load_markets()

            # Filter for USD pairs only (no ticker fetching - that's slow!)
            pairs_data = []
            priority_cryptos = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'AVAX', 'MATIC', 'LINK', 'UNI', 'LTC', 'BCH', 'ATOM', 'ALGO', 'DOGE']

            for symbol, market in markets.items():
                if '/USD' in symbol and market.get('active', True):
                    base = symbol.split('/')[0]

                    pairs_data.append({
                        'symbol': symbol,
                        'base': base,
                        'quote': 'USD',
                        'price': 0,  # No price fetching here - too slow!
                        'change_24h': 0,
                        'priority': base in priority_cryptos
                    })

            # Sort by priority, then alphabetically
            pairs_data.sort(key=lambda x: (not x['priority'], x['symbol']))

            # Cache the result
            result = {
                'success': True,
                'pairs': pairs_data,
                'count': len(pairs_data),
                'cached': False
            }

            _pairs_cache['data'] = result
            _pairs_cache['timestamp'] = current_time

            return jsonify(result)

        except Exception as e:
            # If ccxt fails, return hardcoded pairs immediately
            result = {
                'success': True,
                'pairs': popular_pairs,
                'count': len(popular_pairs),
                'cached': False,
                'fallback': True
            }

            # Cache the fallback too
            _pairs_cache['data'] = result
            _pairs_cache['timestamp'] = current_time

            return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/pair-prices', methods=['POST'])
def get_pair_prices():
    """Get live prices for specific pairs"""
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])

        if not symbols:
            return jsonify({'error': 'No symbols provided'}), 400

        prices = {}

        try:
            import ccxt
            exchange = ccxt.kraken()

            for symbol in symbols:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    prices[symbol] = {
                        'price': ticker['last'],
                        'change_24h': ticker['percentage'],
                        'volume': ticker['quoteVolume'],
                        'high_24h': ticker['high'],
                        'low_24h': ticker['low']
                    }
                except:
                    prices[symbol] = {
                        'price': 0,
                        'change_24h': 0,
                        'volume': 0,
                        'high_24h': 0,
                        'low_24h': 0
                    }
        except ImportError:
            # Return empty if ccxt not available
            for symbol in symbols:
                prices[symbol] = {
                    'price': 0,
                    'change_24h': 0,
                    'volume': 0,
                    'high_24h': 0,
                    'low_24h': 0
                }

        return jsonify({
            'success': True,
            'prices': prices
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trading-pairs', methods=['GET', 'POST'])
def handle_trading_pairs():
    """Get or update trading pair configuration"""
    try:
        if request.method == 'GET':
            # Load current configuration
            config_file = 'trading_pairs_config.json'

            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    import json
                    config = json.load(f)
            else:
                # Default configuration
                config = {
                    'pairs': [
                        {
                            'symbol': 'BTC/USD',
                            'enabled': True,
                            'allocation': 30,
                            'strategies': ['momentum', 'mean_reversion']
                        },
                        {
                            'symbol': 'ETH/USD',
                            'enabled': True,
                            'allocation': 30,
                            'strategies': ['momentum', 'mean_reversion']
                        },
                        {
                            'symbol': 'SOL/USD',
                            'enabled': False,
                            'allocation': 20,
                            'strategies': ['scalping']
                        }
                    ]
                }

            return jsonify({
                'success': True,
                'config': config
            })

        else:  # POST
            data = request.get_json()
            pairs_config = data.get('pairs', [])

            # Validate total allocation doesn't exceed 100%
            total_allocation = sum(p['allocation'] for p in pairs_config if p['enabled'])
            if total_allocation > 100:
                return jsonify({
                    'error': 'Total allocation cannot exceed 100%',
                    'total': total_allocation
                }), 400

            # Save configuration
            config_file = 'trading_pairs_config.json'
            with open(config_file, 'w') as f:
                import json
                json.dump({'pairs': pairs_config}, f, indent=2)

            # Also update .env with comma-separated pair list
            enabled_pairs = [p['symbol'] for p in pairs_config if p['enabled']]

            env_file = '.env'
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    lines = f.readlines()

                # Update TRADING_PAIRS
                pairs_str = ','.join(enabled_pairs)
                found = False
                for i, line in enumerate(lines):
                    if line.startswith('TRADING_PAIRS='):
                        lines[i] = f'TRADING_PAIRS={pairs_str}\n'
                        found = True
                        break

                # Add if not found
                if not found:
                    lines.append(f'\nTRADING_PAIRS={pairs_str}\n')

                with open(env_file, 'w') as f:
                    f.writelines(lines)

            return jsonify({
                'success': True,
                'message': f'Trading pairs updated. {len(enabled_pairs)} pairs enabled.',
                'enabled_pairs': enabled_pairs,
                'total_allocation': total_allocation
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

# Run the application
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))

    # Load settings to show correct mode at startup
    from dotenv import load_dotenv
    load_dotenv()

    paper_trading_str = os.getenv('PAPER_TRADING', 'True')
    paper_trading = paper_trading_str.lower() in ('true', '1', 'yes')

    api_key = os.getenv('KRAKEN_API_KEY', '')
    api_secret = os.getenv('KRAKEN_API_SECRET', '')
    has_real_keys = api_key and api_secret and 'YOUR_API_KEY' not in api_key and 'YOUR_PRIVATE_KEY' not in api_secret

    print(f"✅ Starting web server on port {port}")
    print(f"🌐 Dashboard will be available at http://0.0.0.0:{port}")
    print("="*60)

    if not paper_trading and has_real_keys:
        print("⚠️  LIVE TRADING MODE ENABLED ⚠️")
        print("💰 REAL TRADES will be executed with REAL MONEY")
        print("🔑 API credentials detected and loaded")
        print("🚨 Monitor your positions closely!")
    elif not paper_trading and not has_real_keys:
        print("📊 Paper Trading: ENABLED (No valid API keys)")
        print("💰 Demo Balance: $10,000")
        print("🛡️ No real money will be used")
    else:
        print("📊 Paper Trading: ENABLED (Safe Mode)")
        print("💰 Demo Balance: $10,000")
        print("🛡️ No real money will be used")

    print("="*60)

    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error: {e}")
        print("Trying alternative port...")
        app.run(host='0.0.0.0', port=8080, debug=False)