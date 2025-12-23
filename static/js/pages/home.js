/**
 * 🎧 ENHANCED HOME PAGE - CYBERPUNK AUTOMATION HQ 🎧
 * Overhauled for maximum interactivity and smooth animations
 */

const HomePage = {
    // Enhanced rotating taglines with more personality
    taglines: [
        "Stop sorting audiobooks like a caveman—let the robots handle it! 🤖",
        "Now with 99.9% fewer manual clicks and 300% more automation swagger! ✨",
        "Your audiobook backlog is about to meet its match. 📚⚡",
        "Because life's too short for duplicate MP3s and folder chaos. 🗂️",
        "Audiobook approval, Quentin style: Maximum overkill, maximum satisfaction. 🚀",
        "Automate, approve, listen, repeat. It's the circle of digital life! 🔄",
        "Runs on Python, caffeine, and pure engineering stubbornness. ☕",
        "One click and your next literary adventure is queued up! 🎧",
        "If you're seeing this page, you're already winning at automation! 🏆",
        "Where audiobooks go to get properly organized (finally). 📖",
        "Turning audiobook chaos into beautiful, automated harmony. 🎵",
        "Your personal audiobook butler, minus the fancy accent. 🎩",
        "Making libraries everywhere jealous since 2024. 📚✨",
        "Proof that over-engineering can be beautiful. 🛠️💎",
        "Welcome to the matrix... of audiobook organization! 🕶️",
        "Cyberpunk vibes meet productivity - deal with it! 😎"
    ],

    // Enhanced cycling footer with more wit
    footerPhrases: [
        "Powered by Quentin's Legendary Overkill Engineering™ 🤖",
        "Serving pages with more precision than a Swiss chronometer ⏰",
        "No audiobooks were harmed in the making of this automation 📚",
        "All systems nominal. Humans? Well, that's debatable 🤷‍♂️",
        "Built with more caffeine than sleep, as tradition demands ☕",
        "Running on 24-core Threadripper and pure determination 💪",
        "🔄 Refresh for another dose of Quentin wisdom",
        "Where code meets chaos and somehow produces order 🌪️➡️📊",
        "Automating your audiobooks with algorithmic fury ⚡",
        "Making your digital library so organized, Marie Kondo would weep 🧹✨",
        "Defying the laws of software development since day one 🚀",
        "Cyberpunk vibes meet audiobook organization. Deal with it. 😎",
        "Turning caffeine into code since 2024 ☕➡️💻",
        "More features than a Swiss Army knife, less stabby 🔧✨"
    ],

    // Processing status messages
    processingMessages: [
        "Processing Requests",
        "Analyzing Metadata",
        "Optimizing Chaos",
        "Teaching AI Sarcasm",
        "Brewing More Coffee",
        "Defying Physics",
        "Channeling Cyberpunk",
        "Maximum Overkill Mode"
    ],

    // State management
    state: {
        isInitialized: false,
        taglineIndex: 0,
        footerIndex: 0,
        processingIndex: 0,
        intervals: {},
        isPopupOpen: false,
        isFabMenuOpen: false,
        popupPreloaded: false // Add preload flag
    },

    // Initialize loading screen and fade out
    initLoadingScreen: function() {
        const loadingScreen = document.getElementById('loadingScreen');
        const homeContainer = document.getElementById('homeContainer');

        if (loadingScreen && homeContainer) {
            // Hide home container initially
            homeContainer.style.opacity = '0';

            // Use requestAnimationFrame for smoother transitions
            requestAnimationFrame(() => {
                setTimeout(() => {
                    loadingScreen.classList.add('hidden');
                    homeContainer.style.transition = 'opacity 1s ease-in';
                    homeContainer.style.opacity = '1';

                    // Start animations after loading screen disappears
                    requestIdleCallback(() => {
                        this.startDynamicContent();
                    }, { timeout: 500 });
                }, 1500); // Reduced from 2000ms
            });
        }
    },

    // Dynamic tagline cycling with smooth transitions
    initTaglineCycling: function() {
        const tagElement = document.getElementById('dynamicTag');
        if (!tagElement) return;

        const cycleTagline = () => {
            tagElement.style.opacity = '0';
            tagElement.style.transform = 'translateY(10px)';

            setTimeout(() => {
                tagElement.textContent = this.taglines[this.state.taglineIndex % this.taglines.length];
                this.state.taglineIndex++;
                tagElement.style.opacity = '1';
                tagElement.style.transform = 'translateY(0)';
            }, 300);
        };

        // Add CSS transition
        tagElement.style.transition = 'all 0.3s ease';

        // Start cycling
        this.state.intervals.tagline = setInterval(cycleTagline, 4000);

        // Initial cycle after delay
        setTimeout(cycleTagline, 2000);
    },

    // Footer cycling with enhanced transitions
    initFooterCycling: function() {
        const footerElement = document.getElementById('footerText');
        if (!footerElement) return;

        const cycleFooter = () => {
            footerElement.style.opacity = '0';
            footerElement.style.transform = 'scale(0.95)';

            setTimeout(() => {
                footerElement.textContent = this.footerPhrases[this.state.footerIndex % this.footerPhrases.length];
                this.state.footerIndex++;
                footerElement.style.opacity = '1';
                footerElement.style.transform = 'scale(1)';
            }, 250);
        };

        footerElement.style.transition = 'all 0.25s ease';
        this.state.intervals.footer = setInterval(cycleFooter, 6000);
        setTimeout(cycleFooter, 3000);
    },

    // Processing status cycling
    initProcessingStatus: function() {
        const statusElement = document.getElementById('processingStatus');
        if (!statusElement) return;

        const cycleStatus = () => {
            statusElement.textContent = this.processingMessages[this.state.processingIndex % this.processingMessages.length];
            this.state.processingIndex++;
        };

        this.state.intervals.processing = setInterval(cycleStatus, 3000);
    },

    // Enhanced cat tail easter egg with animations
    initCatTailEasterEgg: function() {
        const catTail = document.getElementById('catTail');
        const mascotImg = document.getElementById('mascotImg');
        const tip = document.getElementById('easterTip');

        if (catTail && tip && mascotImg) {
            // Add click handler to mascot
            mascotImg.addEventListener('click', () => {
                this.showEasterEgg();
            });

            // Add click handler for tail
            catTail.addEventListener('click', () => {
                this.showEasterEgg();
            });

            // Close tip handler
            const closeBtn = tip.querySelector('[data-action="close-tip"]');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    this.hideEasterEgg();
                });
            }
        }
    },

    showEasterEgg: function() {
        const tip = document.getElementById('easterTip');
        if (tip) {
            tip.classList.add('show');
            tip.style.display = 'flex';

            // Auto-hide after 5 seconds
            setTimeout(() => {
                this.hideEasterEgg();
            }, 5000);
        }
    },

    hideEasterEgg: function() {
        const tip = document.getElementById('easterTip');
        if (tip) {
            tip.classList.remove('show');
            setTimeout(() => {
                tip.style.display = 'none';
            }, 300);
        }
    },

    // Enhanced popup functionality with smooth animations and preloading
    initPopupFunctionality: function() {
        const contactButton = document.querySelector('[data-action="contact"]');
        const popup = document.getElementById('callQuentinPopup');
        const closeButtons = document.querySelectorAll('[data-action="close-popup"]');
        const backdrop = document.querySelector('.popup-backdrop');

        if (contactButton && popup) {
            // Preload popup on hover for instant response
            contactButton.addEventListener('mouseenter', () => {
                if (!this.state.popupPreloaded) {
                    this.preloadPopup(popup);
                }
            });

            contactButton.addEventListener('click', (e) => {
                e.preventDefault();
                this.openPopup(popup);
            });
        }

        // Close popup functionality
        const closePopup = () => {
            this.closePopup(popup);
        };

        closeButtons.forEach(button => {
            button.addEventListener('click', closePopup);
        });

        if (backdrop) {
            backdrop.addEventListener('click', closePopup);
        }

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.state.isPopupOpen) {
                closePopup();
            }
        });
    },

    preloadPopup: function(popup) {
        if (popup && !this.state.popupPreloaded) {
            popup.style.display = 'block';
            popup.style.visibility = 'hidden';

            // Force browser to render the popup
            popup.offsetHeight;

            popup.style.display = 'none';
            popup.style.visibility = '';
            this.state.popupPreloaded = true;
        }
    },

    openPopup: function(popup) {
        if (popup) {
            popup.style.display = 'flex';
            this.state.isPopupOpen = true;
            document.body.style.overflow = 'hidden';

            // Use requestAnimationFrame for smoother animation
            requestAnimationFrame(() => {
                popup.classList.add('show');
            });
        }
    },

    closePopup: function(popup) {
        if (popup) {
            popup.classList.remove('show');
            this.state.isPopupOpen = false;
            document.body.style.overflow = '';

            setTimeout(() => {
                popup.style.display = 'none';
            }, 300);
        }
    },

    // Animated statistics counters
    initStatCounters: function() {
        const counters = document.querySelectorAll('[data-target]');

        const observerOptions = {
            threshold: 0.5,
            rootMargin: '0px 0px -100px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        counters.forEach(counter => {
            observer.observe(counter);
        });
    },

    animateCounter: function(element) {
        const target = parseInt(element.getAttribute('data-target'));
        const duration = 2000;
        const start = performance.now();

        const animate = (currentTime) => {
            const elapsed = currentTime - start;
            const progress = Math.min(elapsed / duration, 1);

            // Easing function for smooth animation
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = Math.floor(easeOutQuart * target);

            element.textContent = current;

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                element.textContent = target;
            }
        };

        requestAnimationFrame(animate);
    },

    // Dynamic uptime counter
    initUptimeCounter: function() {
        const uptimeElement = document.getElementById('uptimeDisplay');
        if (!uptimeElement) return;

        let uptime = 99.9;
        let increasing = true;

        this.state.intervals.uptime = setInterval(() => {
            if (increasing) {
                uptime += Math.random() * 0.01;
                if (uptime >= 99.999) increasing = false;
            } else {
                uptime -= Math.random() * 0.005;
                if (uptime <= 99.9) increasing = true;
            }
            uptimeElement.textContent = uptime.toFixed(3) + '%';
        }, 2000);
    },

    // Floating Action Button functionality
    initFAB: function() {
        const fabButton = document.getElementById('fabButton');
        const fabMenu = document.getElementById('fabMenu');

        if (fabButton && fabMenu) {
            fabButton.addEventListener('click', () => {
                this.toggleFABMenu();
            });

            // Close FAB menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!fabButton.contains(e.target) && !fabMenu.contains(e.target)) {
                    this.closeFABMenu();
                }
            });
        }
    },

    toggleFABMenu: function() {
        const fabMenu = document.getElementById('fabMenu');
        const fabButton = document.getElementById('fabButton');

        if (this.state.isFabMenuOpen) {
            this.closeFABMenu();
        } else {
            this.openFABMenu();
        }
    },

    openFABMenu: function() {
        const fabMenu = document.getElementById('fabMenu');
        const fabButton = document.getElementById('fabButton');

        if (fabMenu && fabButton) {
            fabMenu.classList.add('active');
            fabButton.style.transform = 'rotate(45deg)';
            this.state.isFabMenuOpen = true;
        }
    },

    closeFABMenu: function() {
        const fabMenu = document.getElementById('fabMenu');
        const fabButton = document.getElementById('fabButton');

        if (fabMenu && fabButton) {
            fabMenu.classList.remove('active');
            fabButton.style.transform = 'rotate(0deg)';
            this.state.isFabMenuOpen = false;
        }
    },

    // Smooth scrolling functionality with debouncing
    initSmoothScrolling: function() {
        document.querySelectorAll('[data-action="scroll-top"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
        });

        // Debounced scroll handler
        let scrollTimeout;
        let lastScrollTop = 0;

        const handleScroll = () => {
            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
            const fabContainer = document.querySelector('.fab-container');

            if (fabContainer) {
                if (scrollTop > lastScrollTop && scrollTop > 200) {
                    // Scrolling down
                    fabContainer.style.transform = 'translateY(100px)';
                } else {
                    // Scrolling up
                    fabContainer.style.transform = 'translateY(0)';
                }
            }

            lastScrollTop = scrollTop;
        };

        window.addEventListener('scroll', () => {
            if (scrollTimeout) {
                window.cancelAnimationFrame(scrollTimeout);
            }

            scrollTimeout = window.requestAnimationFrame(() => {
                handleScroll();
            });
        }, { passive: true });
    },

    // Enhanced feature card interactions
    initFeatureCardEffects: function() {
        const featureCards = document.querySelectorAll('.feature-card');

        featureCards.forEach((card, index) => {
            // Add staggered hover animations
            card.style.animationDelay = `${index * 0.1}s`;

            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-10px) scale(1.02)';
                card.style.zIndex = '10';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
                card.style.zIndex = '1';
            });

            // Add click effect
            card.addEventListener('click', () => {
                card.style.transform = 'translateY(-8px) scale(0.98)';
                setTimeout(() => {
                    card.style.transform = 'translateY(-10px) scale(1.02)';
                }, 150);
            });
        });
    },

    // Button enhancement effects with optimized ripple
    initButtonEffects: function() {
        const buttons = document.querySelectorAll('.quick-link-btn');

        buttons.forEach(button => {
            // Prepare button for ripple effect
            button.style.position = 'relative';
            button.style.overflow = 'hidden';

            // Add ripple effect with optimization
            button.addEventListener('click', (e) => {
                requestAnimationFrame(() => {
                    this.createRipple(e, button);
                });
            });

            button.addEventListener('mouseenter', () => {
                button.style.transform = 'translateY(-3px) scale(1.02)';
            });

            button.addEventListener('mouseleave', () => {
                button.style.transform = 'translateY(0) scale(1)';
            });
        });
    },

    createRipple: function(e, button) {
        const ripple = document.createElement('span');
        const rect = button.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;

        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple-effect');

        // Add ripple styles
        ripple.style.position = 'absolute';
        ripple.style.borderRadius = '50%';
        ripple.style.background = 'rgba(255, 255, 255, 0.3)';
        ripple.style.pointerEvents = 'none';
        ripple.style.animation = 'ripple-animation 0.6s ease-out';

        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);

        // Remove ripple after animation
        setTimeout(() => {
            ripple.remove();
        }, 600);
    },

    // Particle effects system with performance optimization
    initParticleEffects: function() {
        const container = document.getElementById('particlesContainer');
        if (!container) return;

        // Reduce particle frequency on low-end devices
        const particleInterval = window.matchMedia('(max-width: 768px)').matches ? 5000 : 3000;

        const createParticle = () => {
            if (document.hidden) return; // Don't create particles when tab is hidden

            const particle = document.createElement('div');
            particle.classList.add('particle');

            // Random starting position
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
            particle.style.animationDelay = Math.random() * 2 + 's';

            // Random color
            const colors = ['#00f5ff', '#ff006e', '#00ff88', '#ffbd2e'];
            particle.style.background = colors[Math.floor(Math.random() * colors.length)];

            container.appendChild(particle);

            // Remove particle after animation
            setTimeout(() => {
                particle.remove();
            }, 8000);
        };

        // Create particles periodically
        this.state.intervals.particles = setInterval(createParticle, particleInterval);

        // Limit number of particles
        setInterval(() => {
            const particles = container.querySelectorAll('.particle');
            if (particles.length > 10) {
                particles[0].remove();
            }
        }, 1000);
    },

    // Start all dynamic content after loading with staggered initialization
    startDynamicContent: function() {
        // Use requestIdleCallback for non-critical features
        requestIdleCallback(() => this.initTaglineCycling(), { timeout: 100 });
        requestIdleCallback(() => this.initFooterCycling(), { timeout: 200 });
        requestIdleCallback(() => this.initProcessingStatus(), { timeout: 300 });
        requestIdleCallback(() => this.initStatCounters(), { timeout: 400 });
        requestIdleCallback(() => this.initUptimeCounter(), { timeout: 500 });
        requestIdleCallback(() => this.initParticleEffects(), { timeout: 600 });
    },

    // Cleanup function for intervals
    cleanup: function() {
        Object.values(this.state.intervals).forEach(interval => {
            if (interval) clearInterval(interval);
        });
        this.state.intervals = {};
    },

    // Initialize all home page functionality
    init: function() {
        // Only run on home page
        if (!document.body.classList.contains('home-page')) return;
        if (this.state.isInitialized) return;

        debugLog('🎧 Initializing Enhanced Audiobook HQ Homepage...');

        // Add CSS animations keyframes dynamically
        this.addDynamicStyles();

        // Initialize core functionality
        this.initLoadingScreen();
        this.initCatTailEasterEgg();
        this.initPopupFunctionality();
        this.initFAB();
        this.initSmoothScrolling();
        this.initFeatureCardEffects();
        this.initButtonEffects();

        this.state.isInitialized = true;
        debugLog('✅ Enhanced Homepage initialization complete!');
    },

    // Add dynamic CSS animations with performance hints
    addDynamicStyles: function() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes ripple-animation {
                0% { transform: scale(0); opacity: 1; }
                100% { transform: scale(2); opacity: 0; }
            }

            .tagline-fade { opacity: 0.3; transform: translateY(5px); }
            .footer-fade { opacity: 0.3; transform: scale(0.98); }

            .fab-container {
                transition: transform 0.3s ease;
                will-change: transform;
            }
            .quick-link-btn {
                transition: all 0.3s ease;
                will-change: transform;
            }
            .feature-card {
                transition: all 0.3s ease;
                will-change: transform;
            }
            .call-quentin-popup {
                will-change: opacity, visibility;
            }
            .popup-content {
                will-change: transform;
            }
        `;
        document.head.appendChild(style);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    HomePage.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    HomePage.cleanup();
});

// Handle visibility change to pause/resume animations
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        HomePage.cleanup();
    } else if (HomePage.state.isInitialized) {
        setTimeout(() => {
            HomePage.startDynamicContent();
        }, 1000);
    }
});

// Expose HomePage for debugging
window.HomePage = HomePage;

// Add requestIdleCallback polyfill for older browsers
window.requestIdleCallback = window.requestIdleCallback || function(cb) {
    const start = Date.now();
    return setTimeout(function() {
        cb({
            didTimeout: false,
            timeRemaining: function() {
                return Math.max(0, 50 - (Date.now() - start));
            }
        });
    }, 1);
};
