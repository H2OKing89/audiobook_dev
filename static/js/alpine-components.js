/**
 * Alpine.js Components for Audiobook Approval System
 * Modern reactive components replacing vanilla JavaScript
 */

// Wait for Alpine to be available before initializing
let componentsRetryCount = 0;
const componentsMaxRetries = 50;

function initializeAlpineComponents() {
    if (typeof Alpine === 'undefined') {
        componentsRetryCount++;
        if (componentsRetryCount < componentsMaxRetries) {
            setTimeout(initializeAlpineComponents, 100);
        } else {
            console.error("Alpine.js not available for components after 5 seconds");
        }
        return;
    }
    if (typeof debugLog === 'function') {
        debugLog("Alpine found, initializing components...");
    }

    // Main application store
    Alpine.store('app', {
        // Loading states
        isLoading: false,

        // Theme and UI state
        theme: 'cyberpunk',

        // System status
        systemStatus: {
            uptime: '99.9%',
            cpu: '12%',
            memory: '420MB',
            dadJokes: '∞'
        },

        // Copy to clipboard utility
        async copyToClipboard(text, successCallback) {
            try {
                if (navigator.clipboard && window.isSecureContext) {
                    await navigator.clipboard.writeText(text);
                } else {
                    // Fallback for older browsers
                    const textArea = document.createElement('textarea');
                    textArea.value = text;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                }
                if (successCallback) successCallback();
            } catch (err) {
                console.warn('Copy failed:', err);
            }
        }
    });

    // Popup/Modal store
    Alpine.store('popup', {
        isOpen: false,
        type: null,
        data: null,

        open(type, data = null) {
            this.type = type;
            this.data = data;
            this.isOpen = true;
        },

        close() {
            this.isOpen = false;
            this.type = null;
            this.data = null;
        }
    });

    // Notification store
    Alpine.store('notifications', {
        items: [],

        add(message, type = 'info', duration = 3000) {
            const id = Date.now();
            this.items.push({ id, message, type });

            if (duration > 0) {
                setTimeout(() => this.remove(id), duration);
            }
        },

        remove(id) {
            this.items = this.items.filter(item => item.id !== id);
        }
    });

    // Alpine.js Magic Properties
    Alpine.magic('copy', () => {
        return (text) => {
            return Alpine.store('app').copyToClipboard(text);
        }
    });

    Alpine.magic('notify', () => {
        return (message, type = 'info') => {
            return Alpine.store('notifications').add(message, type);
        }
    });

    // Alpine.js Directives
    Alpine.directive('tooltip', (el, { expression }, { evaluate, cleanup }) => {
        const tooltipText = evaluate(expression);

        let tooltip = null;
        let onMouseEnter, onMouseLeave, onMouseMove;
        let observer = null;

        onMouseEnter = (e) => {
            // Create tooltip element
            tooltip = document.createElement('div');
            tooltip.className = 'alpine-tooltip';
            tooltip.textContent = tooltipText;
            tooltip.style.cssText = `
                position: absolute;
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
                z-index: 9999;
                pointer-events: none;
                left: ${e.pageX + 10}px;
                top: ${e.pageY + 10}px;
            `;
            document.body.appendChild(tooltip);
        };

        onMouseLeave = () => {
            if (tooltip) {
                tooltip.remove();
                tooltip = null;
            }

            // If element is no longer in the document, perform full cleanup to avoid leaks
            if (!document.body.contains(el)) {
                el.removeEventListener('mouseenter', onMouseEnter);
                el.removeEventListener('mouseleave', onMouseLeave);
                el.removeEventListener('mousemove', onMouseMove);
                if (observer) {
                    observer.disconnect();
                    observer = null;
                }
            }
        };

        onMouseMove = (e) => {
            if (tooltip) {
                tooltip.style.left = e.pageX + 10 + 'px';
                tooltip.style.top = e.pageY + 10 + 'px';
            }
        };

        el.addEventListener('mouseenter', onMouseEnter);
        el.addEventListener('mouseleave', onMouseLeave);
        el.addEventListener('mousemove', onMouseMove);

        // Observe DOM removals to clean up if the element is detached
        try {
            observer = new MutationObserver((mutations) => {
                for (const m of mutations) {
                    for (const node of m.removedNodes) {
                        if (node === el || (node.contains && node.contains(el))) {
                            // Element (or its ancestor) has been removed from the DOM
                            if (tooltip) {
                                tooltip.remove();
                                tooltip = null;
                            }
                            el.removeEventListener('mouseenter', onMouseEnter);
                            el.removeEventListener('mouseleave', onMouseLeave);
                            el.removeEventListener('mousemove', onMouseMove);
                            if (observer) {
                                observer.disconnect();
                                observer = null;
                            }
                            return;
                        }
                    }
                }
            });

            // Observe just the parent node instead of entire document.body for better performance
            observer.observe(el.parentNode || document.body, { childList: true, subtree: true });
        } catch (err) {
            // MutationObserver may not be available in some environments; fail gracefully
            console.warn('Tooltip cleanup observer not available:', err);
        }

        // Alpine's cleanup hook when available
        if (typeof cleanup === 'function') {
            cleanup(() => {
                if (tooltip) tooltip.remove();
                el.removeEventListener('mouseenter', onMouseEnter);
                el.removeEventListener('mouseleave', onMouseLeave);
                el.removeEventListener('mousemove', onMouseMove);
                if (observer) {
                    observer.disconnect();
                    observer = null;
                }
            });
        }
    });
}

