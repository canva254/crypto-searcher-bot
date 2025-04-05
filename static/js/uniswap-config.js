// uniswap-config.js - Handles the Uniswap configuration form

async function loadUniswapConfig() {
    try {
        const response = await fetch('/api/uniswap/config');
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.status === 'success' && data.config) {
                document.getElementById('rpc_url').value = data.config.rpc_url || '';
                document.getElementById('wallet_address').value = data.config.wallet_address || '';
                document.getElementById('is_active').checked = data.config.is_active || false;
            }
        } else {
            console.warn('No Uniswap configuration found or server error.');
        }
    } catch (error) {
        console.error('Error loading Uniswap configuration:', error);
    }
}

function setupUniswapConfigForm() {
    const form = document.getElementById('uniswap-config-form');
    const successAlert = document.getElementById('uniswap-success-alert');
    const errorAlert = document.getElementById('uniswap-error-alert');
    
    if (!form) return;
    
    // Load existing configuration
    loadUniswapConfig();
    
    // Handle form submission
    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        const formData = {
            rpc_url: document.getElementById('rpc_url').value,
            wallet_address: document.getElementById('wallet_address').value,
            is_active: document.getElementById('is_active').checked
        };
        
        try {
            const response = await fetch('/api/uniswap/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                // Show success message
                successAlert.classList.remove('d-none');
                errorAlert.classList.add('d-none');
                
                // Auto-hide after 3 seconds
                setTimeout(() => {
                    successAlert.classList.add('d-none');
                }, 3000);
            } else {
                // Show error message
                errorAlert.textContent = result.message || 'Failed to save Uniswap configuration';
                errorAlert.classList.remove('d-none');
                successAlert.classList.add('d-none');
            }
        } catch (error) {
            console.error('Error saving Uniswap configuration:', error);
            errorAlert.textContent = 'Network error saving Uniswap configuration';
            errorAlert.classList.remove('d-none');
            successAlert.classList.add('d-none');
        }
    });
}
