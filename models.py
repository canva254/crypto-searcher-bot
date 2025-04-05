from app import db
from datetime import datetime
from sqlalchemy import Float, String, Boolean, Integer, DateTime, Text

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
    # Add any other fields that are present in the existing schema
    estimated_profit = db.Column(db.Float, nullable=True)
    trade_amount = db.Column(db.Float, nullable=True)
    gas_cost = db.Column(db.Float, nullable=True)
    exchange_fees = db.Column(db.Float, nullable=True)
    net_profit = db.Column(db.Float, nullable=True)
    execution_status = db.Column(db.String(20), nullable=True)
    transaction_hash = db.Column(db.String(100), nullable=True)
    execution_time = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ArbitrageOpportunity {self.token_pair}: {self.buy_exchange}->{self.sell_exchange}, {self.price_difference_percentage:.2f}%>"

class ExchangeConfig(db.Model):
    """Configuration for cryptocurrency exchanges"""
    id = db.Column(db.Integer, primary_key=True)
    exchange_name = db.Column(db.String(50), unique=True, nullable=False)
    api_key = db.Column(db.String(100), nullable=True)
    api_secret = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ExchangeConfig {self.exchange_name}>"

class TokenPair(db.Model):
    """Trading pairs to monitor for arbitrage"""
    id = db.Column(db.Integer, primary_key=True)
    base_token = db.Column(db.String(10), nullable=False)
    quote_token = db.Column(db.String(10), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('base_token', 'quote_token', name='_base_quote_pair_uc'),)

    def __repr__(self):
        return f"<TokenPair {self.base_token}/{self.quote_token}>"

class Settings(db.Model):
    """Global settings for the arbitrage bot"""
    id = db.Column(db.Integer, primary_key=True)
    scan_interval = db.Column(db.Float, default=3.0)  # in seconds
    min_profit_threshold = db.Column(db.Float, default=0.5)  # in percentage

    def __repr__(self):
        return f"<Settings scan_interval={self.scan_interval}s min_profit={self.min_profit_threshold}%>"
        
class UniswapConfig(db.Model):
    """Configuration for Uniswap V3 integration"""
    id = db.Column(db.Integer, primary_key=True)
    rpc_url = db.Column(db.String(255), nullable=True)
    wallet_address = db.Column(db.String(42), nullable=True)  # Ethereum address is 42 chars (0x + 40 hex chars)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<UniswapConfig id={self.id} active={self.is_active}>"
