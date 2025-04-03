// Main JavaScript file for the Crypto Arbitrage Bot

// Global variables
let opportunities = [];
let lastAlertTime = 0;
const MIN_ALERT_INTERVAL = 30000; // 30 seconds between alerts

// Utility function to format currency
function formatCurrency(value) {
    return '$' + parseFloat(value).toFixed(2);
}

// Utility function to format percentage
function formatPercentage(value) {
    return parseFloat(value).toFixed(2) + '%';
}

// Function to get current settings
async function getSettings() {
    try {
        const response = await fetch('/api/settings');
        if (response.ok) {
            return await response.json();
        }
        return null;
    } catch (error) {
        console.error('Error fetching settings:', error);
        return null;
    }
}

// Function to check if we should show an alert for a new opportunity
function shouldAlertForOpportunity(opportunity, settings) {
    // Don't alert if alerts are disabled in settings
    if (settings && !settings.alert_on_opportunities) {
        return false;
    }
    
    // Don't alert if opportunity is below threshold
    if (opportunity.estimated_profit_percentage < settings.min_profit_threshold) {
        return false;
    }
    
    // Don't alert if we've alerted recently
    const now = Date.now();
    if (now - lastAlertTime < MIN_ALERT_INTERVAL) {
        return false;
    }
    
    // Don't alert if this is not a pending opportunity
    if (opportunity.execution_status !== 'pending') {
        return false;
    }
    
    return true;
}

// Function to show desktop notification for new opportunities
function showNotification(opportunity) {
    // Update last alert time
    lastAlertTime = Date.now();
    
    // Check if browser supports notifications
    if (!("Notification" in window)) {
        console.warn("This browser does not support desktop notifications");
        return;
    }
    
    // Check if notification permission is granted
    if (Notification.permission === "granted") {
        createNotification(opportunity);
    } 
    // Check if permission is not denied
    else if (Notification.permission !== "denied") {
        Notification.requestPermission().then(function (permission) {
            if (permission === "granted") {
                createNotification(opportunity);
            }
        });
    }
}

// Create notification with opportunity details
function createNotification(opportunity) {
    const title = "Arbitrage Opportunity";
    const options = {
        body: `${opportunity.token_pair}: Buy on ${opportunity.buy_exchange}, Sell on ${opportunity.sell_exchange}, Profit: ${formatPercentage(opportunity.estimated_profit_percentage)}`,
        icon: "https://cdn-icons-png.flaticon.com/512/5232/5232944.png"
    };
    
    const notification = new Notification(title, options);
    
    notification.onclick = function() {
        window.focus();
        window.location.href = `/opportunities`;
    };
}

// Function to execute a trade for a specific opportunity
async function executeTrade(opportunityId) {
    try {
        const response = await fetch(`/api/execute_trade/${opportunityId}`);
        const data = await response.json();
        
        if (data.status === 'success') {
            alert('Trade execution initiated!');
            location.reload();
        } else {
            alert(`Error executing trade: ${data.message}`);
        }
    } catch (error) {
        console.error('Error executing trade:', error);
        alert('Error executing trade. Check console for details.');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Check notification permission on page load
    if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
        Notification.requestPermission();
    }
    
    // Request permission for notifications on first click/interaction
    document.body.addEventListener('click', function() {
        if ("Notification" in window && Notification.permission !== "granted" && Notification.permission !== "denied") {
            Notification.requestPermission();
        }
    }, { once: true });
});
