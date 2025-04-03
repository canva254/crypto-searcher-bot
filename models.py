from app import db
from datetime import datetime
from sqlalchemy import Float, String, Boolean, Integer, DateTime, Text, JSON

class ArbitrageOpportunity(db.Model):
    """Represents an arbitrage opportunity found by the scanner"""
    id = db.Column(db.Integer, primary_key=True)
    token_pair = db.Column(db.String(20), nullable=False)
    buy_exchange = db.Column(db.String(50), nullable=False)
    sell_exchange = db.Column(db.String(50), nullable=False)
    buy_price = db.Column(db.Float, nullable=False)
    sell_price = db.Column(db.Float, nullable=False)
    price_difference = db.Column(db.Float, nullable=False)
    price_difference_percentage = db.Column(db.Float, nullable=False)
    estimated_profit = db.Column(db.Float, nullable=False)
    estimated_profit_percentage = db.Column(db.Float, nullable=False)
    gas_cost_estimate = db.Column(db.Float, nullable=True)
    exchange_fee_estimate = db.Column(db.Float, nullable=True)
    flashloan_fee_estimate = db.Column(db.Float, nullable=True)
    execution_status = db.Column(db.String(20), default="pending")  # pending, processing, completed, failed
    transaction_hash = db.Column(db.String(100), nullable=True)
    actual_profit = db.Column(db.Float, nullable=True)
    failure_reason = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ArbitrageOpportunity {self.token_pair}: {self.buy_exchange}->{self.sell_exchange}, {self.estimated_profit_percentage}%>"

class ExchangeConfig(db.Model):
    """Configuration for cryptocurrency exchanges"""
    id = db.Column(db.Integer, primary_key=True)
    exchange_name = db.Column(db.String(50), unique=True, nullable=False)
    api_key = db.Column(db.String(100), nullable=True)
    api_secret = db.Column(db.String(100), nullable=True)
    additional_params = db.Column(db.Text, default="{}")  # Stored as JSON
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ExchangeConfig {self.exchange_name}>"

class TokenPair(db.Model):
    """Trading pairs to monitor for arbitrage"""
    id = db.Column(db.Integer, primary_key=True)
    base_token = db.Column(db.String(10), nullable=False)
    quote_token = db.Column(db.String(10), nullable=False)
    min_order_size = db.Column(db.Float, default=0.01)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('base_token', 'quote_token', name='_base_quote_pair_uc'),)

    def __repr__(self):
        return f"<TokenPair {self.base_token}/{self.quote_token}>"

class Settings(db.Model):
    """Global settings for the arbitrage bot"""
    id = db.Column(db.Integer, primary_key=True)
    scan_interval = db.Column(db.Float, default=3.0)  # in seconds
    min_profit_threshold = db.Column(db.Float, default=0.5)  # in percentage
    gas_price_limit = db.Column(db.Integer, default=100)  # in gwei
    alert_on_opportunities = db.Column(db.Boolean, default=True)
    use_flashloans = db.Column(db.Boolean, default=False)
    wallet_address = db.Column(db.String(42), nullable=True)  # Ethereum wallet address
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Settings scan_interval={self.scan_interval}s min_profit={self.min_profit_threshold}%>"
