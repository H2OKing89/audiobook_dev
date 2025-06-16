/**
 * Component-specific JavaScript functionality
 * Reusable UI components and interactions
 */

const AudiobookComponents = {
    // Animated particles background
    initParticles: function() {
        const particlesContainer = document.getElementById('particles');
        if (!particlesContainer) return;

        const particleCount = 50;
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 2 + 's';
            particle.style.animationDuration = (Math.random() * 3 + 2) + 's';
            particlesContainer.appendChild(particle);
        }
    },

    // Modal/popup functionality
    initPopups: function() {
        // Call Quentin popup
        const callButton = document.querySelector('[data-action="contact"]');
        const popup = document.getElementById('call-quentin-popup');
        const closeButton = document.querySelector('[data-action="close-popup"]');

        if (callButton && popup) {
            callButton.addEventListener('click', function() {
                popup.style.display = 'flex';
            });
        }

        if (closeButton && popup) {
            closeButton.addEventListener('click', function() {
                popup.style.display = 'none';
            });

            // Close on outside click
            popup.addEventListener('click', function(e) {
                if (e.target === popup) {
                    popup.style.display = 'none';
                }
            });
        }
    },

    // Form enhancements
    initFormEnhancements: function() {
        // Add loading states to form buttons
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', function() {
                const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    const originalText = submitButton.textContent || submitButton.value;
                    submitButton.textContent = 'Processing...';
                    submitButton.value = 'Processing...';
                    
                    // Re-enable after 10 seconds as fallback
                    setTimeout(() => {
                        submitButton.disabled = false;
                        submitButton.textContent = originalText;
                        submitButton.value = originalText;
                    }, 10000);
                }
            });
        });
    },

    // Tooltip functionality
    initTooltips: function() {
        const tooltipTriggers = document.querySelectorAll('[data-tooltip]');
        tooltipTriggers.forEach(trigger => {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = trigger.dataset.tooltip;
            document.body.appendChild(tooltip);

            trigger.addEventListener('mouseenter', function(e) {
                tooltip.style.display = 'block';
                tooltip.style.left = e.pageX + 10 + 'px';
                tooltip.style.top = e.pageY + 10 + 'px';
            });

            trigger.addEventListener('mouseleave', function() {
                tooltip.style.display = 'none';
            });

            trigger.addEventListener('mousemove', function(e) {
                tooltip.style.left = e.pageX + 10 + 'px';
                tooltip.style.top = e.pageY + 10 + 'px';
            });
        });
    },

    // Initialize all components
    init: function() {
        this.initParticles();
        this.initPopups();
        this.initFormEnhancements();
        this.initTooltips();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    AudiobookComponents.init();
});
