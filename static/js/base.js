/**
 * Base JavaScript functionality for the Audiobook Approval System
 * Shared utilities and common functionality across all pages
 */

// Global utilities and helpers

// Debug helper - set window.DEBUG=true in browser console to enable debug logs
window.DEBUG = window.DEBUG || false;
function debugLog(...args) {
    if (window.DEBUG) console.log(...args);
}

// Expose debug helper on AudiobookApp for modules

const AudiobookApp = {
    // Auto-close countdown functionality
    startAutoCloseCountdown: function(seconds) {
        const countdownElement = document.getElementById('countdown');
        if (!countdownElement) return;
        
        let remainingSeconds = seconds;
        
        function updateCountdown() {
            countdownElement.textContent = remainingSeconds;
            if (remainingSeconds <= 0) {
                window.close();
            } else {
                remainingSeconds--;
                setTimeout(updateCountdown, 1000);
            }
        }
        
        updateCountdown();
    },

    // Copy to clipboard utility
    copyToClipboard: function(text, successCallback) {
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(successCallback);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            try {
                document.execCommand('copy');
                successCallback();
            } catch (err) {
                console.warn('Fallback copy failed:', err);
            }
            document.body.removeChild(textArea);
        }
    },

    // Initialize common features across all pages
    init: function() {
        // Initialize copy buttons if present
        const copyButtons = document.querySelectorAll('.copy-btn');
        copyButtons.forEach(button => {
            button.addEventListener('click', function() {
                const textToCopy = this.dataset.text || window.location.href;
                AudiobookApp.copyToClipboard(textToCopy, function() {
                    button.textContent = 'Copied!';
                    setTimeout(() => {
                        button.textContent = 'Copy Error Info';
                    }, 2000);
                });
            });
        });
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    AudiobookApp.init();
});
