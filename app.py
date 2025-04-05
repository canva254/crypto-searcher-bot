import os
import json
import logging
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import ccxt

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create database base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Configure database
database_url = os.environ.get("DATABASE_URL")
# Fix for SQLAlchemy 1.4+ compatibility with Postgres
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///arbitrage.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Import modules after app creation to avoid circular imports
from models import ArbitrageOpportunity, ExchangeConfig, TokenPair, Settings, UniswapConfig
from exchange_scanner import ExchangeScanner

# Initialize components
scanner = None
scan_thread = None
stop_scan = False

def initialize_components():
    """Initialize the main components of the arbitrage bot"""
    global scanner
    
    with app.app_context():
        # Recreate the database schema
        db.drop_all()
        db.create_all()
        
        # Load settings
        settings = Settings.query.first()
        if not settings:
            settings = Settings(
                scan_interval=3,
                min_profit_threshold=0.5
            )
            db.session.add(settings)
        
        # Add default exchange configs if none exist
        exchange_count = ExchangeConfig.query.count()
        if exchange_count == 0:
            logger.info("Adding default exchange configurations")
            default_exchanges = [
                ExchangeConfig(exchange_name="binance", is_active=True),
                ExchangeConfig(exchange_name="coinbase", is_active=True),
                ExchangeConfig(exchange_name="kraken", is_active=True),
                ExchangeConfig(exchange_name="kucoin", is_active=True),
                ExchangeConfig(exchange_name="huobi", is_active=True)
            ]
            for exchange in default_exchanges:
                db.session.add(exchange)
        
        # Add default token pairs if none exist
        token_pair_count = TokenPair.query.count()
        if token_pair_count == 0:
            logger.info("Adding default token pairs")
            default_pairs = [
                TokenPair(base_token="BTC", quote_token="USDT", is_active=True),
                TokenPair(base_token="ETH", quote_token="USDT", is_active=True),
                TokenPair(base_token="BNB", quote_token="USDT", is_active=True),
                TokenPair(base_token="SOL", quote_token="USDT", is_active=True),
                TokenPair(base_token="ADA", quote_token="USDT", is_active=True)
            ]
            for pair in default_pairs:
                db.session.add(pair)
        
        # Add default Uniswap config if none exists
        uniswap_config = UniswapConfig.query.first()
        if not uniswap_config:
            logger.info("Adding default Uniswap V3 configuration")
            # Use the default Infura endpoint for development
            uniswap_config = UniswapConfig(
                rpc_url="https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161",
                is_active=True
            )
            db.session.add(uniswap_config)
        
        db.session.commit()
        
        # Initialize scanner
        scanner = ExchangeScanner(db)

def scan_for_opportunities():
    """Background task to continuously scan for arbitrage opportunities"""
    global stop_scan
    
    while not stop_scan:
        try:
            with app.app_context():
                settings = Settings.query.first()
                scan_interval = settings.scan_interval if settings else 3
                
                # Get active exchange pairs
                exchange_configs = ExchangeConfig.query.filter_by(is_active=True).all()
                token_pairs = TokenPair.query.filter_by(is_active=True).all()
                
                # Scan exchanges for price differences
                opportunities = scanner.scan_exchanges(exchange_configs, token_pairs)
                
                # Save opportunities to database
                for opportunity in opportunities:
                    # Check if opportunity meets minimum threshold
                    if opportunity.price_difference_percentage >= settings.min_profit_threshold:
                        # Delete older opportunities to prevent database growth
                        # Keep only the most recent 100 records
                        count = ArbitrageOpportunity.query.count()
                        if count > 100:
                            old_records = ArbitrageOpportunity.query.order_by(
                                ArbitrageOpportunity.timestamp.asc()
                            ).limit(count - 100).all()
                            for record in old_records:
                                db.session.delete(record)
                        
                        new_opportunity = ArbitrageOpportunity(
                            token_pair=opportunity.token_pair,
                            buy_exchange=opportunity.buy_exchange,
                            sell_exchange=opportunity.sell_exchange,
                            buy_price=opportunity.buy_price,
                            sell_price=opportunity.sell_price,
                            price_difference=opportunity.price_difference,
                            price_difference_percentage=opportunity.price_difference_percentage,
                            timestamp=datetime.utcnow()
                        )
                        db.session.add(new_opportunity)
                
                db.session.commit()
                logger.info(f"Scan complete. Found {len(opportunities)} opportunities.")
                
                # Sleep for the configured interval
                time.sleep(scan_interval)
        except Exception as e:
            logger.error(f"Error in scan thread: {str(e)}")
            time.sleep(3)  # Sleep on error to prevent CPU spinning

