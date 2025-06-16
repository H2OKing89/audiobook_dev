// 🚫 REJECTION PAGE - INTERACTIVE CONSOLATION SYSTEM 🚫

document.addEventListener('DOMContentLoaded', function() {
    initRejectionPage();
});

function initRejectionPage() {
    loadDadJoke();
    setupKeyboardShortcuts();
    setupEasterEggs();
    startHologramEffects();
    
    console.log('🚫 Rejection consolation system activated');
}

// Dad Joke Loader
const rejectionJokes = [
    "Why don't audiobooks ever get tired? Because they never lose their voice!",
    "What do you call a rejected audiobook? A silent treatment!",
    "Why did the audiobook break up with the e-reader? It wanted someone who would listen!",
    "What's an audiobook's favorite type of music? Spoken word, obviously!",
    "Why don't audiobooks make good comedians? Their timing is always off!",
    "What did the audiobook say when it got rejected? 'That's not how this story ends!'",
    "Why are rejected audiobooks like bad wifi? They just can't connect!",
    "What's the difference between a rejected audiobook and a broken speaker? One's silent by choice!",
    "Why don't audiobooks ever win at poker? Everyone can hear their tells!",
    "What do you call an audiobook that won't stop talking? A reject with attachment issues!"
];

function loadDadJoke() {
    const jokeDisplay = document.getElementById('rejection-joke');
    if (!jokeDisplay) return;
    
    // Show loading animation for 2 seconds
    setTimeout(() => {
        const randomJoke = rejectionJokes[Math.floor(Math.random() * rejectionJokes.length)];
        jokeDisplay.innerHTML = `
            <div class="joke-text">
                <span class="joke-icon">😄</span>
                <span class="joke-content">"${randomJoke}"</span>
            </div>
            <div class="joke-rating">
                <span class="rating-label">DAD_JOKE_QUALITY:</span>
                <span class="rating-value">${Math.floor(Math.random() * 20) + 80}% Groan-worthy</span>
            </div>
        `;
        
        // Add CSS for joke styling
        if (!document.querySelector('#joke-styles')) {
            const style = document.createElement('style');
            style.id = 'joke-styles';
            style.textContent = `
                .joke-text {
                    display: flex;
                    align-items: flex-start;
                    gap: 1rem;
                    margin-bottom: 1rem;
                }
                .joke-icon {
                    font-size: 1.5rem;
                    flex-shrink: 0;
                }
                .joke-content {
                    color: #ffbd2e;
                    font-style: italic;
                    line-height: 1.4;
                    flex: 1;
                }
                .joke-rating {
                    display: flex;
                    justify-content: space-between;
                    font-size: 0.8rem;
                    color: #888;
                    border-top: 1px solid rgba(255, 189, 46, 0.2);
                    padding-top: 0.5rem;
                }
                .rating-value {
                    color: #00ff88;
                    font-weight: bold;
                }
            `;
            document.head.appendChild(style);
        }
    }, 2000);
}

// Keyboard Shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        if (document.activeElement.tagName === 'INPUT' || 
            document.activeElement.tagName === 'TEXTAREA') {
            return;
        }
        
        switch(e.key.toLowerCase()) {
            case 'h':
                e.preventDefault();
                window.location.href = '/';
                break;
                
            case 'a':
                e.preventDefault();
                window.location.href = 'mailto:admin@example.com';
                break;
                
            case 'r':
                e.preventDefault();
                showRetryMessage();
                break;
                
            case '?':
                e.preventDefault();
                triggerEasterEgg();
                break;
                
            case 'escape':
                hideEasterEgg();
                break;
        }
    });
}

// Action Functions
function showRetryMessage() {
    showTemporaryMessage(
        '🔄 RETRY PROTOCOL INITIATED',
        'Suggestion: Try turning your request off and on again. Or add more cowbell.',
        'info'
    );
}

function triggerEasterEgg() {
    const easterEgg = document.getElementById('easterEgg');
    if (easterEgg) {
        easterEgg.classList.add('show');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            hideEasterEgg();
        }, 5000);
    }
}

function hideEasterEgg() {
    const easterEgg = document.getElementById('easterEgg');
    if (easterEgg) {
        easterEgg.classList.remove('show');
    }
}