// Alpine.js Data Components
window.AlpineComponents = {

    // Copy button component
    copyButton() {
        return {
            copied: false,
            originalText: 'Copy',

            async copy(text = null) {
                const textToCopy = text || this.$el.dataset.text || window.location.href;

                try {
                    await this.$store.app.copyToClipboard(textToCopy);
                    this.copied = true;
                    this.originalText = this.$el.textContent;
                    this.$el.textContent = 'Copied!';

                    setTimeout(() => {
                        this.copied = false;
                        this.$el.textContent = this.originalText;
                    }, 2000);
                } catch (err) {
                    console.warn('Copy failed:', err);
                }
            }
        }
    },

    // Auto-close countdown component
    autoCloseCountdown(seconds = 5) {
        return {
            remaining: seconds,

            init() {
                this.startCountdown();
            },

            startCountdown() {
                const interval = setInterval(() => {
                    this.remaining--;
                    if (this.remaining <= 0) {
                        clearInterval(interval);
                        try {
                            // Only attempt automatic close if window was opened by script or has an opener
                            if (window.opener || window._openedByScript) {
                                window.close();
                            } else {
                                throw new Error('Automatic close not permitted by browser');
                            }
                        } catch (err) {
                            console.warn('Auto-close failed:', err);
                            // Reveal a user-facing message/button as a fallback
                            const closeBtn = document.createElement('button');
                            closeBtn.textContent = 'Close window';
                            closeBtn.className = 'btn-details';
                            closeBtn.onclick = () => window.close();
                            document.body.appendChild(closeBtn);
                            // Notify user in UI if notifications store is available
                            if (window.Alpine && Alpine.store && Alpine.store('notifications')) {
                                Alpine.store('notifications').add('Auto-close failed; please click the button to close.', 'warning');
                            }
                        }
                    }
                }, 1000);
            }
        }
    },

    // Form enhancement component
    formEnhancer() {
        return {
            isSubmitting: false,
            originalText: '',

            init() {
                const submitButton = this.$el.querySelector('button[type="submit"], input[type="submit"]');
                if (submitButton) {
                    this.originalText = submitButton.textContent || submitButton.value;
                }
            },

            handleSubmit() {
                this.isSubmitting = true;
                const submitButton = this.$el.querySelector('button[type="submit"], input[type="submit"]');

                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.textContent = 'Processing...';
                    submitButton.value = 'Processing...';

                    // Re-enable after 10 seconds as fallback
                    setTimeout(() => {
                        this.isSubmitting = false;
                        submitButton.disabled = false;
                        submitButton.textContent = this.originalText;
                        submitButton.value = this.originalText;
                    }, 10000);
                }

                return true; // Allow form submission to continue
            }
        }
    },

    // Tooltip component
    tooltip() {
        return {
            visible: false,
            x: 0,
            y: 0,

            show(event) {
                this.visible = true;
                this.updatePosition(event);
            },

            hide() {
                this.visible = false;
            },

            updatePosition(event) {
                this.x = event.pageX + 10;
                this.y = event.pageY + 10;
            }
        }
    },

    // Particles animation component
    particles(count = 50) {
        return {
            particles: [],

            init() {
                this.generateParticles();
            },

            generateParticles() {
                for (let i = 0; i < count; i++) {
                    this.particles.push({
                        id: i,
                        left: Math.random() * 100,
                        delay: Math.random() * 2,
                        duration: Math.random() * 3 + 2
                    });
                }
            }
        }
    },

    // Dynamic tagline rotator
    taglineRotator(taglines = []) {
        return {
            currentIndex: 0,
            currentTagline: '',
            isVisible: true,
            // Track timer IDs so we can clear them on teardown
            rotationInterval: null,
            rotationTimeout: null,

            init() {
                if (taglines.length > 0) {
                    this.currentTagline = taglines[0];
                    this.startRotation();
                }
            },

            startRotation() {
                // Clear any existing timers to avoid duplicates
                if (this.rotationInterval) {
                    clearInterval(this.rotationInterval);
                    this.rotationInterval = null;
                }
                if (this.rotationTimeout) {
                    clearTimeout(this.rotationTimeout);
                    this.rotationTimeout = null;
                }

                this.rotationInterval = setInterval(() => {
                    this.isVisible = false;

                    // Clear previous timeout if any
                    if (this.rotationTimeout) {
                        clearTimeout(this.rotationTimeout);
                        this.rotationTimeout = null;
                    }

                    this.rotationTimeout = setTimeout(() => {
                        this.currentIndex = (this.currentIndex + 1) % taglines.length;
                        this.currentTagline = taglines[this.currentIndex];
                        this.isVisible = true;
                        // Clear reference to completed timeout
                        this.rotationTimeout = null;
                    }, 300);
                }, 4000);
            },

            stopRotation() {
                if (this.rotationInterval) {
                    clearInterval(this.rotationInterval);
                    this.rotationInterval = null;
                }
                if (this.rotationTimeout) {
                    clearTimeout(this.rotationTimeout);
                    this.rotationTimeout = null;
                }
            },

            destroy() {
                // Ensure all timers are cleared when component is torn down
                this.stopRotation();
            }
        }
    },

    // Loading screen component
    loadingScreen() {
        return {
            isLoading: true,
            progress: 0,
            _loadingInterval: null,

            init() {
                this.simulateLoading();
            },

            simulateLoading() {
                this._loadingInterval = setInterval(() => {
                    this.progress += Math.random() * 15;

                    if (this.progress >= 100) {
                        this.progress = 100;
                        if (this._loadingInterval) {
                            clearInterval(this._loadingInterval);
                            this._loadingInterval = null;
                        }

                        setTimeout(() => {
                            this.isLoading = false;
                        }, 500);
                    }
                }, 100);
            },

            destroy() {
                if (this._loadingInterval) {
                    clearInterval(this._loadingInterval);
                    this._loadingInterval = null;
                }
            }
        }
    },

    // Stats counter component
    statsCounter(targetValue, duration = 2000) {
        return {
            currentValue: 0,
            _animationFrameId: null,

            init() {
                this.animateCounter(targetValue, duration);
            },

            animateCounter(target, duration) {
                const startTime = Date.now();
                const startValue = 0;

                const animate = () => {
                    const elapsed = Date.now() - startTime;
                    const progress = Math.min(elapsed / duration, 1);

                    this.currentValue = Math.floor(startValue + (target - startValue) * progress);

                    if (progress < 1) {
                        this._animationFrameId = requestAnimationFrame(animate);
                    } else {
                        this._animationFrameId = null;
                    }
                };

                this._animationFrameId = requestAnimationFrame(animate);
            },

            destroy() {
                if (this._animationFrameId !== null) {
                    cancelAnimationFrame(this._animationFrameId);
                    this._animationFrameId = null;
                }
            }
        }
    }
};

// Initialize when Alpine is ready
document.addEventListener('DOMContentLoaded', initializeAlpineComponents);
