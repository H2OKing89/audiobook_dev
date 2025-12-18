/**
 * Alpine.js Bootstrap Script
 * External initialization for CSP compliance
 */

// Initialize Alpine.js when available
function initializeAlpine() {
    if (typeof Alpine !== 'undefined') {
        window.Alpine = Alpine;
        Alpine.start();
        debugLog('Alpine.js initialized successfully');
        return true;
    }
    return false;
}

// Wait for Alpine to load, with timeout
let retryCount = 0;
const maxRetries = 50; // 5 seconds max

function waitForAlpine() {
    if (initializeAlpine()) {
        return; // Success!
    }
    
    retryCount++;
    if (retryCount < maxRetries) {
        setTimeout(waitForAlpine, 100);
    } else {
        console.error('Alpine.js failed to load after 5 seconds');
    }
}

// Start waiting
waitForAlpine();
