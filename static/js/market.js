document.addEventListener('DOMContentLoaded', function() {
    // Load initial market data
    loadSpotPrices();
    loadLiquidityPools();
    loadArbitrageOpportunities();
    setupGasFeeMonitor();
    setupSlippageCalculator();
    
    // Setup tab filtering for exchanges
    setupExchangeTabFiltering();
    
    // Set up periodic data refreshing
    setInterval(loadSpotPrices, 10000); // Every 10 seconds
    setInterval(loadLiquidityPools, 30000); // Every 30 seconds
    setInterval(loadArbitrageOpportunities, 5000); // Every 5 seconds
    setInterval(updateGasFeeMonitor, 60000); // Every minute
});

// Format currency with appropriate formatting
function formatCurrency(value, decimals = 2) {
    if (value === null || value === undefined) return '$0.00';
    
    // For larger numbers (like BTC), use fewer decimal places
    if (value > 1000) {
        decimals = 2;
    } else if (value > 100) {
        decimals = 3;
    } else {
        decimals = 4;
    }
    
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

// Format a percentage value
function formatPercentage(value, decimals = 2) {
    if (value === null || value === undefined) return '0.00%';
    return `${parseFloat(value).toFixed(decimals)}%`;
}

// Format large numbers with K, M, B suffixes
function formatLargeNumber(value) {
    if (value === null || value === undefined) return '0';
    
    if (value >= 1000000000) {
        return `$${(value / 1000000000).toFixed(2)}B`;
    } else if (value >= 1000000) {
        return `$${(value / 1000000).toFixed(2)}M`;
    } else if (value >= 1000) {
        return `$${(value / 1000).toFixed(2)}K`;
    } else {
        return `$${value.toFixed(2)}`;
    }
}

// Generate crypto icon based on symbol
function getCryptoIcon(symbol) {
    const iconMap = {
        'BTC': '<i class="bi bi-currency-bitcoin text-warning"></i>',
        'ETH': '<i class="bi bi-currency-exchange text-primary"></i>',
        'UNI': '<i class="bi bi-reception-4 text-danger"></i>',
        'LINK': '<i class="bi bi-link-45deg text-info"></i>',
        'SOL': '<i class="bi bi-sun text-success"></i>',
        'ADA': '<i class="bi bi-hexagon text-primary"></i>',
        'BNB': '<i class="bi bi-currency-dollar text-warning"></i>'
    };
    
    return iconMap[symbol] || '<i class="bi bi-coin text-secondary"></i>';
}

// Get price change class based on value
function getPriceChangeClass(change) {
    if (change > 0) return 'text-success';
    if (change < 0) return 'text-danger';
    return 'text-secondary';
}

// Determine icon for price change
function getPriceChangeIcon(change) {
    if (change > 0) return '<i class="bi bi-arrow-up-right"></i>';
    if (change < 0) return '<i class="bi bi-arrow-down-right"></i>';
    return '<i class="bi bi-dash"></i>';
}

// Load spot prices from API
async function loadSpotPrices() {
    try {
        // Get token prices from both regular exchanges and Uniswap
        const exchangeResponse = await fetch('/api/configured_token_pairs');
        const pairData = await exchangeResponse.json();
        
        const spotPricesContainer = document.getElementById('spot-prices');
        spotPricesContainer.innerHTML = '';
        
        // Sample data structure for development - in production this would come from the API
        const cryptoData = [
            { symbol: 'BTC', name: 'Bitcoin', price: 83004.50, change: 0.72 },
            { symbol: 'ETH', name: 'Ethereum', price: 1789.43, change: 1.27 },
            { symbol: 'BNB', name: 'Binance Coin', price: 593.38, change: 0.53 },
            { symbol: 'SOL', name: 'Solana', price: 117.97, change: 5.43 },
            { symbol: 'ADA', name: 'Cardano', price: 0.65, change: 0.53 }
        ];
        
        // Create cards for each crypto
        cryptoData.forEach(crypto => {
            const priceChangeClass = getPriceChangeClass(crypto.change);
            const priceChangeIcon = getPriceChangeIcon(crypto.change);
            
            const card = document.createElement('div');
            card.className = 'col-md-4 col-lg-2-4';
            card.innerHTML = `
                <div class="card spot-price-card">
                    <div class="card-body py-3">
                        <div class="d-flex align-items-center">
                            <div class="crypto-icon me-2">
                                ${getCryptoIcon(crypto.symbol)}
                            </div>
                            <div>
                                <h4 class="fw-bold mb-0">${crypto.symbol}</h4>
                                <small class="text-secondary">${crypto.name}</small>
                            </div>
                            <div class="ms-auto">
                                <span class="price-change ${priceChangeClass}">
                                    ${priceChangeIcon} ${formatPercentage(crypto.change)}
                                </span>
                            </div>
                        </div>
                        <h3 class="mt-2 mb-0 price-value">${formatCurrency(crypto.price)}</h3>
                    </div>
                </div>
            `;
            
            spotPricesContainer.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading spot prices:', error);
    }
}

// Load liquidity pools data
async function loadLiquidityPools() {
    try {
        // This would be replaced with actual API calls to get liquidity pool data
        const uniswapResponse = await fetch('/api/uniswap/details?token_pair=ETH-USDT');
        const uniswapData = { pools: [] };
        
        try {
            const data = await uniswapResponse.json();
            if (data && data.success) {
                uniswapData.pools = data.pools || [];
            }
        } catch (e) {
            console.warn('Could not parse Uniswap data', e);
        }
        
        const liquidityPoolsTable = document.getElementById('liquidity-pools-table');
        
        // Sample data structure - in production this would come from the API
        const poolsData = [
            { 
                name: 'ETH/USDC', 
                exchange: 'Uniswap', 
                tvl: 45678983, 
                volume24h: 12345678, 
                apy: 4.23,
                reserves: '12,900.45 ETH<br>43,250,000.00 USDC',
                type: 'uniswap'
            },
            { 
                name: 'WBTC/ETH', 
                exchange: 'Uniswap', 
                tvl: 32456789, 
                volume24h: 9876543, 
                apy: 3.87,
                reserves: '421.35 WBTC<br>6,250.78 ETH',
                type: 'uniswap'
            },
            { 
                name: 'UNI/ETH', 
                exchange: 'Uniswap', 
                tvl: 8765432, 
                volume24h: 2345678, 
                apy: 7.65,
                reserves: '450,000.00 UNI<br>1,245.67 ETH',
                type: 'uniswap'
            },
            { 
                name: 'BTC/USDT', 
                exchange: 'Coinbase', 
                tvl: 56789012, 
                volume24h: 23456789, 
                apy: 2.12,
                reserves: '684.32 BTC<br>56,789,450.00 USDT',
                type: 'coinbase'
            },
            { 
                name: 'ETH/USDT', 
                exchange: 'Kraken', 
                tvl: 34567890, 
                volume24h: 12345678, 
                apy: 1.98,
                reserves: '18,976.56 ETH<br>33,897,654.00 USDT',
                type: 'kraken'
            },
            { 
                name: 'SOL/USDT', 
                exchange: 'KuCoin', 
                tvl: 12345678, 
                volume24h: 5678901, 
                apy: 3.45,
                reserves: '104,567.89 SOL<br>12,345,678.00 USDT',
                type: 'kucoin'
            }
        ];
        
        // Add any Uniswap pools from the API response
        if (uniswapData.pools && uniswapData.pools.length > 0) {
            uniswapData.pools.forEach(pool => {
                poolsData.push({
                    name: pool.name || 'Unknown',
                    exchange: 'Uniswap',
                    tvl: pool.tvl || 0,
                    volume24h: pool.volume24h || 0,
                    apy: pool.apy || 0,
                    reserves: pool.reserves || '',
                    type: 'uniswap'
                });
            });
        }
        
        // Create the table rows
        liquidityPoolsTable.innerHTML = '';
        if (poolsData.length === 0) {
            liquidityPoolsTable.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-3">No liquidity pools found</td>
                </tr>
            `;
            return;
        }
        
        poolsData.forEach(pool => {
            const apyClass = pool.apy > 5 ? 'text-success' : (pool.apy > 3 ? 'text-primary' : 'text-secondary');
            
            const row = document.createElement('tr');
            row.className = `exchange-row ${pool.type}`;
            row.innerHTML = `
                <td>
                    <span class="d-block fw-bold">${pool.name}</span>
                </td>
                <td>
                    <span class="badge exchange-badge ${pool.type}">${pool.exchange}</span>
                </td>
                <td>${formatLargeNumber(pool.tvl)}</td>
                <td>${formatLargeNumber(pool.volume24h)}</td>
                <td class="${apyClass}">${formatPercentage(pool.apy)}</td>
                <td class="small">${pool.reserves}</td>
            `;
            
            liquidityPoolsTable.appendChild(row);
        });
        
        // Update the data info
        document.getElementById('data-update-info').innerHTML = `
            Data updated
            <div>Fetched ${cryptoCount(poolsData)} tokens and ${poolsData.length} liquidity pools</div>
        `;
    } catch (error) {
        console.error('Error loading liquidity pools:', error);
    }
}

// Count unique crypto tokens in pools
function cryptoCount(pools) {
    const uniqueTokens = new Set();
    pools.forEach(pool => {
        const tokens = pool.name.split('/');
        tokens.forEach(token => uniqueTokens.add(token));
    });
    return uniqueTokens.size;
}

// Setup exchange tab filtering
function setupExchangeTabFiltering() {
    const tabButtons = document.querySelectorAll('.exchange-tabs button');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));
            
            // Add active class to clicked button
            this.classList.add('active');
            
            // Get exchange filter value
            const exchange = this.getAttribute('data-exchange');
            
            // Filter rows
            const rows = document.querySelectorAll('.exchange-row');
            rows.forEach(row => {
                if (exchange === 'all') {
                    row.style.display = '';
                } else if (row.classList.contains(exchange)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });
}

// Load arbitrage opportunities
async function loadArbitrageOpportunities() {
    try {
        const response = await fetch('/api/opportunities');
        const opportunities = await response.json();
        
        const opportunitiesTable = document.getElementById('arbitrage-opportunities');
        
        // If no opportunities, show a message
        if (!opportunities || opportunities.length === 0) {
            opportunitiesTable.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-3">No arbitrage opportunities found</td>
                </tr>
            `;
            document.getElementById('opportunities-count').innerText = '0';
            return;
        }
        
        // Update the counter
        document.getElementById('opportunities-count').innerText = opportunities.length;
        
        // Display opportunities
        opportunitiesTable.innerHTML = '';
        opportunities.forEach(opp => {
            const row = document.createElement('tr');
            
            // Calculate some estimated values (these would come from the API in production)
            const tradeAmount = 1.0; // Example 1 ETH or 1 BTC
            const estimatedProfit = opp.price_difference_percentage * tradeAmount / 100;
            
            row.innerHTML = `
                <td>
                    <div class="d-flex align-items-center">
                        ${getCryptoIcon(opp.token_pair.split('/')[0])}
                        <span class="ms-2">${opp.token_pair}</span>
                    </div>
                </td>
                <td>
                    <span class="badge bg-secondary">${opp.buy_exchange}</span>
                    <span class="ms-1">${formatCurrency(opp.buy_price)}</span>
                </td>
                <td>
                    <span class="badge bg-secondary">${opp.sell_exchange}</span>
                    <span class="ms-1">${formatCurrency(opp.sell_price)}</span>
                </td>
                <td class="text-success">${formatPercentage(opp.price_difference_percentage)}</td>
                <td>${formatCurrency(estimatedProfit)}</td>
                <td>
                    <button class="btn btn-sm btn-success" onclick="executeTrade(${opp.id})">
                        Execute
                    </button>
                </td>
            `;
            
            opportunitiesTable.appendChild(row);
        });
    } catch (error) {
        console.error('Error loading arbitrage opportunities:', error);
    }
}

// Setup gas fee monitor display
function setupGasFeeMonitor() {
    updateGasFeeMonitor();
}

// Update gas fee data
async function updateGasFeeMonitor() {
    try {
        // In production, fetch this data from a real endpoint
        // For demo, we'll use sample data
        const gasFastValue = 35;
        const gasAverageValue = 25;
        const gasSlowValue = 18;
        const maxGas = 50; // For scaling the progress bars
        
        // Update values
        document.getElementById('gas-fast').innerText = `${gasFastValue} gwei`;
        document.getElementById('gas-average').innerText = `${gasAverageValue} gwei`;
        document.getElementById('gas-slow').innerText = `${gasSlowValue} gwei`;
        
        // Update progress bars
        document.getElementById('gas-fast-bar').style.width = `${(gasFastValue / maxGas) * 100}%`;
        document.getElementById('gas-average-bar').style.width = `${(gasAverageValue / maxGas) * 100}%`;
        document.getElementById('gas-slow-bar').style.width = `${(gasSlowValue / maxGas) * 100}%`;
        
        // Update last updated time
        const now = new Date();
        document.getElementById('gas-update-time').innerText = `Last updated: ${now.toLocaleTimeString()}`;
    } catch (error) {
        console.error('Error updating gas fees:', error);
    }
}

// Setup slippage calculator
function setupSlippageCalculator() {
    const tradeAmountInput = document.getElementById('trade-amount');
    const slippageToleranceInput = document.getElementById('slippage-tolerance');
    const slippageValueDisplay = document.getElementById('slippage-value');
    
    // Initial calculation
    calculateSlippage();
    
    // Event listeners for inputs
    tradeAmountInput.addEventListener('input', calculateSlippage);
    slippageToleranceInput.addEventListener('input', function() {
        slippageValueDisplay.innerText = `${this.value}%`;
        calculateSlippage();
    });
}

// Calculate slippage and price impact
function calculateSlippage() {
    const tradeAmount = parseFloat(document.getElementById('trade-amount').value) || 1;
    const slippageTolerance = parseFloat(document.getElementById('slippage-tolerance').value) || 0.5;
    
    // Example calculation (in production would use real market data)
    const ethPrice = 1790.85; // Example ETH price
    const expectedOutput = tradeAmount * ethPrice;
    const priceImpact = (0.1 * tradeAmount * 12); // Example formula: higher trade amounts have higher impact
    const minimumReceived = expectedOutput * (1 - slippageTolerance / 100);
    
    // Update UI
    document.getElementById('expected-output').innerText = formatCurrency(expectedOutput);
    document.getElementById('minimum-received').innerText = formatCurrency(minimumReceived);
    document.getElementById('price-impact').innerText = formatPercentage(priceImpact);
    
    // Change color of price impact based on severity
    const priceImpactElement = document.getElementById('price-impact');
    if (priceImpact < 1) {
        priceImpactElement.className = 'col-5 text-end text-success';
    } else if (priceImpact < 5) {
        priceImpactElement.className = 'col-5 text-end text-warning';
    } else {
        priceImpactElement.className = 'col-5 text-end text-danger';
    }
}

// Execute a trade (placeholder function)
async function executeTrade(opportunityId) {
    // In production, this would call an API endpoint to execute the trade
    alert(`Trade execution requested for opportunity ID: ${opportunityId}`);
}
