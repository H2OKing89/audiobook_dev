/**
 * TOKEN EXPIRED PAGE JAVASCRIPT
 * Cyberpunk Terminal Theme - Time/Temporal Features
 * Features: Time Facts, Interactive Elements, Keyboard Shortcuts, Easter Eggs
 */

// =============================================================================
// TIME FACTS DATABASE
// =============================================================================

const TIME_FACTS = [
    {
        text: "Time is an illusion. Lunchtime doubly so... but expired tokens are real!",
        author: "Douglas Adams (Temporal Edition)"
    },
    {
        text: "Time flies when you're having fun, but crawls when waiting for expired tokens to refresh.",
        author: "Einstein's Lesser-Known Theory"
    },
    {
        text: "A watched token never expires... actually, that's not true at all.",
        author: "Ancient Internet Proverb"
    },
    {
        text: "Time is money, but expired tokens are just expired. No refunds!",
        author: "Benjamin Franklin (Crypto Edition)"
    },
    {
        text: "The early bird gets the worm, but the early clicker gets the valid token.",
        author: "Digital Age Wisdom"
    },
    {
        text: "Time heals all wounds, but it also expires all tokens. Life is cruel.",
        author: "Temporal Philosophy 101"
    },
    {
        text: "In the future, all tokens will be eternal. We're just not there yet.",
        author: "Time Traveler Anonymous"
    },
    {
        text: "Lost time is never found again, but lost tokens can be regenerated!",
        author: "Benjamin Franklin (Optimistic Version)"
    },
    {
        text: "Time is the longest distance between two places... and two token validations.",
        author: "Tennessee Williams (Tech Support)"
    },
    {
        text: "Yesterday is history, tomorrow is a mystery, today's token is expired.",
        author: "Master Oogway (IT Department)"
    },
    {
        text: "Time and tide wait for no one, but tokens wait for exactly 24 hours.",
        author: "Geoffrey Chaucer (API Designer)"
    },
    {
        text: "The only time you have too much of is the time between token expiry and renewal.",
        author: "Murphy's Token Law"
    },
    {
        text: "Time is what keeps everything from happening at once. Tokens prevent everything from happening at all.",
        author: "John Wheeler (Security Consultant)"
    },
    {
        text: "Time is relative, but token expiration is absolute.",
        author: "Albert Einstein (System Administrator)"
    },
    {
        text: "You can't buy time, but you can definitely waste it clicking expired tokens.",
        author: "Modern Life Philosophy"
    },
    {
        text: "Time is a great teacher, but unfortunately it kills all its pupils... and tokens.",
        author: "Louis Hector Berlioz (IT Trainer)"
    },
    {
        text: "The trouble is, you think you have time... for your token to remain valid.",
        author: "Buddha (DevOps Engineer)"
    },
    {
        text: "Time moves in one direction: forward. Tokens move in one direction: expired.",
        author: "Stephen Hawking (Token Theorist)"
    },
    {
        text: "Time is an illusion that helps things make sense. Expired tokens help nothing make sense.",
        author: "Adventure Time (Development Edition)"
    },
    {
        text: "Time waits for no one, especially not for procrastinators with expired tokens.",
        author: "Life Lessons 2.0"
    }
];

// =============================================================================
// TIME VISUALIZATION EFFECTS
// =============================================================================

class TimeEffects {
    constructor() {
        this.clockParticles = [];
        this.maxParticles = 20;
        this.colors = ['#ff8c00', '#ffb347', '#ffd700', '#ff6b35'];
    }

    createTimeParticle() {
        if (this.clockParticles.length >= this.maxParticles) return;

        const particle = document.createElement('div');
        const symbols = ['⏰', '🕐', '⏳', '⌛', '🕑', '🕒', '🕓'];
        const symbol = symbols[Math.floor(Math.random() * symbols.length)];

        particle.className = 'time-particle';
        particle.textContent = symbol;
        particle.style.cssText = `
            position: fixed;
            font-size: ${12 + Math.random() * 8}px;
            color: ${this.colors[Math.floor(Math.random() * this.colors.length)]};
            left: ${Math.random() * window.innerWidth}px;
            top: ${window.innerHeight + 10}px;
            z-index: 9999;
            pointer-events: none;
            text-shadow: 0 0 10px currentColor;
            animation: time-float ${3 + Math.random() * 2}s ease-out forwards;
        `;

        document.body.appendChild(particle);
        this.clockParticles.push(particle);

        // Clean up when animation ends
        particle.addEventListener('animationend', () => {
            if (particle.parentNode) {
                particle.parentNode.removeChild(particle);
                const index = this.clockParticles.indexOf(particle);
                if (index > -1) this.clockParticles.splice(index, 1);
            }
        });
    }

