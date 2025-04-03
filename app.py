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
from models import ArbitrageOpportunity, ExchangeConfig, TokenPair, Settings
from exchange_scanner import ExchangeScanner
from profit_calculator import ProfitCalculator
from blockchain_interface import BlockchainInterface

# Initialize components
scanner = None
profit_calculator = None
blockchain_interface = None
scan_thread = None
stop_scan = False

def initialize_components():
    """Initialize the main components of the arbitrage bot"""
    global scanner, profit_calculator, blockchain_interface
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Load settings
        settings = Settings.query.first()
        if not settings:
            settings = Settings(
                scan_interval=3,
                min_profit_threshold=0.5,
                gas_price_limit=100,
                alert_on_opportunities=True,
                use_flashloans=False
            )
            db.session.add(settings)
            db.session.commit()
        
        # Initialize components with settings
        scanner = ExchangeScanner(db)
        profit_calculator = ProfitCalculator()
        blockchain_interface = BlockchainInterface()

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
                
                if exchange_configs and token_pairs:
                    # Scan exchanges for price differences
                    opportunities = scanner.scan_exchanges(exchange_configs, token_pairs)
                    
                    # Calculate profits for each opportunity
                    for opportunity in opportunities:
                        calculated_opportunity = profit_calculator.calculate_profit(opportunity)
                        
                        # Save profitable opportunities to database
                        if calculated_opportunity.estimated_profit_percentage >= settings.min_profit_threshold:
                            new_opportunity = ArbitrageOpportunity(
                                token_pair=calculated_opportunity.token_pair,
                                buy_exchange=calculated_opportunity.buy_exchange,
                                sell_exchange=calculated_opportunity.sell_exchange,
                                buy_price=calculated_opportunity.buy_price,
                                sell_price=calculated_opportunity.sell_price,
                                price_difference=calculated_opportunity.price_difference,
                                price_difference_percentage=calculated_opportunity.price_difference_percentage,
                                estimated_profit=calculated_opportunity.estimated_profit,
                                estimated_profit_percentage=calculated_opportunity.estimated_profit_percentage,
                                gas_cost_estimate=calculated_opportunity.gas_cost_estimate,
                                exchange_fee_estimate=calculated_opportunity.exchange_fee_estimate,
                                flashloan_fee_estimate=calculated_opportunity.flashloan_fee_estimate,
                                execution_status="pending",
                                timestamp=datetime.utcnow()
                            )
                            db.session.add(new_opportunity)
                            db.session.commit()
                            logger.info(f"New profitable opportunity found: {new_opportunity.token_pair} with {new_opportunity.estimated_profit_percentage:.2f}% profit")
                
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
            settings.gas_price_limit = int(request.form.get('gas_price_limit', 100))
            settings.alert_on_opportunities = 'alert_on_opportunities' in request.form
            settings.use_flashloans = 'use_flashloans' in request.form
            
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
        'estimated_profit_percentage': float(opp.estimated_profit_percentage),
        'execution_status': opp.execution_status,
        'timestamp': opp.timestamp.isoformat()
    } for opp in opportunities])

@app.route('/api/exchanges')
def api_exchanges():
    """Return list of available exchanges from CCXT"""
    try:
        exchanges = ccxt.exchanges
        return jsonify(exchanges)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def api_settings():
    try:
        data = request.json
        settings = Settings.query.first()
        
        if 'scan_interval' in data:
            settings.scan_interval = float(data['scan_interval'])
        if 'min_profit_threshold' in data:
            settings.min_profit_threshold = float(data['min_profit_threshold'])
        if 'gas_price_limit' in data:
            settings.gas_price_limit = int(data['gas_price_limit'])
        if 'alert_on_opportunities' in data:
            settings.alert_on_opportunities = bool(data['alert_on_opportunities'])
        if 'use_flashloans' in data:
            settings.use_flashloans = bool(data['use_flashloans'])
        
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/exchange_config', methods=['POST'])
def api_exchange_config():
    try:
        data = request.json
        exchange_name = data.get('exchange_name')
        
        if not exchange_name:
            return jsonify({'status': 'error', 'message': 'Exchange name is required'}), 400
        
        # Check if config already exists
        config = ExchangeConfig.query.filter_by(exchange_name=exchange_name).first()
        
        if not config:
            config = ExchangeConfig(
                exchange_name=exchange_name,
                api_key=data.get('api_key', ''),
                api_secret=data.get('api_secret', ''),
                additional_params=json.dumps(data.get('additional_params', {})),
                is_active=data.get('is_active', True)
            )
            db.session.add(config)
        else:
            config.api_key = data.get('api_key', config.api_key)
            config.api_secret = data.get('api_secret', config.api_secret)
            config.additional_params = json.dumps(data.get('additional_params', json.loads(config.additional_params)))
            config.is_active = data.get('is_active', config.is_active)
        
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/token_pair', methods=['POST'])
def api_token_pair():
    try:
        data = request.json
        base_token = data.get('base_token')
        quote_token = data.get('quote_token')
        
        if not base_token or not quote_token:
            return jsonify({'status': 'error', 'message': 'Base and quote tokens are required'}), 400
        
        # Check if pair already exists
        pair = TokenPair.query.filter_by(base_token=base_token, quote_token=quote_token).first()
        
        if not pair:
            pair = TokenPair(
                base_token=base_token,
                quote_token=quote_token,
                min_order_size=data.get('min_order_size', 0.01),
                is_active=data.get('is_active', True)
            )
            db.session.add(pair)
        else:
            pair.min_order_size = data.get('min_order_size', pair.min_order_size)
            pair.is_active = data.get('is_active', pair.is_active)
        
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/execute_trade/<int:opportunity_id>')
def execute_trade(opportunity_id):
    try:
        opportunity = ArbitrageOpportunity.query.get(opportunity_id)
        if not opportunity:
            return jsonify({'status': 'error', 'message': 'Opportunity not found'}), 404
        
        if opportunity.execution_status != 'pending':
            return jsonify({'status': 'error', 'message': f'Opportunity already {opportunity.execution_status}'}), 400
        
        # Update status to processing
        opportunity.execution_status = 'processing'
        db.session.commit()
        
        # Execute the trade (this would be a background task in production)
        settings = Settings.query.first()
        
        if settings.use_flashloans:
            # Use blockchain interface to execute flashloan trade
            result = blockchain_interface.execute_flashloan_trade(opportunity)
        else:
            # Use blockchain interface to execute regular trade
            result = blockchain_interface.execute_trade(opportunity)
        
        if result['status'] == 'success':
            opportunity.execution_status = 'completed'
            opportunity.transaction_hash = result.get('transaction_hash')
            opportunity.actual_profit = result.get('actual_profit')
            flash('Trade executed successfully!', 'success')
        else:
            opportunity.execution_status = 'failed'
            opportunity.failure_reason = result.get('message')
            flash(f'Trade execution failed: {result.get("message")}', 'danger')
        
        db.session.commit()
        return jsonify({'status': 'success', 'redirect': url_for('opportunities')})
    except Exception as e:
        logger.error(f"Error executing trade: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/scanner/start')
def api_start_scanner():
    start_scanner()
    return jsonify({'status': 'success', 'message': 'Scanner started'})

@app.route('/api/scanner/stop')
def api_stop_scanner():
    stop_scanner()
    return jsonify({'status': 'success', 'message': 'Scanner stopped'})
