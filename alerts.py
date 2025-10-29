"""
Alert Manager for Kraken Trading Bot
Handles email, Telegram, Discord, and dashboard notifications
"""
import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import asyncio
import aiohttp

import config
from database import db_manager, Alert


class AlertManager:
    """Manages all alert notifications"""

    def __init__(self):
        self.email_enabled = config.ENABLE_EMAIL_ALERTS
        self.telegram_enabled = config.ENABLE_TELEGRAM_ALERTS
        self.discord_enabled = config.ENABLE_DISCORD_ALERTS

        # Alert levels and their priorities
        self.alert_levels = {
            'debug': 0,
            'info': 1,
            'warning': 2,
            'error': 3,
            'critical': 4
        }

        # Alert rate limiting
        self.last_alert_time = {}
        self.alert_cooldown = 60  # Seconds between similar alerts

        logger.info("Alert Manager initialized")

    def send_alert(self, title: str, message: str, level: str = 'info',
                  category: Optional[str] = None, details: Optional[Dict] = None) -> bool:
        """Send alert through all configured channels"""
        try:
            # Check rate limiting
            alert_key = f"{title}_{level}"
            if self._is_rate_limited(alert_key):
                logger.debug(f"Alert rate limited: {title}")
                return False

            # Record alert in database
            db_manager.create_alert(level, title, message, category)

            # Format alert message
            formatted_message = self._format_alert(title, message, level, details)

            # Send through enabled channels
            success = False

            if self.email_enabled:
                success |= self._send_email_alert(title, formatted_message, level)

            if self.telegram_enabled:
                success |= self._send_telegram_alert(formatted_message, level)

            if self.discord_enabled:
                success |= self._send_discord_alert(formatted_message, level)

            # Update rate limiting
            self.last_alert_time[alert_key] = datetime.utcnow()

            logger.info(f"Alert sent: {title} (Level: {level})")
            return success

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    def _format_alert(self, title: str, message: str, level: str, details: Optional[Dict]) -> str:
        """Format alert message for sending"""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Choose emoji based on level
        emoji_map = {
            'debug': '🐛',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        emoji = emoji_map.get(level, '📢')

        # Format message
        formatted = f"{emoji} **{title.upper()}**\n"
        formatted += f"Level: {level.upper()}\n"
        formatted += f"Time: {timestamp}\n"
        formatted += f"\n{message}\n"

        # Add details if provided
        if details:
            formatted += "\n**Details:**\n"
            for key, value in details.items():
                formatted += f"• {key}: {value}\n"

        return formatted

    def _is_rate_limited(self, alert_key: str) -> bool:
        """Check if alert is rate limited"""
        if alert_key not in self.last_alert_time:
            return False

        elapsed = (datetime.utcnow() - self.last_alert_time[alert_key]).total_seconds()
        return elapsed < self.alert_cooldown

    # ====================
    # EMAIL ALERTS
    # ====================

    def _send_email_alert(self, subject: str, message: str, level: str) -> bool:
        """Send email alert"""
        try:
            if not all([config.SMTP_SERVER, config.SMTP_USERNAME, config.SMTP_PASSWORD, config.ALERT_EMAIL_TO]):
                logger.warning("Email configuration incomplete")
                return False

            # Only send email for important alerts
            if self.alert_levels.get(level, 0) < self.alert_levels['warning']:
                return True  # Skip low priority alerts

            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[Kraken Bot] {subject}"
            msg['From'] = config.SMTP_USERNAME
            msg['To'] = config.ALERT_EMAIL_TO

            # Create HTML content
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="background-color: #f0f0f0; padding: 20px; border-radius: 10px;">
                    <h2 style="color: {'#d32f2f' if level in ['error', 'critical'] else '#1976d2'};">
                        {subject}
                    </h2>
                    <pre style="background-color: white; padding: 15px; border-radius: 5px;">
{message}
                    </pre>
                    <p style="color: #666; font-size: 12px;">
                        Sent by Kraken Trading Bot at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
                    </p>
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(message, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            # Send email
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
                server.starttls()
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.send_message(msg)

            logger.debug(f"Email alert sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False

    # ====================
    # TELEGRAM ALERTS
    # ====================

    def _send_telegram_alert(self, message: str, level: str) -> bool:
        """Send Telegram alert"""
        try:
            if not all([config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID]):
                logger.warning("Telegram configuration incomplete")
                return False

            # Format message for Telegram (Markdown)
            telegram_message = message.replace('**', '*')  # Convert to Telegram markdown

            url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': config.TELEGRAM_CHAT_ID,
                'text': telegram_message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.debug("Telegram alert sent")
                return True
            else:
                logger.error(f"Telegram API error: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False

    # ====================
    # DISCORD ALERTS
    # ====================

    def _send_discord_alert(self, message: str, level: str) -> bool:
        """Send Discord alert via webhook"""
        try:
            if not config.DISCORD_WEBHOOK_URL:
                logger.warning("Discord webhook URL not configured")
                return False

            # Choose color based on level
            color_map = {
                'debug': 0x9E9E9E,    # Gray
                'info': 0x2196F3,     # Blue
                'warning': 0xFFC107,  # Amber
                'error': 0xF44336,    # Red
                'critical': 0x9C27B0  # Purple
            }
            color = color_map.get(level, 0x2196F3)

            # Create embed
            embed = {
                'embeds': [{
                    'title': 'Kraken Trading Bot Alert',
                    'description': message,
                    'color': color,
                    'timestamp': datetime.utcnow().isoformat(),
                    'footer': {
                        'text': f'Level: {level.upper()}'
                    }
                }]
            }

            response = requests.post(config.DISCORD_WEBHOOK_URL, json=embed, timeout=10)

            if response.status_code in [200, 204]:
                logger.debug("Discord alert sent")
                return True
            else:
                logger.error(f"Discord webhook error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False

    # ====================
    # SPECIALIZED ALERTS
    # ====================

    def send_trade_alert(self, trade: Dict):
        """Send alert for trade execution"""
        try:
            symbol = trade.get('symbol', 'Unknown')
            side = trade.get('side', 'Unknown')
            price = trade.get('price', 0)
            quantity = trade.get('quantity', 0)
            pnl = trade.get('pnl', 0)

            title = f"Trade Executed: {side} {symbol}"

            message = f"Order executed successfully\n"
            message += f"Symbol: {symbol}\n"
            message += f"Side: {side}\n"
            message += f"Price: ${price:.6f}\n"
            message += f"Quantity: {quantity:.4f}\n"

            if pnl != 0:
                message += f"P&L: ${pnl:.6f} ({pnl/price*100:.2f}%)\n"

            details = {
                'Strategy': trade.get('strategy', 'Manual'),
                'Order ID': trade.get('order_id', 'N/A')
            }

            self.send_alert(title, message, 'info', 'trading', details)

        except Exception as e:
            logger.error(f"Error sending trade alert: {e}")

    def send_position_alert(self, position: Dict, action: str):
        """Send alert for position changes"""
        try:
            symbol = position.get('symbol', 'Unknown')

            if action == 'opened':
                title = f"Position Opened: {symbol}"
                level = 'info'
            elif action == 'closed':
                title = f"Position Closed: {symbol}"
                level = 'info'
            elif action == 'stop_loss':
                title = f"Stop Loss Hit: {symbol}"
                level = 'warning'
            elif action == 'take_profit':
                title = f"Take Profit Hit: {symbol}"
                level = 'info'
            else:
                title = f"Position Update: {symbol}"
                level = 'info'

            message = f"Position {action} for {symbol}\n"
            message += f"Entry: ${position.get('entry_price', 0):.6f}\n"
            message += f"Current: ${position.get('current_price', 0):.6f}\n"
            message += f"P&L: ${position.get('unrealized_pnl', 0):.6f}\n"

            self.send_alert(title, message, level, 'position')

        except Exception as e:
            logger.error(f"Error sending position alert: {e}")

    def send_risk_alert(self, risk_type: str, details: Dict):
        """Send risk management alert"""
        try:
            level_map = {
                'daily_loss': 'critical',
                'drawdown': 'critical',
                'exposure': 'warning',
                'consecutive_losses': 'warning',
                'volatility': 'warning'
            }

            level = level_map.get(risk_type, 'warning')

            if risk_type == 'daily_loss':
                title = "Daily Loss Limit Reached"
                message = f"Daily loss: ${abs(details.get('loss', 0)):.6f}"
            elif risk_type == 'drawdown':
                title = "Maximum Drawdown Exceeded"
                message = f"Current drawdown: {details.get('drawdown', 0):.2f}%"
            elif risk_type == 'exposure':
                title = "High Exposure Warning"
                message = f"Current exposure: ${details.get('exposure', 0):.6f}"
            elif risk_type == 'consecutive_losses':
                title = "Consecutive Losses Alert"
                message = f"Consecutive losses: {details.get('count', 0)}"
            else:
                title = f"Risk Alert: {risk_type}"
                message = str(details)

            self.send_alert(title, message, level, 'risk', details)

        except Exception as e:
            logger.error(f"Error sending risk alert: {e}")

    def send_system_alert(self, system_type: str, message: str, level: str = 'error'):
        """Send system-related alert"""
        try:
            title_map = {
                'api_error': 'API Connection Error',
                'database_error': 'Database Error',
                'strategy_error': 'Strategy Execution Error',
                'websocket_error': 'WebSocket Connection Error',
                'startup': 'Bot Started',
                'shutdown': 'Bot Stopped',
                'crash': 'Bot Crashed'
            }

            title = title_map.get(system_type, f'System Alert: {system_type}')
            self.send_alert(title, message, level, 'system')

        except Exception as e:
            logger.error(f"Error sending system alert: {e}")

    def send_performance_summary(self, metrics: Dict):
        """Send daily performance summary"""
        try:
            title = "Daily Performance Summary"

            message = "📊 Trading Performance Summary\n\n"
            message += f"Total Trades: {metrics.get('total_trades', 0)}\n"
            message += f"Winning Trades: {metrics.get('winning_trades', 0)}\n"
            message += f"Win Rate: {metrics.get('win_rate', 0):.1f}%\n"
            message += f"Total P&L: ${metrics.get('total_pnl', 0):.6f}\n"
            message += f"Best Trade: ${metrics.get('best_trade', 0):.6f}\n"
            message += f"Worst Trade: ${metrics.get('worst_trade', 0):.6f}\n"
            message += f"Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%\n"

            self.send_alert(title, message, 'info', 'performance', metrics)

        except Exception as e:
            logger.error(f"Error sending performance summary: {e}")

    # ====================
    # ALERT MANAGEMENT
    # ====================

    def get_recent_alerts(self, limit: int = 50) -> List[Alert]:
        """Get recent alerts from database"""
        try:
            return db_manager.get_unacknowledged_alerts()[:limit]
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Acknowledge an alert"""
        try:
            # Update in database
            # ... implementation ...
            return True
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")
            return False

    def test_alerts(self):
        """Test all alert channels"""
        test_message = "This is a test alert from Kraken Trading Bot"

        results = {
            'email': False,
            'telegram': False,
            'discord': False
        }

        if self.email_enabled:
            results['email'] = self._send_email_alert("Test Alert", test_message, 'info')

        if self.telegram_enabled:
            results['telegram'] = self._send_telegram_alert(test_message, 'info')

        if self.discord_enabled:
            results['discord'] = self._send_discord_alert(test_message, 'info')

        logger.info(f"Alert test results: {results}")
        return results