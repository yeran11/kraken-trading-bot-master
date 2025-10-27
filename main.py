#!/usr/bin/env python3
"""
Kraken Trading Bot - Main Entry Point
Start the bot and web dashboard
"""
import os
import sys
import signal
import time
import threading
from datetime import datetime
from loguru import logger
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

logger.add(
    "logs/kraken_bot.log",
    rotation="500 MB",
    retention="10 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

import config
from app import app, socketio, bot_manager, db_manager


class KrakenBotRunner:
    """Main bot runner class"""

    def __init__(self):
        self.app = app
        self.socketio = socketio
        self.bot_manager = bot_manager
        self.is_running = False
        self.shutdown_event = threading.Event()

    def print_banner(self):
        """Print startup banner"""
        banner = """
TPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPW
Q                                                               Q
Q     >‘ KRAKEN TRADING BOT v1.0.0 >‘                         Q
Q                                                               Q
Q     Advanced Cryptocurrency Trading System                    Q
Q     Powered by AI-Driven Strategies                          Q
Q                                                               Q
ZPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP]
        """
        print(banner)

    def print_status(self):
        """Print current status"""
        print("\n" + "="*60)
        print(f"=' CONFIGURATION")
        print("="*60)
        print(f"=Ê Environment: {config.ENVIRONMENT}")
        print(f"= Paper Trading: {config.PAPER_TRADING}")
        print(f"=± Trading Pairs: {', '.join(config.TRADING_PAIRS[:3])}...")
        print(f"<¯ Strategies: {', '.join(config.ENABLED_STRATEGIES)}")
        print(f"=° Max Position Size: ${config.MAX_POSITION_SIZE_USD}")
        print(f"   Max Daily Loss: ${config.MAX_DAILY_LOSS_USD}")
        print(f"=É Max Drawdown: {config.MAX_DRAWDOWN_PERCENT}%")
        print("="*60)

    def safety_check(self) -> bool:
        """Perform safety checks before starting"""
        if not config.PAPER_TRADING:
            print("\n" + "=¨"*30)
            print("\n   WARNING: LIVE TRADING MODE ENABLED!  ")
            print("\nThis bot will execute REAL trades with REAL money!")
            print("You can and will lose money if not configured properly.")
            print("\nPlease ensure:")
            print("1.  API keys are correctly configured")
            print("2.  Risk management settings are appropriate")
            print("3.  You understand the strategies being used")
            print("4.  You can afford to lose the money at risk")
            print("\n" + "=¨"*30 + "\n")

            confirmation = input("\nType 'I_UNDERSTAND_LIVE_TRADING' to continue: ")
            if confirmation != "I_UNDERSTAND_LIVE_TRADING":
                print("\nL Startup cancelled. Exiting...")
                return False

        return True

    def initialize_components(self):
        """Initialize all bot components"""
        try:
            print("\n= Initializing components...")

            # Create necessary directories
            os.makedirs('logs', exist_ok=True)
            os.makedirs('backups', exist_ok=True)
            os.makedirs(config.LOG_DIR, exist_ok=True)

            # Initialize database
            print("=Ê Initializing database...")
            with self.app.app_context():
                db_manager.init_database()

            print(" Components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization error: {e}")
            print(f"\nL Initialization failed: {e}")
            return False

    def start_web_server(self):
        """Start the web dashboard server"""
        try:
            print(f"\n< Starting web dashboard on http://0.0.0.0:{config.FLASK_PORT}")
            print(f"=ñ Access the dashboard at http://localhost:{config.FLASK_PORT}")

            # Run Flask with SocketIO
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=config.FLASK_PORT,
                debug=False,
                use_reloader=False,
                log_output=False
            )

        except Exception as e:
            logger.error(f"Web server error: {e}")
            print(f"\nL Failed to start web server: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n\n   Received signal {signum}. Shutting down gracefully...")

        # Stop the bot if running
        if self.bot_manager.is_running:
            print("=Ñ Stopping trading bot...")
            self.bot_manager.stop(close_positions=False, cancel_orders=True)

        # Set shutdown event
        self.shutdown_event.set()

        print("=K Goodbye!")
        sys.exit(0)

    def run(self):
        """Main run method"""
        try:
            # Print banner
            self.print_banner()

            # Print configuration
            self.print_status()

            # Safety check for live trading
            if not self.safety_check():
                return

            # Initialize components
            if not self.initialize_components():
                return

            # Register signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            # Print instructions
            print("\n" + "="*60)
            print("=Ì INSTRUCTIONS")
            print("="*60)
            print("1. Open your browser and navigate to the dashboard")
            print("2. Use the START/STOP buttons to control the bot")
            print("3. Monitor positions and performance in real-time")
            print("4. Press Ctrl+C to shutdown the system")
            print("="*60)

            print("\n System ready! Starting web server...\n")

            # Start web server (blocking)
            self.start_web_server()

        except KeyboardInterrupt:
            print("\n\n   Keyboard interrupt received. Shutting down...")
            self.signal_handler(signal.SIGINT, None)

        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            print(f"\nL Fatal error: {e}")
            sys.exit(1)


def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import krakenex
        import ccxt
        import pandas
        import numpy
        import flask
        import flask_socketio
        import sqlalchemy
        import loguru
        import requests
        return True
    except ImportError as e:
        print(f"\nL Missing dependency: {e}")
        print("\n=æ Please install dependencies:")
        print("   pip install -r requirements.txt")
        return False


def main():
    """Main entry point"""
    # Check Python version
    if sys.version_info < (3, 8):
        print("L Python 3.8+ is required")
        sys.exit(1)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Create and run bot
    runner = KrakenBotRunner()
    runner.run()


if __name__ == "__main__":
    main()