#!/usr/bin/env python3
"""
Ultra-simple Flask app for Kraken Bot
Minimal dependencies - guaranteed to work
"""
import os
import sys

# Install Flask if not present
try:
    from flask import Flask, render_template, jsonify
except ImportError:
    print("Installing Flask...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask", "--quiet"])
    from flask import Flask, render_template, jsonify

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key'

# Basic routes
@app.route('/')
def index():
    """Serve the dashboard"""
    return render_template('dashboard.html')

@app.route('/api/status')
def status():
    """Return bot status"""
    return jsonify({
        'is_running': False,
        'paper_trading': True,
        'message': 'Bot in demo mode - Click START to begin'
    })

@app.route('/api/balance')
def balance():
    """Return mock balance"""
    return jsonify({
        'balances': {'USD': 10000.00},
        'total_usd': 10000.00
    })

@app.route('/api/positions')
def positions():
    """Return positions"""
    return jsonify({'positions': [], 'count': 0})

@app.route('/api/start', methods=['POST'])
def start():
    """Start bot"""
    return jsonify({'success': True, 'message': 'Bot started in demo mode'})

@app.route('/api/stop', methods=['POST'])
def stop():
    """Stop bot"""
    return jsonify({'success': True, 'message': 'Bot stopped'})

# Main entry
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🦑 KRAKEN TRADING BOT - STARTING")
    print("="*60)
    print("📊 Mode: DEMO / PAPER TRADING")
    print("🌐 Dashboard: http://0.0.0.0:5000")
    print("="*60 + "\n")

    # Get port from environment
    port = int(os.environ.get('PORT', 5000))

    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=False)