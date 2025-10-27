"""
Database Models and Schema for Kraken Trading Bot
"""
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, Text, Index, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import NullPool
from flask_sqlalchemy import SQLAlchemy
from loguru import logger

import config

# Initialize SQLAlchemy
db = SQLAlchemy()
Base = declarative_base()

# ====================
# Database Models
# ====================

class Trade(db.Model):
    """Trade execution records"""
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True)
    order_id = Column(String(100), unique=True, nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY/SELL
    order_type = Column(String(20), nullable=False)  # MARKET/LIMIT/STOP
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)

    # PnL Tracking
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)

    # Strategy Info
    strategy = Column(String(50))
    strategy_signal = Column(JSON)  # Store signal details

    # Status
    status = Column(String(20), default='pending')  # pending/filled/cancelled/failed
    filled_at = Column(DateTime)

    # Risk Management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    trailing_stop = Column(Float)

    # Metadata
    exchange = Column(String(20), default='kraken')
    is_paper = Column(Boolean, default=False)
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for performance
    __table_args__ = (
        Index('idx_trades_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_trades_strategy', 'strategy'),
        Index('idx_trades_status', 'status'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'price': self.price,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'strategy': self.strategy,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class Position(db.Model):
    """Open position tracking"""
    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, unique=True)
    side = Column(String(10), nullable=False)  # long/short

    # Position Details
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    quantity = Column(Float, nullable=False)
    notional_value = Column(Float)

    # PnL Tracking
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_percentage = Column(Float, default=0.0)

    # Risk Management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    liquidation_price = Column(Float)
    margin_used = Column(Float, default=0.0)
    leverage = Column(Integer, default=1)

    # Strategy
    strategy = Column(String(50))
    entry_signal = Column(JSON)

    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Related trades
    trades = relationship("Trade", backref="position", lazy="dynamic",
                         foreign_keys=[Trade.id])

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'quantity': self.quantity,
            'unrealized_pnl': self.unrealized_pnl,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'strategy': self.strategy,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None
        }


class BotStatus(db.Model):
    """Bot operational status and state"""
    __tablename__ = 'bot_status'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)

    # Status
    is_running = Column(Boolean, default=False)
    is_paper_trading = Column(Boolean, default=True)
    start_time = Column(DateTime)
    stop_time = Column(DateTime)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)

    # Configuration
    enabled_strategies = Column(JSON)
    trading_pairs = Column(JSON)
    risk_settings = Column(JSON)

    # Performance Summary
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)

    # Current State
    open_positions = Column(Integer, default=0)
    pending_orders = Column(Integer, default=0)
    current_balance = Column(Float)

    # Metadata
    version = Column(String(20))
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)


class PerformanceMetrics(db.Model):
    """Performance tracking and analytics"""
    __tablename__ = 'performance_metrics'

    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), nullable=False)

    # Time Period
    period_type = Column(String(20))  # hourly/daily/weekly/monthly
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Trading Metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    # PnL Metrics
    gross_pnl = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    best_trade = Column(Float, default=0.0)
    worst_trade = Column(Float, default=0.0)
    average_win = Column(Float, default=0.0)
    average_loss = Column(Float, default=0.0)

    # Risk Metrics
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    calmar_ratio = Column(Float)
    profit_factor = Column(Float)

    # Volume Metrics
    total_volume = Column(Float, default=0.0)
    average_trade_size = Column(Float, default=0.0)

    # Strategy Breakdown
    strategy_performance = Column(JSON)  # Performance by strategy
    pair_performance = Column(JSON)  # Performance by trading pair

    # Portfolio Metrics
    starting_balance = Column(Float)
    ending_balance = Column(Float)
    roi = Column(Float, default=0.0)

    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_metrics_session_period', 'session_id', 'period_type', 'period_start'),
    )