    startTimeRain() {
        // Add time floating CSS animation if not already present
        if (!document.getElementById('time-effects-styles')) {
            const style = document.createElement('style');
            style.id = 'time-effects-styles';
            style.textContent = `
                @keyframes time-float {
                    0% {
                        transform: translateY(0) rotate(0deg);
                        opacity: 1;
                    }
                    100% {
                        transform: translateY(-${window.innerHeight + 100}px) rotate(360deg);
                        opacity: 0;
                    }
                }

                @keyframes time-distortion {
                    0%, 100% {
                        transform: scale(1) skew(0deg);
                        filter: hue-rotate(0deg);
                    }
                    50% {
                        transform: scale(1.05) skew(2deg);
                        filter: hue-rotate(30deg);
                    }
                }

                @keyframes clock-glitch {
                    0%, 100% {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    10% {
                        transform: translateX(-2px);
                        opacity: 0.8;
                    }
                    20% {
                        transform: translateX(2px);
                        opacity: 1;
                    }
                    30% {
                        transform: translateX(-1px);
                        opacity: 0.9;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        // Create time particles periodically
        const interval = setInterval(() => {
            this.createTimeParticle();
        }, 500);

        // Stop after 10 seconds
        setTimeout(() => {
            clearInterval(interval);
        }, 10000);
    }

    createTimeRipple(x, y) {
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: fixed;
            left: ${x - 25}px;
            top: ${y - 25}px;
            width: 50px;
            height: 50px;
            border: 2px solid #ff8c00;
            border-radius: 50%;
            transform: scale(0);
            animation: time-ripple 1s ease-out forwards;
            pointer-events: none;
            z-index: 9998;
        `;

        if (!document.getElementById('ripple-styles')) {
            const style = document.createElement('style');
            style.id = 'ripple-styles';
            style.textContent = `
                @keyframes time-ripple {
                    to {
                        transform: scale(4);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(ripple);
        setTimeout(() => ripple.remove(), 1000);
    }

    triggerTimeDistortion() {
        const mascot = document.querySelector('.time-image');
        if (mascot) {
            mascot.style.animation = 'time-distortion 2s ease-in-out';
            setTimeout(() => {
                mascot.style.animation = 'time-confusion 3s ease-in-out infinite';
            }, 2000);
        }
    }

    triggerClockGlitch() {
        const clockElements = document.querySelectorAll('.clock-overlay, .time-icon, .clock');
        clockElements.forEach((element, index) => {
            setTimeout(() => {
                element.style.animation = 'clock-glitch 0.5s ease-out';
                setTimeout(() => {
                    element.style.animation = '';
                }, 500);
            }, index * 100);
        });
    }
}

// =============================================================================
// TIME FACT GENERATOR
// =============================================================================

class TimeFactGenerator {
    constructor() {
        this.currentFactIndex = 0;
        this.factElement = document.getElementById('time-fact');
        this.typewriterSpeed = 40;
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

    getRandomFact() {
        const randomIndex = Math.floor(Math.random() * TIME_FACTS.length);
        return TIME_FACTS[randomIndex];
    }

    async displayFact(fact = null) {
        if (!this.factElement) return;

        if (!fact) {
            fact = this.getRandomFact();
        }

        // Clear current content
        this.factElement.innerHTML = `
            <div class="fact-content">
                <div class="fact-text" id="fact-text"></div>
                <div class="fact-author" id="fact-author"></div>
            </div>
            <button class="fact-refresh" onclick="timeFactGenerator.generateNewFact()" title="Generate new time fact [T]">
                <span class="refresh-icon">🔄</span>
                <span class="refresh-text">NEW_FACT.EXE</span>
            </button>
        `;

        const textElement = document.getElementById('fact-text');
        const authorElement = document.getElementById('fact-author');

        // Type out the fact
        await this.typeWriter(`"${fact.text}"`, textElement, 25);
        await new Promise(resolve => setTimeout(resolve, 500));
        await this.typeWriter(`— ${fact.author}`, authorElement, 35);

        // Add some clock effects
        this.addClockEffect();
    }

    addClockEffect() {
        const clocks = ['🕐', '🕑', '🕒', '🕓', '🕔', '🕕'];
        const factContent = this.factElement.querySelector('.fact-content');

        for (let i = 0; i < 2; i++) {
            setTimeout(() => {
                const clock = document.createElement('span');
                clock.className = 'floating-clock';
                clock.textContent = clocks[Math.floor(Math.random() * clocks.length)];
                clock.style.cssText = `
                    position: absolute;
                    right: ${Math.random() * 40 + 10}px;
                    top: ${Math.random() * 40 + 10}px;
                    font-size: ${14 + Math.random() * 6}px;
                    animation: clock-float 2s ease-out forwards;
                    pointer-events: none;
                    color: #ffd700;
                `;

                if (!document.getElementById('clock-float-styles')) {
                    const style = document.createElement('style');
                    style.id = 'clock-float-styles';
                    style.textContent = `
                        @keyframes clock-float {
                            0% {
                                transform: translateY(0) rotate(0deg);
                                opacity: 1;
                            }
                            100% {
                                transform: translateY(-20px) rotate(180deg);
                                opacity: 0;
                            }
                        }
                    `;
                    document.head.appendChild(style);
                }

                factContent.style.position = 'relative';
                factContent.appendChild(clock);

                setTimeout(() => clock.remove(), 2000);
            }, i * 400);
        }
    }

    async generateNewFact() {
        if (this.isTyping) return;

        // Add loading state
        this.factElement.innerHTML = `
            <div class="loading-fact">
                <span class="loading-text">Consulting temporal database...</span>
                <div class="loading-clocks">
                    <span class="clock">🕐</span>
                    <span class="clock">🕑</span>
                    <span class="clock">🕒</span>
                </div>
            </div>
        `;

        // Wait a bit for effect
        await new Promise(resolve => setTimeout(resolve, 1200));

        // Display new fact
        await this.displayFact();
    }

    initialize() {
        // Start with initial fact after a short delay
        setTimeout(() => {
            this.displayFact();
        }, 2000);
    }
}

// =============================================================================
// MAIN TOKEN EXPIRED PAGE CONTROLLER
// =============================================================================

class TokenExpiredController {
    constructor() {
        this.timeEffects = new TimeEffects();
        this.timeFactGenerator = new TimeFactGenerator();
        this.konamiCode = [];
        this.konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'KeyB', 'KeyA'];
        this.setupEventListeners();
        this.addInteractiveElements();
    }

    setupEventListeners() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));

        // Time effects on mascot click
        const mascot = document.querySelector('.time-image');
        if (mascot) {
            mascot.addEventListener('click', () => this.triggerMascotInteraction());
        }

        // Click effects on time elements
        const timeElements = document.querySelectorAll('.time-icon, .clock-overlay');
        timeElements.forEach(element => {
            element.addEventListener('click', (e) => {
                this.timeEffects.createTimeRipple(e.clientX, e.clientY);
                this.timeEffects.triggerClockGlitch();
            });
        });

        // Add ripple effects to buttons
        const buttons = document.querySelectorAll('.action-cmd');
        buttons.forEach(button => {
            button.addEventListener('click', (e) => this.addRippleEffect(e));
        });

        // Auto-start some time effects
        setTimeout(() => {
            this.autoStartTimeEffects();
        }, 1500);
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
            this.triggerKonamiTimeTravel();
            this.konamiCode = [];
            return;
        }

        // Handle other shortcuts
        switch(e.key.toLowerCase()) {
            case 'h':
                window.location.href = '/';
                break;
            case 't':
                this.timeFactGenerator.generateNewFact();
                break;
            case '?':
                showTimeHelp();
                break;
            case 'escape':
                this.closeOverlays();
                break;
            // Special time travel combination
            case 'e':
                if (e.shiftKey && e.ctrlKey) {
                    this.triggerTimeTravel();
                }
                break;
        }
    }

    triggerMascotInteraction() {
        const mascot = document.querySelector('.time-image');
        if (!mascot) return;

        // Add time distortion effect
        this.timeEffects.triggerTimeDistortion();

        // Create time ripple at mascot position
        const rect = mascot.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        this.timeEffects.createTimeRipple(centerX, centerY);

        // Show time message
        this.showTemporaryMessage("⏰ Quentin is confused about time! ⏰", 2500);

        // Start time rain
        this.timeEffects.startTimeRain();
    }

    triggerKonamiTimeTravel() {
        // Ultimate time travel mode
        this.showTemporaryMessage("🚀 KONAMI TIME TRAVEL ACTIVATED! 🚀", 4000);

        // Add special effects
        this.timeEffects.triggerTimeDistortion();
        this.timeEffects.triggerClockGlitch();
        this.timeEffects.startTimeRain();

        // Create multiple time ripples
        for (let i = 0; i < 5; i++) {
            setTimeout(() => {
                const x = Math.random() * window.innerWidth;
                const y = Math.random() * window.innerHeight;
                this.timeEffects.createTimeRipple(x, y);
            }, i * 200);
        }

        // Add special styling to page
        const body = document.body;
        body.style.filter = 'hue-rotate(60deg) saturate(1.5)';
        setTimeout(() => {
            body.style.filter = '';
        }, 5000);
    }

    autoStartTimeEffects() {
        // Start some subtle time effects
        this.timeEffects.startTimeRain();

        // Create initial time ripple
        setTimeout(() => {
            const centerX = window.innerWidth / 2;
            const centerY = window.innerHeight / 3;
            this.timeEffects.createTimeRipple(centerX, centerY);
        }, 1000);
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
            background: rgba(255, 140, 0, 0.4);
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
            background: linear-gradient(45deg, #2d1b0a, #3d2814);
            color: #ff8c00;
            padding: 15px 25px;
            border: 2px solid #ff8c00;
            border-radius: 8px;
            z-index: 10000;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            text-align: center;
            box-shadow: 0 0 20px rgba(255, 140, 0, 0.3);
            animation: message-appear 0.3s ease-out;
        `;

        document.body.appendChild(messageDiv);

        setTimeout(() => {
            messageDiv.style.animation = 'message-disappear 0.3s ease-out forwards';
            setTimeout(() => messageDiv.remove(), 300);
        }, duration);
    }

    closeOverlays() {
        const overlay = document.getElementById('helpOverlay');
        if (overlay && overlay.style.display === 'flex') {
            overlay.style.display = 'none';
        }
    }

    addInteractiveElements() {
        // Add click counter to time elements
        let clickCount = 0;
        const timeElements = document.querySelectorAll('.time-icon, .time-image');

        timeElements.forEach(element => {
            element.addEventListener('click', () => {
                clickCount++;
                if (clickCount === 5) {
                    this.showTemporaryMessage("🕰️ Time Master Achievement Unlocked! 🕰️", 3000);
                } else if (clickCount === 10) {
                    this.showTemporaryMessage("⏰ Temporal Obsession Detected! ⏰", 3000);
                    this.timeEffects.startTimeRain();
                }
            });
        });
    }
}

// =============================================================================
// GLOBAL FUNCTIONS (called from HTML)
// =============================================================================

function showTimeHelp() {
    const helpMessages = [
        "🕰️ Time help loading...",
        "⏳ Consulting temporal documentation...",
        "📚 Fact: Tokens expire to prevent time paradoxes!",
        "🔄 Solution: Just go home and get a fresh token!",
        "💡 Remember: Time waits for no one, especially not expired tokens!"
    ];

    let messageIndex = 0;
    const overlay = document.getElementById('helpOverlay');
    const content = overlay.querySelector('.overlay-content');

    content.innerHTML = `
        <h2>🕰️ TEMPORAL ASSISTANCE</h2>
        <div id="help-message" style="font-family: 'Courier New', monospace; font-size: 1.1rem; margin: 20px 0;"></div>
        <div class="help-progress" style="width: 100%; height: 4px; background: #3d2814; border-radius: 2px; overflow: hidden;">
            <div class="progress" style="height: 100%; background: linear-gradient(90deg, #ff8c00, #ffd700); width: 0%; animation: progress-fill 4s ease-out forwards;"></div>
        </div>
        <div class="help-tip">💡 Pro tip: Time machines are still in beta testing!</div>
    `;

    overlay.style.display = 'flex';

    const helpElement = document.getElementById('help-message');

    function showNextMessage() {
        if (messageIndex < helpMessages.length) {
            helpElement.textContent = helpMessages[messageIndex];
            messageIndex++;
            setTimeout(showNextMessage, 1000);
        } else {
            setTimeout(() => {
                overlay.style.display = 'none';
            }, 2000);
        }
    }

    showNextMessage();
}

function explainTokens() {
    const overlay = document.getElementById('helpOverlay');
    const content = overlay.querySelector('.overlay-content');

    content.innerHTML = `
        <h2>🔑 TOKEN SCIENCE EXPLAINED</h2>
        <div style="text-align: left; margin: 20px 0;">
            <p><strong>What is a token?</strong></p>
            <p>Think of it as a digital movie ticket - good for one show only!</p>
            <br>
            <p><strong>Why do they expire?</strong></p>
            <p>For security! Like milk, tokens go bad after a while.</p>
            <br>
            <p><strong>How long do they last?</strong></p>
            <p>Usually 24 hours, or until someone uses them.</p>
            <br>
            <p><strong>Can I get a new one?</strong></p>
            <p>Absolutely! Just go back home and request again!</p>
        </div>
        <div style="margin-top: 20px;">
            <button onclick="document.getElementById('helpOverlay').style.display='none'"
                    style="background: linear-gradient(45deg, #ff8c00, #ffb347); color: #1a0d00; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                Got it! [ESC]
            </button>
        </div>
    `;

    overlay.style.display = 'flex';
}

function timeTravel() {
    const destinations = [
        "🏺 Ancient Egypt (No WiFi Available)",
        "🦖 Jurassic Period (Tokens Not Yet Invented)",
        "🚀 Year 3024 (Tokens Are Quantum)",
        "🎭 Renaissance (Tokens Written on Parchment)",
        "🤖 Robot Future (Tokens Are Sentient)",
        "🌌 Parallel Universe (Tokens Never Expire!)"
    ];

    const destination = destinations[Math.floor(Math.random() * destinations.length)];
    const overlay = document.getElementById('helpOverlay');
    const content = overlay.querySelector('.overlay-content');

    content.innerHTML = `
        <h2>🚀 TIME TRAVEL INITIATED</h2>
        <div style="font-size: 1.2rem; margin: 20px 0;">
            <p>Destination: <strong>${destination}</strong></p>
            <p style="margin-top: 15px;">🔄 Calibrating temporal coordinates...</p>
            <p>⚡ Charging flux capacitor...</p>
            <p>🌀 Opening space-time portal...</p>
            <p style="color: #ff6b35; font-weight: bold;">❌ ERROR: Time travel not covered by warranty!</p>
        </div>
        <div style="background: #3d2814; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="font-style: italic;">Disclaimer: Quentin's Time Travel™ is purely fictional. Please use regular transportation methods.</p>
        </div>
        <div style="margin-top: 20px;">
            <button onclick="document.getElementById('helpOverlay').style.display='none'"
                    style="background: linear-gradient(45deg, #ff8c00, #ffb347); color: #1a0d00; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                Stay in Present [ESC]
            </button>
        </div>
    `;

    overlay.style.display = 'flex';

    // Add time travel effects
    if (window.tokenController) {
        window.tokenController.timeEffects.startTimeRain();
        window.tokenController.timeEffects.triggerTimeDistortion();
    }
}

// =============================================================================
// INITIALIZATION
// =============================================================================

// Global variables for access from HTML
let tokenController;
let timeFactGenerator;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the main controller
    tokenController = new TokenExpiredController();
    timeFactGenerator = tokenController.timeFactGenerator;

    // Make them globally accessible
    window.tokenController = tokenController;
    window.timeFactGenerator = timeFactGenerator;

    // Initialize time fact generator
    timeFactGenerator.initialize();

    // Add CSS for progress bar animation
    if (!document.getElementById('progress-styles')) {
        const style = document.createElement('style');
        style.id = 'progress-styles';
        style.textContent = `
            @keyframes progress-fill {
                from { width: 0%; }
                to { width: 100%; }
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

    debugLog('⏰ Token expired page loaded! Time effects ready! ⏰');
    debugLog('💡 Tip: Try pressing T for time facts, clicking the mascot, or the Konami code for time travel! 🚀');
});
