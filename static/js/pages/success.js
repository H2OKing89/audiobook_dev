/**
 * SUCCESS PAGE JAVASCRIPT
 * Cyberpunk Terminal Theme - Success Celebration Suite
 * Features: Quote Generator, Celebration Effects, Keyboard Shortcuts, Easter Eggs
 */

// =============================================================================
// INSPIRATIONAL QUOTES DATABASE
// =============================================================================

const INSPIRATIONAL_QUOTES = [
    {
        text: "The best time to read was 20 years ago. The second best time is now.",
        author: "Ancient Audiobook Proverb"
    },
    {
        text: "A book a day keeps the boredom away!",
        author: "Dr. Read-a-lot"
    },
    {
        text: "Success is not final, failure is not fatal: it is the courage to continue that counts... and good audiobooks.",
        author: "Winston Churchill (probably)"
    },
    {
        text: "In the future, all books will be audio. You're just ahead of your time!",
        author: "Time Traveler Anonymous"
    },
    {
        text: "Reading is to the mind what exercise is to the body... and audiobooks are like having a personal trainer!",
        author: "Joseph Addison 2.0"
    },
    {
        text: "A reader lives a thousand lives before he dies. An audiobook listener lives them in 2x speed!",
        author: "George R.R. Martin (Speed Reader Edition)"
    },
    {
        text: "Knowledge is power. Audiobooks are power with sound effects!",
        author: "Sir Francis Bacon (Crispy)"
    },
    {
        text: "The more that you listen, the more things you will know. The more that you know, the more places you'll go!",
        author: "Dr. Seuss (Audio Edition)"
    },
    {
        text: "I have not failed. I've just found 10,000 ways that don't work... but audiobooks always work!",
        author: "Thomas Edison (Inventor of Audio)"
    },
    {
        text: "Today a reader, tomorrow a leader... today an audiobook listener, tomorrow a speed-leader!",
        author: "Margaret Fuller (Fast Forward)"
    },
    {
        text: "Books are a uniquely portable magic. Audiobooks are magic with Bluetooth!",
        author: "Stephen King (Wireless Wizard)"
    },
    {
        text: "If you want to go fast, go alone. If you want to go far, bring audiobooks.",
        author: "African Proverb (Audio Edition)"
    },
    {
        text: "The journey of a thousand miles begins with a single step... and a good audiobook playlist.",
        author: "Lao Tzu (Ancient Audio Master)"
    },
    {
        text: "In the end, we will remember not the words of our enemies, but the audiobooks of our friends.",
        author: "MLK Jr. (Audio Civil Rights Leader)"
    },
    {
        text: "Imagination is more important than knowledge... but audiobooks give you both!",
        author: "Albert Einstein (Genius Audio Enthusiast)"
    },
    {
        text: "Two things are infinite: the universe and audiobook queues, and I'm not sure about the universe.",
        author: "Albert Einstein (Queue Theorist)"
    },
    {
        text: "Success is 1% inspiration, 99% perspiration, and 100% having the right audiobook.",
        author: "Thomas Edison (Math Challenged)"
    },
    {
        text: "The only impossible journey is the one you never begin... so start that audiobook!",
        author: "Tony Robbins (Motivational Audio Coach)"
    },
    {
        text: "Whether you think you can or you think you can't, you're right... but audiobooks help either way!",
        author: "Henry Ford (Auto-Audio Pioneer)"
    },
    {
        text: "Life is what happens to you while you're busy making other plans... like audiobook playlists!",
        author: "John Lennon (Beatle Audio Fan)"
    }
];

// =============================================================================
// CELEBRATION EFFECTS & ANIMATIONS
// =============================================================================

class CelebrationEngine {
    constructor() {
        this.confettiActive = false;
        this.particleCount = 0;
        this.maxParticles = 50;
        this.colors = ['#00ff41', '#0099ff', '#ff0099', '#ffff00', '#ff6600'];
    }

    createConfetti() {
        if (this.particleCount >= this.maxParticles) return;

        const confetti = document.createElement('div');
        confetti.className = 'confetti-particle';
        confetti.style.cssText = `
            position: fixed;
            width: 10px;
            height: 10px;
            background: ${this.colors[Math.floor(Math.random() * this.colors.length)]};
            left: ${Math.random() * window.innerWidth}px;
            top: -10px;
            z-index: 9999;
            border-radius: 50%;
            pointer-events: none;
            animation: confetti-fall ${2 + Math.random() * 3}s linear forwards;
        `;

        document.body.appendChild(confetti);
        this.particleCount++;

        // Clean up when animation ends
        confetti.addEventListener('animationend', () => {
            if (confetti.parentNode) {
                confetti.parentNode.removeChild(confetti);
                this.particleCount--;
            }
        });
    }

