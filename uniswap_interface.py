import os
import json
import logging
import time
from typing import Dict, Any, Optional, Tuple
from web3 import Web3
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants for Uniswap V3
UNISWAP_V3_FACTORY_ADDRESS = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
UNISWAP_V3_ROUTER_ADDRESS = "0xE592427A0AEce92De3Edee1F18E0157C05861564"

# Common token addresses
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # Wrapped ETH
USDT_ADDRESS = "0xdAC17F958D2ee523a2206206994597C13D831ec7"  # USDT
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC
DAI_ADDRESS = "0x6B175474E89094C44Da98b954EedeAC495271d0F"   # DAI
WBTC_ADDRESS = "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"  # Wrapped BTC

# Common fee tiers in Uniswap V3 (in hundredths of a bip, 1 bip = 0.01%)
FEE_LOW = 500      # 0.05%
FEE_MEDIUM = 3000  # 0.3%
FEE_HIGH = 10000   # 1%

# ABI for the Uniswap V3 Factory
FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "tokenA", "type": "address"},
            {"internalType": "address", "name": "tokenB", "type": "address"},
            {"internalType": "uint24", "name": "fee", "type": "uint24"}
        ],
        "name": "getPool",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ABI for a Uniswap V3 Pool
POOL_ABI = [
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "fee",
        "outputs": [{"internalType": "uint24", "name": "", "type": "uint24"}],
        "stateMutability": "view",
        "type": "function"
    }
]

