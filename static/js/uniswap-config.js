// Load Uniswap configuration
async function loadUniswapConfig() {
    try {
        const response = await fetch('/api/uniswap/config');
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                const config = data.config;
                document.getElementById('uniswapRpcUrl').value = config.rpc_url || '';
                document.getElementById('uniswapWalletAddress').value = config.wallet_address || '';
                document.getElementById('uniswapActiveCheck').checked = config.is_active;
            }
        }
    } catch (error) {
        console.error('Error loading Uniswap configuration:', error);
    }
}

// Save Uniswap configuration
function setupUniswapConfigForm() {
    const saveBtn = document.getElementById('saveUniswapConfigBtn');
    if (saveBtn) {
        saveBtn.addEventListener('click', async function() {
            const rpcUrl = document.getElementById('uniswapRpcUrl').value;
            const walletAddress = document.getElementById('uniswapWalletAddress').value;
            const isActive = document.getElementById('uniswapActiveCheck').checked;
            
            try {
                const response = await fetch('/api/uniswap/config', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        rpc_url: rpcUrl,
                        wallet_address: walletAddress,
                        is_active: isActive
                    })
                });
                
                const data = await response.json();
                if (data.status === 'success') {
                    alert('Uniswap configuration saved successfully!');
                } else {
                    alert('Error saving Uniswap configuration: ' + data.message);
                }
            } catch (error) {
                console.error('Error saving Uniswap configuration:', error);
                alert('Error saving Uniswap configuration. See console for details.');
            }
        });
    }
}

// Initialize Uniswap config functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadUniswapConfig();
    setupUniswapConfigForm();
});