    startConfetti() {
        if (this.confettiActive) return;
        this.confettiActive = true;

        // Add confetti CSS animation if not already present
        if (!document.getElementById('confetti-styles')) {
            const style = document.createElement('style');
            style.id = 'confetti-styles';
            style.textContent = `
                @keyframes confetti-fall {
                    to {
                        transform: translateY(100vh) rotate(720deg);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        // Create confetti particles
        const interval = setInterval(() => {
            if (this.confettiActive) {
                for (let i = 0; i < 3; i++) {
                    this.createConfetti();
                }
            } else {
                clearInterval(interval);
            }
        }, 100);

        // Stop after 5 seconds
        setTimeout(() => {
            this.confettiActive = false;
        }, 5000);
    }

    createFirework(x, y) {
        const colors = ['#00ff41', '#0099ff', '#ff0099', '#ffff00'];
        const particleCount = 12;

        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            const angle = (i / particleCount) * Math.PI * 2;
            const velocity = 2 + Math.random() * 2;

            particle.style.cssText = `
                position: fixed;
                width: 4px;
                height: 4px;
                background: ${colors[Math.floor(Math.random() * colors.length)]};
                left: ${x}px;
                top: ${y}px;
                z-index: 9999;
                border-radius: 50%;
                pointer-events: none;
            `;

            document.body.appendChild(particle);

            // Animate particle
            let distance = 0;
            const maxDistance = 50 + Math.random() * 50;
            const animate = () => {
                distance += velocity;
                const currentX = x + Math.cos(angle) * distance;
                const currentY = y + Math.sin(angle) * distance;

                particle.style.left = currentX + 'px';
                particle.style.top = currentY + 'px';
                particle.style.opacity = 1 - (distance / maxDistance);

                if (distance < maxDistance) {
                    requestAnimationFrame(animate);
                } else {
                    particle.remove();
                }
            };
            animate();
        }
    }

    triggerScreenFlash() {
        const flash = document.createElement('div');
        flash.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 255, 65, 0.3);
            z-index: 9998;
            pointer-events: none;
            animation: flash-effect 0.5s ease-out;
        `;

        if (!document.getElementById('flash-styles')) {
            const style = document.createElement('style');
            style.id = 'flash-styles';
            style.textContent = `
                @keyframes flash-effect {
                    0% { opacity: 1; }
                    100% { opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 500);
    }
}

// =============================================================================
// QUOTE GENERATOR
// =============================================================================

class QuoteGenerator {
    constructor() {
        this.currentQuoteIndex = 0;
        this.quoteElement = document.getElementById('success-quote');
        this.typewriterSpeed = 50;
        this.isTyping = false;
    }

    async typeWriter(text, element, speed = this.typewriterSpeed) {
        this.isTyping = true;
        element.textContent = '';
        
        for (let i = 0; i < text.length; i++) {
            if (!this.isTyping) break;
            element.textContent += text.charAt(i);
            await new Promise(resolve => setTimeout(resolve, speed));
        }
        this.isTyping = false;
    }

    getRandomQuote() {
        const randomIndex = Math.floor(Math.random() * INSPIRATIONAL_QUOTES.length);
        return INSPIRATIONAL_QUOTES[randomIndex];
    }

    async displayQuote(quote = null) {
        if (!this.quoteElement) return;

        if (!quote) {
            quote = this.getRandomQuote();
        }

        // Clear current content
        this.quoteElement.innerHTML = `
            <div class="quote-content">
                <div class="quote-text" id="quote-text"></div>
                <div class="quote-author" id="quote-author"></div>
            </div>
            <button class="quote-refresh" title="Generate new quote [Q]">
                <span class="refresh-icon">🔄</span>
                <span class="refresh-text">NEW_QUOTE.EXE</span>
            </button>
        `;

        // Attach click handler to refresh button
        const refreshBtn = this.quoteElement.querySelector('.quote-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.generateNewQuote());
        }

        const textElement = document.getElementById('quote-text');
        const authorElement = document.getElementById('quote-author');

        // Type out the quote
        await this.typeWriter(`"${quote.text}"`, textElement, 30);
        await new Promise(resolve => setTimeout(resolve, 500));
        await this.typeWriter(`— ${quote.author}`, authorElement, 40);

        // Add some sparkle effects
        this.addSparkleEffect();
    }

    addSparkleEffect() {
        const sparkles = ['✨', '⭐', '🌟', '💫'];
        const quoteContent = this.quoteElement.querySelector('.quote-content');
        
        for (let i = 0; i < 3; i++) {
            setTimeout(() => {
                const sparkle = document.createElement('span');
                sparkle.className = 'floating-sparkle';
                sparkle.textContent = sparkles[Math.floor(Math.random() * sparkles.length)];
                sparkle.style.cssText = `
                    position: absolute;
                    right: ${Math.random() * 50 + 10}px;
                    top: ${Math.random() * 50 + 10}px;
                    font-size: ${12 + Math.random() * 8}px;
                    animation: sparkle-float 2s ease-out forwards;
                    pointer-events: none;
                `;
                
                quoteContent.style.position = 'relative';
                quoteContent.appendChild(sparkle);
                
                setTimeout(() => sparkle.remove(), 2000);
            }, i * 300);
        }
    }

    async generateNewQuote() {
        if (this.isTyping) return;
        
        // Add loading state
        this.quoteElement.innerHTML = `
            <div class="loading-quote">
                <span class="loading-text">Generating wisdom...</span>
                <div class="loading-sparkles">
                    <span class="sparkle">✨</span>
                    <span class="sparkle">⭐</span>
                    <span class="sparkle">🌟</span>
                </div>
            </div>
        `;

        // Wait a bit for effect
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Display new quote
        await this.displayQuote();
    }

    initialize() {
        // Start with initial quote after a short delay
        setTimeout(() => {
            this.displayQuote();
        }, 1500);
    }
}

// =============================================================================
// MAIN SUCCESS PAGE CONTROLLER
// =============================================================================

class SuccessPageController {
    constructor() {
        this.celebrationEngine = new CelebrationEngine();
        this.quoteGenerator = new QuoteGenerator();
        this.konamiCode = [];
        this.konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'KeyB', 'KeyA'];
        this.setupEventListeners();
        this.addCSSAnimations();
    }

    setupEventListeners() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
        
        // Celebration effects on mascot click
        const mascot = document.querySelector('.celebration-image');
        if (mascot) {
            mascot.addEventListener('click', () => this.triggerMascotInteraction());
        }

        // Random confetti on achievement click
        const achievement = document.querySelector('.achievement-badge');
        if (achievement) {
            achievement.addEventListener('click', () => this.celebrationEngine.startConfetti());
        }

        // Add ripple effects to buttons
        const buttons = document.querySelectorAll('.action-cmd');
        buttons.forEach(button => {
            button.addEventListener('click', (e) => this.addRippleEffect(e));
            // Delegate actions from data-action attributes
            const action = button.dataset.action;
            if (action === 'status') {
                button.addEventListener('click', () => this.showStatusUpdate());
            } else if (action === 'celebrate') {
                button.addEventListener('click', () => this.celebrationEngine.startConfetti());
            } else if (action === 'easter') {
                button.addEventListener('click', () => this.triggerEasterEgg());
            }
        });


        // Auto-start some celebration effects

        // Implement UI action handlers
        // Bind instance methods as arrow functions so `this` remains the SuccessPageController instance
        this.showStatusUpdate = () => {
            // Simple status overlay or alert if not available
            const overlay = document.getElementById('successOverlay');
            if (overlay) {
                overlay.style.display = 'block';
                setTimeout(() => overlay.style.display = 'none', 3000);
            } else {
                alert('Status: Download progress is being monitored.');
            }
        };

        this.triggerEasterEgg = () => {
            // Ensure celebrationEngine exists before calling
            if (this.celebrationEngine) {
                this.celebrationEngine.createFirework(window.innerWidth/2, window.innerHeight/2);
                this.celebrationEngine.startConfetti();
            } else {
                console.warn('triggerEasterEgg called but celebrationEngine is not initialized');
            }
        };

        setTimeout(() => {
            this.autoStartCelebration();
        }, 1000);
    }

    handleKeyPress(e) {
        // Update Konami code sequence
        this.konamiCode.push(e.code);
        if (this.konamiCode.length > this.konamiSequence.length) {
            this.konamiCode.shift();
        }

        // Check if Konami code is complete
        if (this.konamiCode.length === this.konamiSequence.length &&
            this.konamiCode.every((code, index) => code === this.konamiSequence[index])) {
            this.triggerKonamiEasterEgg();
            this.konamiCode = [];
            return;
        }

        // Handle other shortcuts
        switch(e.key.toLowerCase()) {
            case 'h':
                window.location.href = '/';
                break;
            case 's':
                showStatusUpdate();
                break;
            case 'p':
                triggerCelebration();
                break;
            case 'q':
                this.quoteGenerator.generateNewQuote();
                break;
            case '?':
                showEasterEgg();
                break;
            case 'escape':
                this.closeOverlays();
                break;
        }
    }

    triggerMascotInteraction() {
        const mascot = document.querySelector('.celebration-image');
        if (!mascot) return;

        // Add bounce effect
        mascot.style.animation = 'none';
        setTimeout(() => {
            mascot.style.animation = 'mascot-celebration 0.6s ease-out';
        }, 10);

        // Create firework at mascot position
        const rect = mascot.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        this.celebrationEngine.createFirework(centerX, centerY);

        // Show happy message
        this.showTemporaryMessage("🎉 Quentin is extra happy! 🎉", 2000);
    }

    triggerKonamiEasterEgg() {
        // Ultimate celebration mode
        this.celebrationEngine.triggerScreenFlash();
        this.celebrationEngine.startConfetti();
        
        // Show special message
        this.showTemporaryMessage("🚀 KONAMI CODE ACTIVATED! ULTIMATE CELEBRATION MODE! 🚀", 4000);
        
        // Add special effects to mascot
        const mascot = document.querySelector('.celebration-image');
        if (mascot) {
            mascot.style.filter = 'hue-rotate(180deg) saturate(2)';
            setTimeout(() => {
                mascot.style.filter = '';
            }, 5000);
        }

        // Play some fireworks
        setTimeout(() => {
            for (let i = 0; i < 5; i++) {
                setTimeout(() => {
                    const x = Math.random() * window.innerWidth;
                    const y = Math.random() * window.innerHeight;
                    this.celebrationEngine.createFirework(x, y);
                }, i * 500);
            }
        }, 1000);
    }

    autoStartCelebration() {
        // Start some subtle celebration effects
        this.celebrationEngine.startConfetti();
        
        // Add some initial fireworks
        setTimeout(() => {
            const centerX = window.innerWidth / 2;
            const centerY = window.innerHeight / 3;
            this.celebrationEngine.createFirework(centerX, centerY);
        }, 500);

        setTimeout(() => {
            const centerX = window.innerWidth / 3;
            const centerY = window.innerHeight / 2;
            this.celebrationEngine.createFirework(centerX, centerY);
        }, 1500);
    }

    addRippleEffect(e) {
        const button = e.currentTarget;
        const rect = button.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const ripple = document.createElement('span');
        ripple.className = 'ripple-effect';
        ripple.style.cssText = `
            position: absolute;
            border-radius: 50%;
            background: rgba(0, 255, 65, 0.4);
            transform: scale(0);
            animation: ripple 0.6s linear;
            left: ${x - 5}px;
            top: ${y - 5}px;
            width: 10px;
            height: 10px;
            pointer-events: none;
        `;

        button.style.position = 'relative';
        button.appendChild(ripple);

        setTimeout(() => {
            ripple.remove();
        }, 600);
    }

    showTemporaryMessage(message, duration = 3000) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'temporary-message';
        messageDiv.textContent = message;
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(45deg, #001122, #003344);
            color: #00ff41;
            padding: 15px 25px;
            border: 2px solid #00ff41;
            border-radius: 8px;
            z-index: 10000;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 0 20px rgba(0, 255, 65, 0.3);
            animation: message-appear 0.3s ease-out;
        `;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.style.animation = 'message-disappear 0.3s ease-out forwards';
            setTimeout(() => messageDiv.remove(), 300);
        }, duration);
    }

