/**
 * Alpine.js Success/Rejection/Error Pages Components
 * Enhanced interactive result pages
 */

// Wait for Alpine to be available
let pagesRetryCount = 0;
const pagesMaxRetries = 100;

function initializePagesComponents() {
    if (typeof Alpine === 'undefined') {
        pagesRetryCount++;
        if (pagesRetryCount < pagesMaxRetries) {
            setTimeout(initializePagesComponents, 50);
        } else {
            console.error(`Alpine.js not available for pages components after ${pagesMaxRetries} attempts`);
        }
        return;
    }

    // Success Page Component
    Alpine.data('successPage', () => ({
        // Celebration state
        celebrationActive: false,
        confettiActive: false,
        achievementUnlocked: false,
        
        // Dynamic content
        successQuotes: [
            "🎉 Mission accomplished! Your audiobook is queued for download!",
            "🚀 Success rate: 100%. Confidence level: Over 9000!",
            "✨ Another victory for Team Automation!",
            "🎧 Your literary adventure awaits!",
            "🤖 Beep boop! Success protocol executed flawlessly!",
            "🏆 Achievement unlocked: Master of Audiobook Approval!"
        ],
        currentQuote: '',
        
        // Stats
        systemStats: {
            successRate: 0,
            happinessLevel: 0,
            confettiDeployed: 0,
            nextRequest: 'READY'
        },
        
        init() {
            this.currentQuote = this.successQuotes[Math.floor(Math.random() * this.successQuotes.length)];
            this.animateStats();
            this.triggerInitialCelebration();
        },
        
        // Track running intervals for cleanup
        _rateInterval: null,
        _happinessInterval: null,
        _confettiInterval: null,

        animateStats() {
            // Animate success rate to 100%
            let rate = 0;
            this._rateInterval = setInterval(() => {
                rate += 2;
                this.systemStats.successRate = Math.min(rate, 100);
                if (rate >= 100) {
                    clearInterval(this._rateInterval);
                    this._rateInterval = null;
                }
            }, 50);

            // Animate happiness level
            let happiness = 0;
            this._happinessInterval = setInterval(() => {
                happiness += 5;
                this.systemStats.happinessLevel = Math.min(happiness, 100);
                if (happiness >= 100) {
                    clearInterval(this._happinessInterval);
                    this._happinessInterval = null;
                }
            }, 30);

            // Animate confetti count
            let confetti = 0;
            this._confettiInterval = setInterval(() => {
                confetti += 10;
                this.systemStats.confettiDeployed = confetti;
                if (confetti >= 1000) {
                    this.systemStats.confettiDeployed = '∞';
                    clearInterval(this._confettiInterval);
                    this._confettiInterval = null;
                }
            }, 100);
        },

        destroy() {
            // Clear any intervals started by this component
            if (this._rateInterval) {
                clearInterval(this._rateInterval);
                this._rateInterval = null;
            }
            if (this._happinessInterval) {
                clearInterval(this._happinessInterval);
                this._happinessInterval = null;
            }
            if (this._confettiInterval) {
                clearInterval(this._confettiInterval);
                this._confettiInterval = null;
            }
        },

        
        triggerInitialCelebration() {
            setTimeout(() => {
                this.celebrationActive = true;
                this.deployConfetti();
            }, 500);
        },
        
        triggerCelebration() {
            this.celebrationActive = true;
            this.deployConfetti();
            this.$notify('🎊 Extra celebration activated!', 'success');
        },
        
        deployConfetti() {
            this.confettiActive = true;
            // Create confetti particles
            for (let i = 0; i < 50; i++) {
                this.createConfettiParticle();
            }
            
            setTimeout(() => {
                this.confettiActive = false;
            }, 3000);
        },
        
        createConfettiParticle() {
            const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#f0932b'];
            const confetti = document.createElement('div');
            confetti.style.cssText = `
                position: fixed;
                width: 10px;
                height: 10px;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                left: ${Math.random() * 100}vw;
                top: -10px;
                z-index: 9999;
                animation: confetti-fall ${Math.random() * 2 + 2}s linear forwards;
            `;
            document.body.appendChild(confetti);
            
            setTimeout(() => {
                confetti.remove();
            }, 4000);
        },
        
        showStatusUpdate() {
            this.$notify('📊 Status: Your audiobook is #1 in the priority queue!', 'info');
        },
        
        showEasterEgg() {
            this.achievementUnlocked = true;
            this.$notify('🥚 Easter egg found! You are now a certified audiobook ninja!', 'success');
        }
    }));
    
    // Rejection Page Component
    Alpine.data('rejectionPage', () => ({
        // State
        isRetryMessageVisible: false,
        easterEggFound: false,
        
        // Dynamic content
        dadJokes: [
            "Why don't scientists trust atoms? Because they make up everything!",
            "I told my wife she was drawing her eyebrows too high. She looked surprised.",
            "Why don't skeletons fight each other? They don't have the guts.",
            "What do you call a fake noodle? An impasta!",
            "Why did the scarecrow win an award? He was outstanding in his field!",
            "I'm reading a book about anti-gravity. It's impossible to put down!"
        ],
        currentJoke: '',
        
        // System state
        rejectionCount: 1,
        userTears: 0,
        appealSuccessRate: 42,
        
        init() {
            this.loadDadJoke();
        },
        
        loadDadJoke() {
            this.currentJoke = this.dadJokes[Math.floor(Math.random() * this.dadJokes.length)];
        },
        
        showRetryMessage() {
            this.isRetryMessageVisible = true;
            this.$notify('💡 Pro tip: Try adjusting your request and resubmitting!', 'info');
        },
        
        triggerEasterEgg() {
            this.easterEggFound = true;
            this.$notify('🎉 Secret achievement unlocked: Rejection Survivor!', 'success');
        },
        
        generateNewJoke() {
            this.loadDadJoke();
            this.$notify('🎭 Fresh dad joke deployed!', 'info');
        }
    }));
    
    // Token Expired Page Component
    Alpine.data('tokenExpiredPage', () => ({
        // Time-related state
        timeFactIndex: 0,
        timeFactInterval: null,
        showTimeHelp: false,
        showTokenInfo: false,
        
        // Time facts
        timeFacts: [
            "⏰ A token's lifespan is shorter than a mayfly's attention span!",
            "🕐 Time flies when you're having fun, but tokens expire faster!",
            "⏱️ Fun fact: This token expired 0.42 seconds ago!",
            "🕰️ Time is relative, but token expiration is absolute!",
            "⏰ Tokens are like ice cream - best used quickly!",
            "🕐 Time waits for no one, especially not expired tokens!"
        ],
        currentTimeFact: '',
        
        // System stats
        timeSync: 'FAILED',
        paradoxLevel: 'MODERATE',
        timelineIntegrity: 87,
        
        init() {
            this.currentTimeFact = this.timeFacts[0];
            this.startTimeFactRotation();
        },
        
        startTimeFactRotation() {
            // Clear existing interval if present
            if (this.timeFactInterval) {
                clearInterval(this.timeFactInterval);
                this.timeFactInterval = null;
            }

            this.timeFactInterval = setInterval(() => {
                this.timeFactIndex = (this.timeFactIndex + 1) % this.timeFacts.length;
                this.currentTimeFact = this.timeFacts[this.timeFactIndex];
            }, 3000);
        },

        stopTimeFactRotation() {
            if (this.timeFactInterval) {
                clearInterval(this.timeFactInterval);
                this.timeFactInterval = null;
            }
        },

        destroy() {
            // Cleanup when component is torn down
            this.stopTimeFactRotation();
        },
        
        showTimeHelp() {
            this.showTimeHelp = true;
            this.$notify('🕰️ Time help activated! Check the overlay.', 'info');
        },
        
        explainTokens() {
            this.showTokenInfo = true;
            this.$notify('💡 Token info displayed!', 'info');
        },
        
        timeTravel() {
            this.$notify('⏰ Time travel failed - tokens are immutable!', 'error');
            // Trigger a fun glitch effect
            document.body.style.animation = 'glitch 0.5s ease-in-out';
            setTimeout(() => {
                document.body.style.animation = '';
            }, 500);
        },
        
        closeTimeHelp() {
            this.showTimeHelp = false;
        },
        
        closeTokenInfo() {
            this.showTokenInfo = false;
        }
    }));
    
    // Error Page Component (for 401, 404, etc.)
    Alpine.data('errorPage', () => ({
        // Error state
        showDetails: false,
        errorReported: false,
        
        // Error info
        errorInfo: {
            code: '401',
            type: 'Unauthorized',
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            path: window.location.pathname
        },
        
        // Error tips
        errorTips: [
            "🔐 Double-check your API key or authentication",
            "🌐 Verify you're accessing the correct endpoint",
            "🔄 Try refreshing the page and attempting again",
            "👨‍💻 Contact the administrator if the issue persists"
        ],
        
        init() {
            // Auto-detect error type from page
            if (window.location.pathname.includes('401')) {
                this.errorInfo.code = '401';
                this.errorInfo.type = 'Unauthorized';
            } else if (window.location.pathname.includes('404')) {
                this.errorInfo.code = '404';
                this.errorInfo.type = 'Not Found';
            }
        },
        
        toggleDetails() {
            this.showDetails = !this.showDetails;
        },
        
        copyErrorInfo() {
            const errorText = `
Error ${this.errorInfo.code}: ${this.errorInfo.type}
Path: ${this.errorInfo.path}
Timestamp: ${this.errorInfo.timestamp}
User Agent: ${this.errorInfo.userAgent}
            `.trim();
            
            this.$copy(errorText).then(() => {
                this.$notify('📋 Error details copied to clipboard!', 'success');
            });
        },
        
        reportError() {
            this.errorReported = true;
            this.$notify('📧 Error report sent! Thanks for helping improve the system.', 'success');
        }
    }));
}

// Initialize when ready
document.addEventListener('DOMContentLoaded', initializePagesComponents);

// Add confetti animation CSS (idempotent)
if (!document.getElementById('confetti-style')) {
    const confettiStyle = document.createElement('style');
    confettiStyle.id = 'confetti-style';
    confettiStyle.dataset.confettiStyle = '1';
    confettiStyle.textContent = `
@keyframes confetti-fall {
    0% {
        transform: translateY(-10px) rotate(0deg);
        opacity: 1;
    }
    100% {
        transform: translateY(100vh) rotate(720deg);
        opacity: 0;
    }
}
`;
    document.head.appendChild(confettiStyle);
}