class Signal(db.Model):
    """Trading signals generated by strategies"""
    __tablename__ = 'signals'

    id = Column(Integer, primary_key=True)
    strategy = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)

    # Signal Details
    action = Column(String(10), nullable=False)  # BUY/SELL/HOLD
    strength = Column(Float)  # 0-1 signal strength
    confidence = Column(Float)  # 0-1 confidence level

    # Price Levels
    entry_price = Column(Float)
    target_price = Column(Float)
    stop_price = Column(Float)

    # Indicators
    indicators = Column(JSON)  # Store indicator values
    reason = Column(Text)  # Human-readable reason

    # Execution
    executed = Column(Boolean, default=False)
    execution_time = Column(DateTime)
    execution_price = Column(Float)

    # Results
    result = Column(String(20))  # profit/loss/cancelled
    pnl = Column(Float)

    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_signals_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_signals_strategy_executed', 'strategy', 'executed'),
    )


class Alert(db.Model):
    """System alerts and notifications"""
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)  # info/warning/error/critical
    category = Column(String(50))  # trading/risk/system/strategy

    # Alert Content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON)

    # Status
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)

    # Notification Status
    email_sent = Column(Boolean, default=False)
    telegram_sent = Column(Boolean, default=False)
    discord_sent = Column(Boolean, default=False)

    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_alerts_level_acknowledged', 'level', 'acknowledged'),
        Index('idx_alerts_timestamp', 'timestamp'),
    )


class BacktestResult(db.Model):
    """Backtest results storage"""
    __tablename__ = 'backtest_results'

    id = Column(Integer, primary_key=True)
    strategy = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)

    # Backtest Parameters
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Float, nullable=False)
    parameters = Column(JSON)  # Strategy parameters used

    # Results
    final_balance = Column(Float)
    total_return = Column(Float)
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Float)

    # Risk Metrics
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)

    # Trade Statistics
    average_trade = Column(Float)
    best_trade = Column(Float)
    worst_trade = Column(Float)
    average_win = Column(Float)
    average_loss = Column(Float)
    profit_factor = Column(Float)

    # Trade Details
    trades = Column(JSON)  # List of all trades
    equity_curve = Column(JSON)  # Equity curve data

    timestamp = Column(DateTime, default=datetime.utcnow)


class OrderBook(db.Model):
    """Order book snapshots for analysis"""
    __tablename__ = 'orderbook'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)

    # Bid/Ask Data
    best_bid = Column(Float)
    best_ask = Column(Float)
    bid_volume = Column(Float)
    ask_volume = Column(Float)
    spread = Column(Float)

    # Depth
    bids = Column(JSON)  # Top N bids
    asks = Column(JSON)  # Top N asks

    # Market Metrics
    imbalance = Column(Float)  # Order book imbalance
    depth_weighted_mid = Column(Float)

    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_orderbook_symbol_timestamp', 'symbol', 'timestamp'),
    )


class SystemLog(db.Model):
    """System operation logs"""
    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False)  # DEBUG/INFO/WARNING/ERROR/CRITICAL
    logger = Column(String(100))

    # Log Content
    message = Column(Text, nullable=False)
    exception = Column(Text)
    traceback = Column(Text)

    # Context
    module = Column(String(100))
    function = Column(String(100))
    line_number = Column(Integer)

    # Additional Data
    extra_data = Column(JSON)

    timestamp = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_logs_level_timestamp', 'level', 'timestamp'),
    )


# ====================
# Database Functions
# ====================

