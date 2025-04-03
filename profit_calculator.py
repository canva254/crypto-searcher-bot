import logging
from typing import Dict, Any
from dataclasses import dataclass
from exchange_scanner import OpportunityData

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class ProfitCalculator:
    """
    Calculates potential profits from arbitrage opportunities,
    taking into account transaction costs, gas fees, and exchange fees.
    """
    
    def __init__(self):
        """Initialize the profit calculator with default fee settings"""
        self.default_exchange_fee_rate = 0.001  # 0.1% per trade
        self.default_gas_cost_eth = 0.005  # Estimated ETH cost for gas
        self.default_eth_price_usd = 2000  # Fallback ETH price in USD
        self.default_flashloan_fee_rate = 0.0009  # 0.09% for flash loans
        logger.info("ProfitCalculator initialized")
    
    def get_exchange_fee(self, exchange_name: str, trade_amount: float) -> float:
        """
        Get the estimated fee for a trade on a specific exchange
        
        Args:
            exchange_name: Name of the exchange
            trade_amount: Amount of the trade in quote currency
            
        Returns:
            Estimated fee amount
        """
        # In a real implementation, this would have different fee rates per exchange
        # based on your tier level, etc.
        return trade_amount * self.default_exchange_fee_rate
    
    def get_gas_cost_estimate(self, use_flashloan: bool = False) -> float:
        """
        Estimate the gas cost for executing a trade or flashloan
        
        Args:
            use_flashloan: Whether this trade will use a flashloan
            
        Returns:
            Estimated gas cost in USD
        """
        # In a real implementation, you would query current gas prices
        # and calculate based on expected gas usage for your contracts
        multiplier = 2.0 if use_flashloan else 1.0  # Flashloans use more gas
        return self.default_gas_cost_eth * self.default_eth_price_usd * multiplier
    
    def get_flashloan_fee(self, loan_amount: float) -> float:
        """
        Calculate the fee for a flashloan
        
        Args:
            loan_amount: Amount of the flashloan in quote currency
            
        Returns:
            Fee amount for the flashloan
        """
        return loan_amount * self.default_flashloan_fee_rate
    
    def calculate_profit(self, opportunity: OpportunityData, trade_amount: float = 1.0, use_flashloan: bool = False) -> OpportunityData:
        """
        Calculate the potential profit for an arbitrage opportunity
        
        Args:
            opportunity: OpportunityData object with price information
            trade_amount: Amount to trade in base currency (default: 1.0)
            use_flashloan: Whether to use a flashloan for the trade
            
        Returns:
            Updated OpportunityData with profit calculations
        """
        # Calculate the raw profit before fees
        buy_value = trade_amount * opportunity.buy_price
        sell_value = trade_amount * opportunity.sell_price
        raw_profit = sell_value - buy_value
        
        # Calculate fees
        buy_exchange_fee = self.get_exchange_fee(opportunity.buy_exchange, buy_value)
        sell_exchange_fee = self.get_exchange_fee(opportunity.sell_exchange, sell_value)
        gas_cost = self.get_gas_cost_estimate(use_flashloan)
        
        # Calculate flashloan fee if applicable
        flashloan_fee = 0
        if use_flashloan:
            flashloan_fee = self.get_flashloan_fee(buy_value)
        
        # Calculate total costs and net profit
        total_costs = buy_exchange_fee + sell_exchange_fee + gas_cost + flashloan_fee
        net_profit = raw_profit - total_costs
        
        # Calculate profit percentage relative to the trade amount
        profit_percentage = (net_profit / buy_value) * 100
        
        # Update the opportunity with calculated values
        opportunity.estimated_profit = net_profit
        opportunity.estimated_profit_percentage = profit_percentage
        opportunity.gas_cost_estimate = gas_cost
        opportunity.exchange_fee_estimate = buy_exchange_fee + sell_exchange_fee
        opportunity.flashloan_fee_estimate = flashloan_fee
        
        logger.debug(f"Calculated profit for {opportunity.token_pair}: {net_profit:.4f} ({profit_percentage:.2f}%)")
        
        return opportunity