def start_scanner():
    """Start the background scanner thread"""
    global scan_thread, stop_scan
    
    if scan_thread is not None and scan_thread.is_alive():
        logger.info("Scanner already running")
        return
    
    logger.info("Starting scanner thread")
    stop_scan = False
    scan_thread = threading.Thread(target=scan_for_opportunities)
    scan_thread.daemon = True
    scan_thread.start()

def stop_scanner():
    """Stop the background scanner thread"""
    global stop_scan
    logger.info("Stopping scanner thread")
    stop_scan = True

# Initialize components when app starts
with app.app_context():
    initialize_components()
    start_scanner()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/opportunities')
def opportunities():
    opportunities = ArbitrageOpportunity.query.order_by(ArbitrageOpportunity.timestamp.desc()).limit(50).all()
    return render_template('opportunities.html', opportunities=opportunities)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if request.method == 'POST':
        try:
            settings = Settings.query.first()
            if not settings:
                settings = Settings()
                db.session.add(settings)
            
            settings.scan_interval = float(request.form.get('scan_interval', 3))
            settings.min_profit_threshold = float(request.form.get('min_profit_threshold', 0.5))
            
            db.session.commit()
            flash('Settings updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'danger')
        
        return redirect(url_for('settings'))
    
    settings = Settings.query.first()
    exchange_configs = ExchangeConfig.query.all()
    token_pairs = TokenPair.query.all()
    
    return render_template('settings.html', 
                          settings=settings, 
                          exchange_configs=exchange_configs,
                          token_pairs=token_pairs)

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Get or update application settings"""
    if request.method == 'POST':
        try:
            data = request.json
            settings = Settings.query.first()
            
            if not settings:
                settings = Settings()
                db.session.add(settings)
            
            if 'scan_interval' in data:
                settings.scan_interval = float(data['scan_interval'])
            
            if 'min_profit_threshold' in data:
                settings.min_profit_threshold = float(data['min_profit_threshold'])
            
            db.session.commit()
            logger.info("Settings updated via API")
            
            return jsonify({
                'status': 'success',
                'message': 'Settings updated successfully',
                'settings': {
                    'scan_interval': settings.scan_interval,
                    'min_profit_threshold': settings.min_profit_threshold
                }
            })
        except Exception as e:
            logger.error(f"Error updating settings via API: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 400
    
    # GET request
    settings = Settings.query.first()
    
    if not settings:
        return jsonify({
            'status': 'success',
            'settings': {
                'scan_interval': 3.0,
                'min_profit_threshold': 0.5
            }
        })
    
    return jsonify({
        'status': 'success',
        'settings': {
            'scan_interval': settings.scan_interval,
            'min_profit_threshold': settings.min_profit_threshold
        }
    })

@app.route('/api/opportunities')
def api_opportunities():
    opportunities = ArbitrageOpportunity.query.order_by(ArbitrageOpportunity.timestamp.desc()).limit(20).all()
    return jsonify([{
        'id': opp.id,
        'token_pair': opp.token_pair,
        'buy_exchange': opp.buy_exchange,
        'sell_exchange': opp.sell_exchange,
        'buy_price': float(opp.buy_price),
        'sell_price': float(opp.sell_price),
        'price_difference_percentage': float(opp.price_difference_percentage),
        'timestamp': opp.timestamp.isoformat()
    } for opp in opportunities])

@app.route('/api/exchanges')
def api_exchanges():
    """Return list of available exchanges from CCXT"""
    try:
        exchanges = ccxt.exchanges
        return jsonify(exchanges)
    except Exception as e:
        logger.error(f"Error getting exchanges from CCXT: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/configured_exchanges')
def api_configured_exchanges():
    """Return list of exchanges that have been configured in the system"""
    try:
        exchanges = ExchangeConfig.query.all()
        exchange_list = [{
            'id': ex.id,
            'exchange_name': ex.exchange_name,
            'is_active': ex.is_active,
            'has_api_key': bool(ex.api_key),
            'created_at': ex.created_at.isoformat() if ex.created_at else None
        } for ex in exchanges]
        
        # Add Uniswap if it's configured
        uniswap_config = UniswapConfig.query.first()
        if uniswap_config and uniswap_config.is_active:
            # Add Uniswap as a special exchange type
            exchange_list.append({
                'id': 'uniswap_v3',  # Use a fixed ID for Uniswap
                'exchange_name': 'uniswap_v3',
                'display_name': 'Uniswap V3',
                'is_active': uniswap_config.is_active,
                'has_api_key': bool(uniswap_config.rpc_url),  # Consider having RPC URL as having an "API key"
                'created_at': uniswap_config.created_at.isoformat() if uniswap_config.created_at else None
            })
            
        return jsonify(exchange_list)
    except Exception as e:
        logger.error(f"Error getting configured exchanges: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/api/configured_token_pairs')
def api_configured_token_pairs():
    """Return list of token pairs that have been configured in the system"""
    try:
        token_pairs = TokenPair.query.all()
        return jsonify([{
            'id': pair.id,
            'symbol': f"{pair.base_token}/{pair.quote_token}",
            'base_token': pair.base_token,
            'quote_token': pair.quote_token,
            'is_active': pair.is_active,
            'created_at': pair.created_at.isoformat() if pair.created_at else None
        } for pair in token_pairs])
    except Exception as e:
        logger.error(f"Error getting configured token pairs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/exchange_config', methods=['POST'])
def api_exchange_config():
    try:
        data = request.json
        exchange_name = data.get('exchange_name')
        exchange_id = data.get('id')
        
        if not exchange_name and not exchange_id:
            return jsonify({'status': 'error', 'message': 'Exchange name or ID is required'}), 400
        
        # Check if config already exists
        if exchange_id:
            config = ExchangeConfig.query.get(exchange_id)
            if not config:
                return jsonify({'status': 'error', 'message': f'Exchange with ID {exchange_id} not found'}), 404
        else:
            config = ExchangeConfig.query.filter_by(exchange_name=exchange_name).first()
        
        if not config:
            # Create new config
            config = ExchangeConfig(
                exchange_name=exchange_name,
                api_key=data.get('api_key', ''),
                api_secret=data.get('api_secret', ''),
                is_active=data.get('is_active', True)
            )
            db.session.add(config)
            logger.info(f"Created new exchange config for {exchange_name}")
        else:
            # Update existing config
            if 'api_key' in data:
                config.api_key = data.get('api_key')
            if 'api_secret' in data:
                config.api_secret = data.get('api_secret')
            if 'is_active' in data:
                config.is_active = data.get('is_active')
            
            logger.info(f"Updated exchange config for {config.exchange_name}")
        
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': f"Exchange {config.exchange_name} {'created' if exchange_id is None and not exchange_name else 'updated'} successfully",
            'exchange': {
                'id': config.id,
                'exchange_name': config.exchange_name,
                'is_active': config.is_active,
                'has_api_key': bool(config.api_key)
            }
        })
    except Exception as e:
        logger.error(f"Error in api_exchange_config: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/token_pair', methods=['POST'])
def api_token_pair():
    try:
        data = request.json
        pair_id = data.get('id')
        
        if pair_id:
            # Update existing pair
            pair = TokenPair.query.get(pair_id)
            if not pair:
                return jsonify({'status': 'error', 'message': f'Token pair with ID {pair_id} not found'}), 404
            
            if 'is_active' in data:
                pair.is_active = data.get('is_active')
            
            db.session.commit()
            logger.info(f"Updated token pair {pair.base_token}/{pair.quote_token}")
            
            return jsonify({
                'status': 'success',
                'message': f"Token pair {pair.base_token}/{pair.quote_token} updated successfully",
                'pair': {
                    'id': pair.id,
                    'base_token': pair.base_token,
                    'quote_token': pair.quote_token,
                    'is_active': pair.is_active
                }
            })
        
        # Create new pair
        base_token = data.get('base_token')
        quote_token = data.get('quote_token')
        
        if not base_token or not quote_token:
            return jsonify({'status': 'error', 'message': 'Base and quote tokens are required'}), 400
        
        # Standardize token symbols to uppercase
        base_token = base_token.upper()
        quote_token = quote_token.upper()
        
        # Check if pair already exists
        pair = TokenPair.query.filter_by(base_token=base_token, quote_token=quote_token).first()
        
        if not pair:
            # Create new pair
            pair = TokenPair(
                base_token=base_token,
                quote_token=quote_token,
                is_active=data.get('is_active', True)
            )
            db.session.add(pair)
            logger.info(f"Created new token pair {base_token}/{quote_token}")
        else:
            # Update existing pair
            pair.is_active = data.get('is_active', pair.is_active)
            logger.info(f"Updated existing token pair {base_token}/{quote_token}")
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f"Token pair {base_token}/{quote_token} {'created' if not pair else 'updated'} successfully",
            'pair': {
                'id': pair.id,
                'base_token': pair.base_token,
                'quote_token': pair.quote_token,
                'is_active': pair.is_active
            }
        })
    except Exception as e:
        logger.error(f"Error in api_token_pair: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/scanner/start')
def api_start_scanner():
    start_scanner()
    return jsonify({'status': 'success', 'message': 'Scanner started'})

@app.route('/api/scanner/stop')
def api_stop_scanner():
    stop_scanner()
    return jsonify({'status': 'success', 'message': 'Scanner stopped'})

@app.route('/api/uniswap/config', methods=['GET', 'POST'])
def api_uniswap_config():
    """Get or update Uniswap configuration"""
    if request.method == 'POST':
        try:
            data = request.json
            config = UniswapConfig.query.first()
            
            if not config:
                config = UniswapConfig()
                db.session.add(config)
            
            if 'rpc_url' in data:
                config.rpc_url = data.get('rpc_url')
            
            if 'wallet_address' in data:
                config.wallet_address = data.get('wallet_address')
                
            if 'is_active' in data:
                config.is_active = data.get('is_active')
            
            db.session.commit()
            logger.info("Uniswap configuration updated")
            
            return jsonify({
                'status': 'success',
                'message': 'Uniswap configuration updated successfully',
                'config': {
                    'id': config.id,
                    'rpc_url': config.rpc_url,
                    'wallet_address': config.wallet_address,
                    'is_active': config.is_active,
                    'created_at': config.created_at.isoformat() if config.created_at else None
                }
            })
        except Exception as e:
            logger.error(f"Error updating Uniswap configuration: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 400
    
    # GET request
    config = UniswapConfig.query.first()
    
    if not config:
        return jsonify({
            'status': 'error',
            'message': 'Uniswap configuration not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'config': {
            'id': config.id,
            'rpc_url': config.rpc_url,
            'wallet_address': config.wallet_address,
            'is_active': config.is_active,
            'created_at': config.created_at.isoformat() if config.created_at else None
        }
    })