class UniswapV3Interface:
    """
    Interface to interact with Uniswap V3 for price data and potential swaps
    """
    
    def __init__(self, db=None):
        """Initialize the Uniswap V3 interface with web3 connection"""
        try:
            # First try to get RPC URL from database if db connection is provided
            rpc_url = None
            if db:
                from models import UniswapConfig
                # Use Flask-SQLAlchemy session if provided
                try:
                    config = db.session.query(UniswapConfig).filter_by(is_active=True).first()
                    if config and config.rpc_url:
                        rpc_url = config.rpc_url
                        logger.info("Using Uniswap RPC URL from database configuration")
                except Exception as db_err:
                    logger.error(f"Error fetching Uniswap config from database: {str(db_err)}")
            
            # If no RPC URL from database, try environment variable
            if not rpc_url:
                rpc_url = os.getenv("RPC_URL")
            
            # Default to Infura if not provided elsewhere
            if not rpc_url:
                rpc_url = "https://mainnet.infura.io/v3/8f869800e73e4de2ba792d9ec67cab85"  # User's Infura key
                logger.warning("No RPC_URL found in database or .env file, using user's Infura node")
                
            self.web3 = Web3(Web3.HTTPProvider(rpc_url))
            if not self.web3.is_connected():
                logger.error("Failed to connect to Ethereum. Check your RPC provider.")
                raise ConnectionError("Cannot connect to Ethereum")
            
            # Initialize factory contract
            self.factory = self.web3.eth.contract(
                address=Web3.to_checksum_address(UNISWAP_V3_FACTORY_ADDRESS),
                abi=FACTORY_ABI
            )
            
            logger.info(f"Uniswap V3 interface initialized successfully with RPC URL: {rpc_url[:20]}...")
        except Exception as e:
            logger.error(f"Error initializing Uniswap V3 interface: {str(e)}")
            raise
    
    def get_pool_address(self, token_a: str, token_b: str, fee: int = FEE_MEDIUM) -> str:
        """
        Get the address of a Uniswap V3 pool for a pair of tokens
        
        Args:
            token_a: Address of the first token
            token_b: Address of the second token
            fee: Fee tier (500, 3000, or 10000)
            
        Returns:
            Address of the pool
        """
        try:
            # Ensure token addresses are checksummed
            token_a = Web3.to_checksum_address(token_a)
            token_b = Web3.to_checksum_address(token_b)
            
            # Sort tokens (required by Uniswap)
            if token_a.lower() > token_b.lower():
                token_a, token_b = token_b, token_a
            
            # Query the factory for the pool address
            pool_address = self.factory.functions.getPool(token_a, token_b, fee).call()
            
            # Check if pool exists
            if pool_address == "0x0000000000000000000000000000000000000000":
                logger.warning(f"No pool exists for {token_a}-{token_b} with fee {fee}")
                return None
            
            return pool_address
        except Exception as e:
            logger.error(f"Error getting pool address: {str(e)}")
            return None
    
    def get_pool_price(self, token_a: str, token_b: str, fee: int = FEE_MEDIUM) -> Optional[float]:
        """
        Get the current price from a Uniswap V3 pool
        
        Args:
            token_a: Address of the input token
            token_b: Address of the output token
            fee: Fee tier (500, 3000, or 10000)
            
        Returns:
            Current price of token_b in terms of token_a
        """
        try:
            # Get pool address
            pool_address = self.get_pool_address(token_a, token_b, fee)
            if not pool_address:
                return None
            
            # Create pool contract instance
            pool = self.web3.eth.contract(
                address=Web3.to_checksum_address(pool_address),
                abi=POOL_ABI
            )
            
            # Get token addresses from the pool to determine order
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            
            # Get current price from slot0
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            
            # Calculate price from sqrtPriceX96
            # Formula: sqrtPriceX96 = sqrt(price) * 2^96
            # So, price = (sqrtPriceX96 / 2^96)^2
            price = (sqrt_price_x96 / (2**96))**2
            
            # If token_a is token1, invert the price
            if token_a.lower() == token1.lower():
                price = 1 / price
            
            return price
        except Exception as e:
            logger.error(f"Error getting pool price: {str(e)}")
            return None
    
    def get_token_pair_price(self, symbol: str) -> Optional[float]:
        """
        Get the price for a token pair in a format compatible with the arbitrage bot
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Current price on Uniswap V3
        """
        try:
            # Parse the symbol
            tokens = symbol.split('/')
            if len(tokens) != 2:
                logger.error(f"Invalid symbol format: {symbol}")
                return None
            
            base, quote = tokens
            
            # Map to token addresses
            token_map = {
                'ETH': WETH_ADDRESS,
                'WETH': WETH_ADDRESS,
                'BTC': WBTC_ADDRESS,
                'WBTC': WBTC_ADDRESS,
                'USDT': USDT_ADDRESS,
                'USDC': USDC_ADDRESS,
                'DAI': DAI_ADDRESS
            }
            
            if base not in token_map or quote not in token_map:
                logger.warning(f"Unsupported token in {symbol}")
                return None
            
            # Get price for each fee tier and use the one with most liquidity
            # (this is a simplification, in reality you would check liquidity)
            for fee_tier in [FEE_LOW, FEE_MEDIUM, FEE_HIGH]:
                price = self.get_pool_price(token_map[base], token_map[quote], fee_tier)
                if price:
                    return price
            
            logger.warning(f"No price found for {symbol} on Uniswap V3")
            return None
        except Exception as e:
            logger.error(f"Error in get_token_pair_price: {str(e)}")
            return None
    
    def calculate_fee(self, amount: float, fee_tier: int) -> float:
        """
        Calculate the fee for a swap
        
        Args:
            amount: Amount being swapped
            fee_tier: Fee tier (500, 3000, or 10000)
            
        Returns:
            Fee amount
        """
        # Fee is in hundredths of a bip, where 1 bip = 0.01%
        fee_percentage = fee_tier / 1_000_000
        return amount * fee_percentage
    
    def get_pool_liquidity(self, token_a: str, token_b: str, fee: int = FEE_MEDIUM) -> Optional[Dict[str, Any]]:
        """
        Get liquidity information for a Uniswap V3 pool
        
        Args:
            token_a: Address of the first token
            token_b: Address of the second token
            fee: Fee tier (500, 3000, or 10000)
            
        Returns:
            Dictionary with liquidity information
        """
        try:
            # Get pool address
            pool_address = self.get_pool_address(token_a, token_b, fee)
            if not pool_address:
                return None
            
            # Create pool contract instance
            pool = self.web3.eth.contract(
                address=Web3.to_checksum_address(pool_address),
                abi=POOL_ABI
            )
            
            # Get current liquidity
            liquidity = pool.functions.liquidity().call()
            
            # Get token addresses from the pool to determine order
            token0 = pool.functions.token0().call()
            token1 = pool.functions.token1().call()
            
            # Get token symbols if possible (simplified version)
            token0_symbol = "Unknown"
            token1_symbol = "Unknown"
            
            for symbol, address in [("ETH", WETH_ADDRESS), ("WBTC", WBTC_ADDRESS), ("USDT", USDT_ADDRESS), ("USDC", USDC_ADDRESS), ("DAI", DAI_ADDRESS)]:
                if token0.lower() == address.lower():
                    token0_symbol = symbol
                if token1.lower() == address.lower():
                    token1_symbol = symbol
            
            return {
                "pool_address": pool_address,
                "liquidity": liquidity,
                "token0": {
                    "address": token0,
                    "symbol": token0_symbol
                },
                "token1": {
                    "address": token1,
                    "symbol": token1_symbol
                },
                "fee_tier": fee
            }
        except Exception as e:
            logger.error(f"Error getting pool liquidity: {str(e)}")
            return None
    
    def get_gas_price(self) -> Optional[Dict[str, float]]:
        """
        Get current gas prices from the Ethereum network
        
        Returns:
            Dictionary with gas price information in gwei
        """
        try:
            # Get gas price (Wei)
            gas_price = self.web3.eth.gas_price
            
            # Convert to gwei for easier reading
            gas_price_gwei = gas_price / 10**9
            
            # Estimate different speed prices
            return {
                "standard": gas_price_gwei,
                "fast": gas_price_gwei * 1.2,
                "rapid": gas_price_gwei * 1.5
            }
        except Exception as e:
            logger.error(f"Error getting gas prices: {str(e)}")
            return None
    
    def calculate_price_impact(self, token_in: str, token_out: str, amount_in: float, fee: int = FEE_MEDIUM) -> Optional[Dict[str, Any]]:
        """
        Calculate the estimated price impact for a swap
        
        Args:
            token_in: Address of the input token
            token_out: Address of the output token
            amount_in: Amount of the input token to swap
            fee: Fee tier (500, 3000, or 10000)
            
        Returns:
            Dictionary with price impact information
        """
        try:
            # Get the current spot price
            spot_price = self.get_pool_price(token_in, token_out, fee)
            if not spot_price:
                return None
            
            # This is a simplified estimation of price impact
            # In a real implementation, you'd use the x*y=k formula and the actual pool reserves
            
            # Calculate fee amount
            fee_percentage = fee / 1_000_000
            fee_amount = amount_in * fee_percentage
            
            # Simplified estimation of price impact based on the amount relative to pool depth
            # This is not accurate for large trades but gives a basic estimate
            pool_info = self.get_pool_liquidity(token_in, token_out, fee)
            if not pool_info:
                # If pool info is not available, provide a very rough estimate
                # Assuming 0.5% impact per 1% of pool liquidity used
                estimated_impact = 0.005  # Default 0.5% for unknown size
            else:
                # Convert liquidity to a usable metric (this is simplified)
                liquidity = pool_info["liquidity"]
                if liquidity > 0:
                    # A very rough estimation, real impact depends on many factors
                    estimated_impact = min(0.20, (amount_in / (liquidity * spot_price)) * 10)
                else:
                    estimated_impact = 0.01  # Default 1% if we can't calculate
            
            return {
                "spot_price": spot_price,
                "amount_in": amount_in,
                "estimated_fee": fee_amount,
                "estimated_price_impact_percentage": estimated_impact * 100,
                "slippage_tolerance": 0.5,  # Default 0.5% slippage tolerance
                "minimum_received": amount_in * spot_price * (1 - estimated_impact - 0.005)  # Accounting for slippage
            }
        except Exception as e:
            logger.error(f"Error calculating price impact: {str(e)}")
            return None
    
    def get_token_pair_details(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive details for a token pair including spot price, liquidity, and gas fees
        
        Args:
            symbol: Trading pair symbol (e.g., 'ETH/USDT')
            
        Returns:
            Dictionary with detailed information about the token pair
        """
        try:
            # Parse the symbol
            tokens = symbol.split('/')
            if len(tokens) != 2:
                logger.error(f"Invalid symbol format: {symbol}")
                return None
            
            base, quote = tokens
            
            # Map to token addresses
            token_map = {
                'ETH': WETH_ADDRESS,
                'WETH': WETH_ADDRESS,
                'BTC': WBTC_ADDRESS,
                'WBTC': WBTC_ADDRESS,
                'USDT': USDT_ADDRESS,
                'USDC': USDC_ADDRESS,
                'DAI': DAI_ADDRESS
            }
            
            if base not in token_map or quote not in token_map:
                logger.warning(f"Unsupported token in {symbol}")
                return None
            
            # Get token addresses
            base_address = token_map[base]
            quote_address = token_map[quote]
            
            # Get price for the best fee tier
            price = None
            fee_used = None
            pool_liquidity = None
            
            for fee_tier in [FEE_LOW, FEE_MEDIUM, FEE_HIGH]:
                current_price = self.get_pool_price(token_map[base], token_map[quote], fee_tier)
                if current_price:
                    price = current_price
                    fee_used = fee_tier
                    pool_liquidity = self.get_pool_liquidity(token_map[base], token_map[quote], fee_tier)
                    break
            
            if not price:
                logger.warning(f"No price found for {symbol} on Uniswap V3")
                return None
            
            # Get gas prices
            gas_prices = self.get_gas_price()
            
            # Calculate price impact for a standard trade size (1 unit of base token)
            price_impact = self.calculate_price_impact(base_address, quote_address, 1.0, fee_used) if fee_used else None
            
            # Combine all data
            return {
                "symbol": symbol,
                "base_token": base,
                "quote_token": quote,
                "spot_price": price,
                "fee_tier": fee_used,
                "fee_percentage": fee_used / 1_000_000 if fee_used else None,
                "pool_liquidity": pool_liquidity,
                "gas_prices": gas_prices,
                "price_impact": price_impact,
                "timestamp": int(time.time())
            }
        except Exception as e:
            logger.error(f"Error in get_token_pair_details: {str(e)}")
            return None
    
    def get_exchange_data(self) -> Dict[str, Any]:
        """
        Return information about Uniswap as an exchange for use in the arbitrage scanner
        
        Returns:
            Dictionary with exchange information
        """
        return {
            "name": "uniswap_v3",
            "display_name": "Uniswap V3",
            "url": "https://app.uniswap.org/#/swap",
            "supported_pairs": ["ETH/USDT", "ETH/USDC", "BTC/USDT", "BTC/USDC"]
        }

# Example usage
if __name__ == "__main__":
    uniswap = UniswapV3Interface()
    
    # Example to get ETH/USDT price
    eth_usdt_price = uniswap.get_token_pair_price("ETH/USDT")
    if eth_usdt_price:
        print(f"ETH/USDT price on Uniswap V3: {eth_usdt_price}")
    
    # Example to calculate fees
    amount = 1.0  # 1 ETH
    fee_amount = uniswap.calculate_fee(amount, FEE_MEDIUM)
    print(f"Fee for swapping {amount} ETH: {fee_amount} ETH")