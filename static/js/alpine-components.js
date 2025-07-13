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
    console.log("Alpine found, initializing components...");

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
    Alpine.directive('tooltip', (el, { expression }, { evaluate }) => {
        const tooltipText = evaluate(expression);
        
        let tooltip = null;
        
        el.addEventListener('mouseenter', (e) => {
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
        });
        
        el.addEventListener('mouseleave', () => {
            if (tooltip) {
                tooltip.remove();
                tooltip = null;
            }
        });
        
        el.addEventListener('mousemove', (e) => {
            if (tooltip) {
                tooltip.style.left = e.pageX + 10 + 'px';
                tooltip.style.top = e.pageY + 10 + 'px';
            }
        });
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
                        window.close();
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
            
            init() {
                if (taglines.length > 0) {
                    this.currentTagline = taglines[0];
                    this.startRotation();
                }
            },
            
            startRotation() {
                setInterval(() => {
                    this.isVisible = false;
                    
                    setTimeout(() => {
                        this.currentIndex = (this.currentIndex + 1) % taglines.length;
                        this.currentTagline = taglines[this.currentIndex];
                        this.isVisible = true;
                    }, 300);
                }, 4000);
            }
        }
    },
    
    // Loading screen component
    loadingScreen() {
        return {
            isLoading: true,
            progress: 0,
            
            init() {
                this.simulateLoading();
            },
            
            simulateLoading() {
                const interval = setInterval(() => {
                    this.progress += Math.random() * 15;
                    
                    if (this.progress >= 100) {
                        this.progress = 100;
                        clearInterval(interval);
                        
                        setTimeout(() => {
                            this.isLoading = false;
                        }, 500);
                    }
                }, 100);
            }
        }
    },
    
    // Stats counter component
    statsCounter(targetValue, duration = 2000) {
        return {
            currentValue: 0,
            
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
                        requestAnimationFrame(animate);
                    }
                };
                
                requestAnimationFrame(animate);
            }
        }
    }
};

// Initialize when Alpine is ready
document.addEventListener('DOMContentLoaded', initializeAlpineComponents);

// Also try to initialize immediately in case DOMContentLoaded already fired
initializeAlpineComponents();