    closeOverlays() {
        const overlay = document.getElementById('successOverlay');
        if (overlay && overlay.style.display === 'flex') {
            overlay.style.display = 'none';
        }
    }

    addCSSAnimations() {
        if (document.getElementById('success-animations')) return;

        const style = document.createElement('style');
        style.id = 'success-animations';
        style.textContent = `
            @keyframes sparkle-float {
                0% {
                    transform: translateY(0) scale(1);
                    opacity: 1;
                }
                100% {
                    transform: translateY(-30px) scale(0.5);
                    opacity: 0;
                }
            }

            @keyframes mascot-celebration {
                0%, 100% { transform: scale(1) rotate(0deg); }
                25% { transform: scale(1.1) rotate(-5deg); }
                50% { transform: scale(1.15) rotate(5deg); }
                75% { transform: scale(1.1) rotate(-3deg); }
            }

            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }

            @keyframes message-appear {
                from {
                    opacity: 0;
                    transform: translateX(-50%) translateY(-20px);
                }
                to {
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }
            }

            @keyframes message-disappear {
                from {
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }
                to {
                    opacity: 0;
                    transform: translateX(-50%) translateY(-20px);
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// =============================================================================
// GLOBAL FUNCTIONS (called from HTML)
// =============================================================================

function showStatusUpdate() {
    const messages = [
        "🔄 Scanning download queues...",
        "📡 Contacting secret audiobook satellites...",
        "🎯 Your book is #1 in the priority queue!",
        "⚡ Download speed: MAXIMUM OVERDRIVE!",
        "🚀 ETA: Faster than you can say 'chapter one'!"
    ];
    
    let messageIndex = 0;
    const overlay = document.getElementById('successOverlay');
    const content = overlay.querySelector('.overlay-content');
    
    content.innerHTML = `
        <h2>📡 STATUS CHECK INITIATED</h2>
        <div id="status-message" style="font-family: 'Courier New', monospace; font-size: 1.1rem; margin: 20px 0;"></div>
        <div class="loading-bar" style="width: 100%; height: 4px; background: #003; border-radius: 2px; overflow: hidden;">
            <div class="progress" style="height: 100%; background: linear-gradient(90deg, #00ff41, #0099ff); width: 0%; animation: progress-fill 3s ease-out forwards;"></div>
        </div>
    `;
    
    overlay.style.display = 'flex';
    
    const statusElement = document.getElementById('status-message');
    
    function showNextMessage() {
        if (messageIndex < messages.length) {
            statusElement.textContent = messages[messageIndex];
            messageIndex++;
            setTimeout(showNextMessage, 800);
        } else {
            setTimeout(() => {
                overlay.style.display = 'none';
            }, 1500);
        }
    }
    
    showNextMessage();
}

function triggerCelebration() {
    if (window.successController) {
        window.successController.celebrationEngine.startConfetti();
        window.successController.celebrationEngine.triggerScreenFlash();
        
        // Extra fireworks
        for (let i = 0; i < 3; i++) {
            setTimeout(() => {
                const x = Math.random() * window.innerWidth;
                const y = Math.random() * window.innerHeight * 0.7;
                window.successController.celebrationEngine.createFirework(x, y);
            }, i * 300);
        }
        
        window.successController.showTemporaryMessage("🎊 PARTY MODE ACTIVATED! 🎊", 3000);
    }
}

function showEasterEgg() {
    const easterEggs = [
        {
            title: "🎁 SECRET ACHIEVEMENT UNLOCKED!",
            message: "You found the mystery button! Here's a virtual cookie: 🍪",
            extra: "Fun fact: This button was clicked exactly 42 times before you!"
        },
        {
            title: "🔍 CURIOSITY REWARDED!",
            message: "Easter egg hunters get special privileges! You're now a VIP member! ⭐",
            extra: "Your next audiobook will have 23% more awesome per chapter!"
        },
        {
            title: "🎯 EXPLORATION BONUS!",
            message: "You've discovered the developer's secret stash of dad jokes! 🤓",
            extra: "Why don't scientists trust atoms? Because they make up everything... like this message!"
        }
    ];
    
    const randomEgg = easterEggs[Math.floor(Math.random() * easterEggs.length)];
    const overlay = document.getElementById('successOverlay');
    const content = overlay.querySelector('.overlay-content');
    
    content.innerHTML = `
        <h2>${randomEgg.title}</h2>
        <p style="font-size: 1.2rem; margin: 20px 0;">${randomEgg.message}</p>
        <p style="font-style: italic; color: #00cc88;">${randomEgg.extra}</p>
        <div style="margin-top: 20px;">
            <button onclick="document.getElementById('successOverlay').style.display='none'" 
                    style="background: linear-gradient(45deg, #00ff41, #0099ff); color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                AWESOME! [ESC]
            </button>
        </div>
    `;
    
    overlay.style.display = 'flex';
    
    // Add some celebration effects
    if (window.successController) {
        window.successController.celebrationEngine.startConfetti();
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

// Global variables for access from HTML
let successController;
let quoteGenerator;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the main controller
    successController = new SuccessPageController();
    quoteGenerator = successController.quoteGenerator;
    
    // Make them globally accessible
    window.successController = successController;
    window.quoteGenerator = quoteGenerator;
    
    // Initialize quote generator
    quoteGenerator.initialize();
    
    // Add initial CSS for progress bar animation
    if (!document.getElementById('progress-styles')) {
        const style = document.createElement('style');
        style.id = 'progress-styles';
        style.textContent = `
            @keyframes progress-fill {
                from { width: 0%; }
                to { width: 100%; }
            }
        `;
        document.head.appendChild(style);
    }
    
    debugLog('🎉 Success page loaded! Ready for celebration! 🎉');
    debugLog('💡 Tip: Try pressing Q for a new quote, P for party mode, or the Konami code! 🎮');
});