function showTemporaryMessage(title, message, type = 'info') {
    // Create temporary message overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: rgba(0, 0, 0, 0.95);
        border: 2px solid ${type === 'info' ? '#00f5ff' : '#ff006e'};
        border-radius: 12px;
        padding: 2rem;
        box-shadow: 0 0 30px ${type === 'info' ? 'rgba(0, 245, 255, 0.5)' : 'rgba(255, 0, 110, 0.5)'};
        text-align: center;
        z-index: 1001;
        max-width: 400px;
        animation: messageAppear 0.3s ease-out;
    `;
    
    overlay.innerHTML = `
        <h3 style="color: ${type === 'info' ? '#00f5ff' : '#ff006e'}; margin: 0 0 1rem 0; text-shadow: 0 0 10px ${type === 'info' ? 'rgba(0, 245, 255, 0.5)' : 'rgba(255, 0, 110, 0.5)'};">
            ${title}
        </h3>
        <p style="color: #fff; margin: 0; font-size: 1rem; line-height: 1.4;">
            ${message}
        </p>
    `;
    
    document.body.appendChild(overlay);
    
    // Remove after 3 seconds
    setTimeout(() => {
        if (overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    }, 3000);
    
    // Click to dismiss
    overlay.addEventListener('click', () => {
        if (overlay.parentNode) {
            overlay.parentNode.removeChild(overlay);
        }
    });
}

// Hologram Effects
function startHologramEffects() {
    const hologramImage = document.querySelector('.hologram-image');
    if (!hologramImage) return;
    
    // Random glitch effects
    setInterval(() => {
        if (Math.random() < 0.1) { // 10% chance every interval
            hologramImage.style.filter = 'brightness(0.8) contrast(1.2) hue-rotate(180deg) saturate(1.5)';
            setTimeout(() => {
                hologramImage.style.filter = 'brightness(0.8) contrast(1.2) hue-rotate(180deg)';
            }, 100);
        }
    }, 2000);
    
    // Click interaction
    hologramImage.addEventListener('click', () => {
        showTemporaryMessage(
            '🤖 QUENTIN_AI.EXE SAYS:',
            '"Don\'t worry, rejection builds character! Plus, I hear the appeals process is surprisingly lenient..."',
            'info'
        );
    });
}

// Easter Egg Sequences
const konamiCode = [
    'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
    'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
    'KeyB', 'KeyA'
];
let konamiIndex = 0;

document.addEventListener('keydown', function(e) {
    if (e.code === konamiCode[konamiIndex]) {
        konamiIndex++;
        if (konamiIndex === konamiCode.length) {
            activateKonamiEasterEgg();
            konamiIndex = 0;
        }
    } else {
        konamiIndex = 0;
    }
});

function activateKonamiEasterEgg() {
    showTemporaryMessage(
        '🎮 KONAMI CODE ACTIVATED!',
        'SECRET ACHIEVEMENT UNLOCKED: "Master of Rejection"\n\nBonus: +30 Confidence Points\nReward: Virtual pat on the back 🫳',
        'info'
    );
    
    // Add some fun visual effects
    const body = document.body;
    body.style.animation = 'rainbow 2s linear';
    
    // Add rainbow animation if not present
    if (!document.querySelector('#rainbow-keyframes')) {
        const style = document.createElement('style');
        style.id = 'rainbow-keyframes';
        style.textContent = `
            @keyframes rainbow {
                0% { filter: hue-rotate(0deg); }
                25% { filter: hue-rotate(90deg); }
                50% { filter: hue-rotate(180deg); }
                75% { filter: hue-rotate(270deg); }
                100% { filter: hue-rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
    
    setTimeout(() => {
        body.style.animation = '';
    }, 2000);
}

// Add some helpful console messages
console.log('🎭 REJECTION CONSOLE COMMANDS:');
console.log('  triggerEasterEgg() - Show easter egg');
console.log('  showRetryMessage() - Show retry info');
console.log('  loadDadJoke() - Load new dad joke');
console.log('  Konami Code - ↑↑↓↓←→←→BA for secret');
console.log('  Keyboard shortcuts: H=Home, A=Appeal, R=Retry, ?=Easter Egg');

// Export functions for global access
window.showRetryMessage = showRetryMessage;
window.triggerEasterEgg = triggerEasterEgg;
window.loadDadJoke = loadDadJoke;