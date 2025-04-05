import logging
import ccxt
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import traceback
from uniswap_interface import UniswapV3Interface

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    timestamp: int = 0

class RateLimiter:
    """
    Simple rate limiter to prevent hitting exchange API limits
    """
    def __init__(self, max_calls_per_second=5):
        self.max_calls_per_second = max_calls_per_second
        self.call_timestamps = []
    
    async def wait(self):
        """Wait if we've made too many calls recently"""
        now = time.time()
        # Remove timestamps older than 1 second
        self.call_timestamps = [ts for ts in self.call_timestamps if now - ts < 1]
        
        if len(self.call_timestamps) >= self.max_calls_per_second:
            # Need to wait until we can make another call
            sleep_time = 1 - (now - self.call_timestamps[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        # Record this call
        self.call_timestamps.append(time.time())

class ExchangeScanner:
    """
    Scans multiple exchanges for price differences to identify arbitrage opportunities
    """
    
    def __init__(self, db):
        """Initialize the scanner with database access"""
        self.db = db
        self.exchanges = {}
        self.rate_limiters = {}
        self.default_symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT"]
        self.exchange_instances = {}
        
        # Initialize Uniswap V3 interface
        try:
            self.uniswap = UniswapV3Interface(db=self.db)
            logger.info("Uniswap V3 interface initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Uniswap V3 interface: {str(e)}")
            self.uniswap = None
            
        logger.info("ExchangeScanner initialized")
    
    def _initialize_exchange(self, exchange_config):
        """Initialize an exchange connection"""
        exchange_id = exchange_config.exchange_name
        
        # Check if we have already initialized this exchange
        if exchange_id in self.exchange_instances:
            return self.exchange_instances[exchange_id]
        
        # Initialize the exchange
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange_params = {}
            
            # Add API credentials if available
            if exchange_config.api_key and exchange_config.api_secret:
                exchange_params['apiKey'] = exchange_config.api_key
                exchange_params['secret'] = exchange_config.api_secret
            
            # Additional common settings
            exchange_params['enableRateLimit'] = True
            
            # Create exchange instance
            exchange = exchange_class(exchange_params)
            self.exchange_instances[exchange_id] = exchange
            self.rate_limiters[exchange_id] = RateLimiter()
            
            logger.info(f"Initialized exchange: {exchange_id}")
            return exchange
        
        except Exception as e:
            logger.error(f"Failed to initialize exchange {exchange_id}: {str(e)}")
            return None
    
    async def _fetch_ticker(self, exchange, symbol):
        """Fetch ticker data for a symbol from an exchange with rate limiting"""
        try:
            # Apply rate limiting
            await self.rate_limiters[exchange.id].wait()
            
            # Fetch ticker
            ticker = await exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol} from {exchange.id}: {str(e)}")
            return None
    
    def get_token_pair_symbol(self, token_pair):
        """Convert a TokenPair database object to a ccxt symbol format"""
        return f"{token_pair.base_token}/{token_pair.quote_token}"
    
    def get_uniswap_prices(self, symbols_to_check):
        """
        Get price data from Uniswap V3 for the specified symbols
        
        Args:
            symbols_to_check: List of symbols to check prices for
            
        Returns:
            Dictionary containing price data for the symbols
        """
        if not self.uniswap:
            logger.warning("Uniswap V3 interface not initialized")
            return {}
            
        uniswap_prices = {}
        current_timestamp = int(time.time() * 1000)  # Current time in milliseconds
        
        # Check which symbols are supported by Uniswap
        supported_pairs = self.uniswap.get_exchange_data().get('supported_pairs', [])
        
        for symbol in symbols_to_check:
            if symbol in supported_pairs:
                try:
                    price = self.uniswap.get_token_pair_price(symbol)
                    if price:
                        uniswap_prices[symbol] = {
                            'price': price,
                            # For Uniswap, we don't have separate bid/ask so use price for both
                            'bid': price,
                            'ask': price,
                            # We don't have volume data from our simple implementation
                            'volume': 0,
                            'timestamp': current_timestamp
                        }
                        logger.info(f"Got Uniswap V3 price for {symbol}: {price}")
                except Exception as e:
                    logger.error(f"Error getting Uniswap price for {symbol}: {str(e)}")
        
        return uniswap_prices
        
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
        
        try:
            # Initialize exchanges if needed
            active_exchanges = []
            for config in exchange_configs:
                if not config.is_active:
                    continue
                
                exchange = self._initialize_exchange(config)
                if exchange:
                    active_exchanges.append(exchange)
            
            # If we don't have enough exchanges, we can't find arbitrage opportunities
            if len(active_exchanges) < 1:  # Changed from 2 to 1 since we'll add Uniswap
                logger.warning(f"Not enough active exchanges. Need at least 1, got {len(active_exchanges)}")
                return []
            
            # Use default symbols if no token pairs are configured
            symbols_to_check = []
            if token_pairs:
                for pair in token_pairs:
                    if pair.is_active:
                        symbol = f"{pair.base_token}/{pair.quote_token}"
                        symbols_to_check.append(symbol)
            
            if not symbols_to_check:
                symbols_to_check = self.default_symbols
                logger.warning(f"No token pairs configured, using default symbols: {symbols_to_check}")
            
            # Collect price data from all exchanges
            exchange_prices = {}
            
            # For now, use synchronous calls for simplicity
            for exchange in active_exchanges:
                exchange_prices[exchange.id] = {}
                
                for symbol in symbols_to_check:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        if ticker and 'last' in ticker and ticker['last']:
                            exchange_prices[exchange.id][symbol] = {
                                'price': ticker['last'],
                                'bid': ticker.get('bid', 0),
                                'ask': ticker.get('ask', 0),
                                'volume': ticker.get('quoteVolume', 0),
                                'timestamp': ticker.get('timestamp', 0)
                            }
                    except Exception as e:
                        logger.error(f"Error fetching {symbol} from {exchange.id}: {str(e)}")
                        continue
                        
            # Add Uniswap V3 prices if available
            if self.uniswap:
                uniswap_prices = self.get_uniswap_prices(symbols_to_check)
                if uniswap_prices:
                    exchange_prices['uniswap_v3'] = uniswap_prices
            
            # Find arbitrage opportunities across exchanges
            for symbol in symbols_to_check:
                # Get all prices for this symbol across exchanges
                prices_by_exchange = []
                
                for exchange_id, symbols in exchange_prices.items():
                    if symbol in symbols:
                        prices_by_exchange.append((
                            exchange_id,
                            symbols[symbol]['price'],
                            symbols[symbol]['volume'],
                            symbols[symbol]['timestamp']
                        ))
                
                # Sort by price
                prices_by_exchange.sort(key=lambda x: x[1])
                
                # Check if we have at least two exchanges with prices
                if len(prices_by_exchange) < 2:
                    continue
                
                # Get the lowest and highest prices
                lowest = prices_by_exchange[0]
                highest = prices_by_exchange[-1]
                
                # Calculate the price difference
                buy_exchange, buy_price, buy_volume, buy_timestamp = lowest
                sell_exchange, sell_price, sell_volume, sell_timestamp = highest
                
                price_diff = sell_price - buy_price
                if buy_price <= 0:
                    continue  # Avoid division by zero
                
                price_diff_percentage = (price_diff / buy_price) * 100
                
                # Create opportunity object
                # Handle case where one of the timestamps might be None
                if buy_timestamp is None and sell_timestamp is None:
                    current_timestamp = int(time.time() * 1000)  # Current time in milliseconds
                    timestamp = current_timestamp
                elif buy_timestamp is None:
                    timestamp = sell_timestamp
                elif sell_timestamp is None:
                    timestamp = buy_timestamp
                else:
                    timestamp = max(buy_timestamp, sell_timestamp)
                
                opportunity = OpportunityData(
                    token_pair=symbol,
                    buy_exchange=buy_exchange,
                    sell_exchange=sell_exchange,
                    buy_price=buy_price,
                    sell_price=sell_price,
                    price_difference=price_diff,
                    price_difference_percentage=price_diff_percentage,
                    buy_volume=buy_volume,
                    sell_volume=sell_volume,
                    timestamp=timestamp
                )
                
                opportunities.append(opportunity)
                
                logger.info(f"Found opportunity: {symbol} - Buy on {buy_exchange} at {buy_price:.2f}, "
                            f"Sell on {sell_exchange} at {sell_price:.2f}, "
                            f"Difference: {price_diff_percentage:.2f}%")
            
        except Exception as e:
            logger.error(f"Error in scan_exchanges: {str(e)}")
            logger.error(traceback.format_exc())
        
        return opportunities
