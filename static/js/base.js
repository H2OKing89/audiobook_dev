/**
 * Base JavaScript functionality for the Audiobook Approval System
 * Shared utilities and common functionality across all pages
 */

// Global utilities and helpers
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

    // High contrast mode toggle (global accessibility feature)
    initContrastToggle: function() {
        const contrastToggle = document.getElementById('contrastToggle');
        if (!contrastToggle) return;

        // Check for saved preference
        const savedMode = localStorage.getItem('highContrastMode');
        if (savedMode === 'true') {
            document.body.classList.add('high-contrast');
            contrastToggle.querySelector('span').textContent = '🌙';
        }

        contrastToggle.addEventListener('click', function() {
            const isHighContrast = document.body.classList.toggle('high-contrast');
            contrastToggle.querySelector('span').textContent = isHighContrast ? '🌙' : '💫';
            localStorage.setItem('highContrastMode', isHighContrast);
        });
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
        this.initContrastToggle();
        
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