class DatabaseManager:
    """Database management and operations"""

    def __init__(self):
        self.engine = None
        self.Session = None

    def init_database(self):
        """Initialize database connection and create tables"""
        try:
            # Create engine
            self.engine = create_engine(
                config.DATABASE_URL,
                pool_size=config.DB_POOL_SIZE,
                pool_recycle=config.DB_POOL_RECYCLE,
                poolclass=NullPool
            )

            # Create session factory
            self.Session = scoped_session(sessionmaker(bind=self.engine))

            # Create all tables
            Base.metadata.create_all(self.engine)
            db.create_all()

            logger.info("Database initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            return False

    def get_session(self):
        """Get database session"""
        if not self.Session:
            self.init_database()
        return self.Session()

    def close_session(self, session):
        """Close database session"""
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing session: {e}")

    # ====================
    # Trade Operations
    # ====================

    def record_trade(self, trade_data: Dict) -> Optional[Trade]:
        """Record a new trade"""
        session = self.get_session()
        try:
            trade = Trade(**trade_data)
            session.add(trade)
            session.commit()
            logger.info(f"Trade recorded: {trade.order_id}")
            return trade
        except Exception as e:
            session.rollback()
            logger.error(f"Error recording trade: {e}")
            return None
        finally:
            self.close_session(session)

    def get_recent_trades(self, limit: int = 100, symbol: Optional[str] = None) -> List[Trade]:
        """Get recent trades"""
        session = self.get_session()
        try:
            query = session.query(Trade)
            if symbol:
                query = query.filter_by(symbol=symbol)
            trades = query.order_by(Trade.timestamp.desc()).limit(limit).all()
            return trades
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return []
        finally:
            self.close_session(session)

    # ====================
    # Position Operations
    # ====================

    def update_position(self, symbol: str, position_data: Dict) -> bool:
        """Update or create position"""
        session = self.get_session()
        try:
            position = session.query(Position).filter_by(symbol=symbol).first()

            if position:
                for key, value in position_data.items():
                    setattr(position, key, value)
            else:
                position = Position(symbol=symbol, **position_data)
                session.add(position)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating position: {e}")
            return False
        finally:
            self.close_session(session)

    def close_position(self, symbol: str) -> bool:
        """Close a position"""
        session = self.get_session()
        try:
            position = session.query(Position).filter_by(symbol=symbol).first()
            if position:
                session.delete(position)
                session.commit()
                logger.info(f"Position closed: {symbol}")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error closing position: {e}")
            return False
        finally:
            self.close_session(session)

    # ====================
    # Performance Operations
    # ====================

    def calculate_performance_metrics(self, session_id: str, period: str = 'daily') -> Dict:
        """Calculate performance metrics for a period"""
        session = self.get_session()
        try:
            # Get trades for the period
            trades = session.query(Trade).filter(
                Trade.timestamp >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).all()

            if not trades:
                return {}

            # Calculate metrics
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.pnl > 0)
            losing_trades = sum(1 for t in trades if t.pnl < 0)

            metrics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
                'gross_pnl': sum(t.pnl for t in trades),
                'net_pnl': sum(t.pnl - t.fee for t in trades),
                'total_fees': sum(t.fee for t in trades),
                'best_trade': max((t.pnl for t in trades), default=0),
                'worst_trade': min((t.pnl for t in trades), default=0)
            }

            # Save metrics
            perf_metrics = PerformanceMetrics(
                session_id=session_id,
                period_type=period,
                period_start=datetime.utcnow().replace(hour=0, minute=0, second=0),
                period_end=datetime.utcnow(),
                **metrics
            )
            session.add(perf_metrics)
            session.commit()

            return metrics

        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}
        finally:
            self.close_session(session)

    # ====================
    # Alert Operations
    # ====================

    def create_alert(self, level: str, title: str, message: str,
                    category: Optional[str] = None) -> bool:
        """Create a new alert"""
        session = self.get_session()
        try:
            alert = Alert(
                level=level,
                title=title,
                message=message,
                category=category
            )
            session.add(alert)
            session.commit()
            logger.info(f"Alert created: {title}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating alert: {e}")
            return False
        finally:
            self.close_session(session)

    def get_unacknowledged_alerts(self) -> List[Alert]:
        """Get unacknowledged alerts"""
        session = self.get_session()
        try:
            alerts = session.query(Alert).filter_by(acknowledged=False).all()
            return alerts
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
        finally:
            self.close_session(session)


# Initialize database manager
db_manager = DatabaseManager()