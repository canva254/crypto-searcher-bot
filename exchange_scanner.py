import logging
import ccxt
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class OpportunityData:
    """Data class to hold arbitrage opportunity information"""
    token_pair: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    price_difference: float
    price_difference_percentage: float
    estimated_profit: float = 0.0
    estimated_profit_percentage: float = 0.0
    gas_cost_estimate: float = 0.0
    exchange_fee_estimate: float = 0.0
    flashloan_fee_estimate: float = 0.0

class ExchangeScanner:
    """
    Scans multiple exchanges for price differences to identify arbitrage opportunities
    """
    
    def __init__(self, db):
        """Initialize the scanner with database access"""
        self.db = db
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        logger.info("ExchangeScanner initialized")
    
    def _initialize_exchange(self, exchange_config):
        """Initialize an exchange with configuration from the database"""
        try:
            exchange_id = exchange_config.exchange_name
            
            # Check if exchange is supported by ccxt
            if exchange_id not in ccxt.exchanges:
                logger.error(f"Exchange {exchange_id} not supported by ccxt")
                return None
            
            # Create exchange instance
            exchange_class = getattr(ccxt, exchange_id)
            
            # Configure exchange with API keys if available
            config = {}
            if exchange_config.api_key and exchange_config.api_secret:
                config['apiKey'] = exchange_config.api_key
                config['secret'] = exchange_config.api_secret
            
            # Add any additional parameters
            if exchange_config.additional_params:
                import json
                additional_params = json.loads(exchange_config.additional_params)
                config.update(additional_params)
            
            exchange = exchange_class(config)
            
            # Set up rate limiting to be safe
            exchange.enableRateLimit = True
            
            logger.info(f"Initialized exchange: {exchange_id}")
            return exchange
            
        except Exception as e:
            logger.error(f"Error initializing exchange {exchange_config.exchange_name}: {str(e)}")
            return None
    
    def scan_exchanges(self, exchange_configs, token_pairs):
        """
        Scan all active exchanges for price differences on specified token pairs
        
        Args:
            exchange_configs: List of ExchangeConfig objects from the database
            token_pairs: List of TokenPair objects from the database
            
        Returns:
            List of OpportunityData objects representing potential arbitrage opportunities
        """
        opportunities = []
        
        # In demo mode, generate simulated opportunities to demonstrate the app
        # In a real implementation, this would fetch actual exchange data
        
        # Check if we have token pairs and exchanges configured
        if not token_pairs or not exchange_configs:
            # Generate demo data with common crypto pairs if no configuration exists
            symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT"]
            exchanges = ["binance", "coinbase", "kraken", "huobi", "kucoin"]
            
            import random
            # Generate a few random opportunities with realistic price variations
            for symbol in symbols:
                # Create a realistic base price for each symbol
                if symbol.startswith("BTC"):
                    base_price = random.uniform(60000, 70000)
                elif symbol.startswith("ETH"):
                    base_price = random.uniform(3000, 4000)
                elif symbol.startswith("BNB"):
                    base_price = random.uniform(500, 650)
                elif symbol.startswith("SOL"):
                    base_price = random.uniform(150, 200)
                else:
                    base_price = random.uniform(0.5, 2.5)
                
                # Pick two different exchanges
                buy_exchange, sell_exchange = random.sample(exchanges, 2)
                
                # Create price difference (0.1% to 2%)
                diff_percent = random.uniform(0.1, 2.0)
                buy_price = base_price
                sell_price = buy_price * (1 + diff_percent/100)
                
                # Create opportunity
                opportunity = OpportunityData(
                    token_pair=symbol,
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    buy_price=buy_price,
                    sell_price=sell_price,
                    price_difference=sell_price - buy_price,
                    price_difference_percentage=diff_percent
                )
                opportunities.append(opportunity)
                
            logger.info(f"Generated {len(opportunities)} demo opportunities")
            return opportunities
            
        # Initialize exchanges if needed
        for config in exchange_configs:
            if config.exchange_name not in self.exchanges:
                exchange = self._initialize_exchange(config)
                if exchange:
                    self.exchanges[config.exchange_name] = exchange
        
        # Prepare pairs in ccxt format
        ccxt_pairs = {}
        for pair in token_pairs:
            symbol = f"{pair.base_token}/{pair.quote_token}"
            ccxt_pairs[pair.id] = symbol
        
        # Fetch ticker data from all exchanges
        ticker_data = {}
        for exchange_name, exchange in self.exchanges.items():
            ticker_data[exchange_name] = {}
            
            try:
                # Load markets first to ensure symbols are recognized
                exchange.load_markets()
                
                for pair_id, symbol in ccxt_pairs.items():
                    # Check if the exchange supports this symbol
                    if symbol in exchange.symbols:
                        try:
                            ticker = exchange.fetch_ticker(symbol)
                            ticker_data[exchange_name][symbol] = {
                                'bid': ticker['bid'],  # Highest buy price
                                'ask': ticker['ask'],  # Lowest sell price
                                'timestamp': ticker['timestamp']
                            }
                            logger.debug(f"Fetched {symbol} from {exchange_name}: bid={ticker['bid']}, ask={ticker['ask']}")
                        except Exception as e:
                            logger.error(f"Error fetching {symbol} from {exchange_name}: {str(e)}")
                    else:
                        logger.debug(f"Exchange {exchange_name} does not support {symbol}")
            
            except Exception as e:
                logger.error(f"Error processing exchange {exchange_name}: {str(e)}")
        
        # Compare prices across exchanges to find arbitrage opportunities
        for pair_id, symbol in ccxt_pairs.items():
            # Find all exchanges that have data for this symbol
            exchanges_with_symbol = [
                ex_name for ex_name in ticker_data.keys() 
                if symbol in ticker_data[ex_name]
            ]
            
            if len(exchanges_with_symbol) < 2:
                # Need at least 2 exchanges to compare
                continue
                
            # Find best buy (lowest ask) and best sell (highest bid) prices
            best_buy = {'exchange': None, 'price': float('inf')}
            best_sell = {'exchange': None, 'price': 0}
            
            for exchange_name in exchanges_with_symbol:
                ask_price = ticker_data[exchange_name][symbol]['ask']
                bid_price = ticker_data[exchange_name][symbol]['bid']
                
                if ask_price and ask_price < best_buy['price']:
                    best_buy = {'exchange': exchange_name, 'price': ask_price}
                
                if bid_price and bid_price > best_sell['price']:
                    best_sell = {'exchange': exchange_name, 'price': bid_price}
            
            # Check if there's a profitable opportunity (sell price > buy price)
            if best_sell['price'] > best_buy['price'] and best_buy['exchange'] != best_sell['exchange']:
                price_difference = best_sell['price'] - best_buy['price']
                price_difference_percentage = (price_difference / best_buy['price']) * 100
                
                opportunity = OpportunityData(
                    token_pair=symbol,
                    buy_exchange=best_buy['exchange'],
                    sell_exchange=best_sell['exchange'],
                    buy_price=best_buy['price'],
                    sell_price=best_sell['price'],
                    price_difference=price_difference,
                    price_difference_percentage=price_difference_percentage
                )
                
                opportunities.append(opportunity)
                logger.info(f"Found opportunity: {symbol} - Buy on {best_buy['exchange']} at {best_buy['price']}, "
                            f"Sell on {best_sell['exchange']} at {best_sell['price']}, "
                            f"Difference: {price_difference_percentage:.2f}%")
        
        return opportunities
