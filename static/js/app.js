/**
 * Common JavaScript functionality for the Audiobook Approval System
 */

// Auto-close countdown functionality
function startAutoCloseCountdown(seconds) {
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
}

// Home page functionality
function initializeHomePage() {
    // Enhanced rotating taglines with more personality
    const taglines = [
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
        "Your personal audiobook butler, minus the fancy accent. 🎩"
    ];
    
    let tagIdx = 0;
    function cycleTagline() {
        const tagElement = document.getElementById('dynamicTag');
        if (tagElement) {
            tagElement.classList.add('tagline-fade');
            setTimeout(() => {
                tagElement.innerText = taglines[tagIdx % taglines.length];
                tagIdx++;
            }, 250);
            setTimeout(cycleTagline, 5000);
        }
    }
    
    // Enhanced cycling footer with more wit
    const footerPhrases = [
        "Powered by Quentin's Legendary Overkill Engineering™ 🤖",
        "Serving pages with more precision than a Swiss chronometer ⏰",
        "No audiobooks were harmed in the making of this automation 📚",
        "All systems nominal. Humans? Well, that's debatable 🤷‍♂️",
        "Built with more caffeine than sleep, as tradition demands ☕",
        "Running on 24-core Threadripper and pure, unfiltered determination 💪",
        "🔄 Refresh for another dose of Quentin wisdom",
        "Where code meets chaos and somehow produces order 🌪️➡️📊",
        "Automating your audiobooks with the fury of a thousand algorithms ⚡",
        "Making your digital library so organized, Marie Kondo would weep 🧹✨"
    ];
    
    let footerIdx = 0;
    function cycleFooter() {
        const footerElement = document.getElementById('footer');
        if (footerElement) {
            footerElement.classList.add('footer-fade');
            setTimeout(() => {
                footerElement.innerText = footerPhrases[footerIdx % footerPhrases.length];
                footerIdx++;
            }, 250);
            setTimeout(cycleFooter, 4000);
        }
    }
    
    // Cat tail easter egg
    function initCatTailEasterEgg() {
        const catTail = document.querySelector('.cat-tail');
        const tip = document.getElementById('easterTip');
        
        if (catTail && tip) {
            catTail.addEventListener('click', () => {
                tip.style.display = 'block';
                setTimeout(() => { 
                    tip.style.display = 'none'; 
                }, 3400);
            });
        }
    }
    
    // High contrast mode toggle
    function initContrastToggle() {
        const contrastToggle = document.getElementById('contrastToggle');
        if (contrastToggle) {
            contrastToggle.addEventListener('click', () => {
                document.body.classList.toggle('contrast');
                contrastToggle.classList.toggle('active');
                
                const mainBox = document.querySelector('.main-box');
                const footer = document.querySelector('.footer');
                
                if (document.body.classList.contains('contrast')) {
                    document.body.style.background = "#000";
                    document.body.style.color = "#ff69b4";
                    if (mainBox) mainBox.style.background = "#23243a";
                    if (footer) footer.style.color = "#ff69b4";
                } else {
                    document.body.style.background = "";
                    document.body.style.color = "";
                    if (mainBox) mainBox.style.background = "";
                    if (footer) footer.style.color = "";
                }
            });
        }
    }
    
    // Enhanced contact popup functionality
    function initContactPopup() {
        const contactBtn = document.querySelector('[data-action="contact"]');
        const popup = document.getElementById('call-quentin-popup');
        const closeBtn = document.querySelector('[data-action="close-popup"]');
        
        if (contactBtn && popup) {
            contactBtn.addEventListener('click', (e) => {
                e.preventDefault();
                popup.style.display = 'block';
                // Add some fun randomization to the popup message
                const messages = [
                    "🤖 <strong>Beep boop!</strong> Quentin is currently busy teaching robots how to be more sarcastic.",
                    "🔧 <strong>Status Update:</strong> Quentin is deep in code, probably arguing with a semicolon somewhere.",
                    "☕ <strong>Coffee Break Alert:</strong> Quentin is refueling with his 47th cup of coffee today.",
                    "🧠 <strong>Brain Loading...</strong> Quentin is processing approximately 247 automation ideas simultaneously.",
                    "🎭 <strong>Plot Twist:</strong> Quentin is actually three raccoons in a trench coat, but they're really good at coding."
                ];
                const randomMessage = messages[Math.floor(Math.random() * messages.length)];
                const messageEl = popup.querySelector('.popup-message');
                if (messageEl) {
                    messageEl.innerHTML = randomMessage + 
                        '<br><br>💬 In the meantime, you can find him on GitHub, probably explaining why his 47-line function "needs to be that way for performance reasons."' +
                        '<br><br>🎭 <em>Fun fact:</em> Quentin once spent 3 hours optimizing a function that saved 0.2 milliseconds. He regrets nothing.';
                }
            });
        }
        
        if (closeBtn && popup) {
            closeBtn.addEventListener('click', () => {
                popup.style.display = 'none';
            });
        }
        
        // Close popup when clicking outside
        if (popup) {
            popup.addEventListener('click', (e) => {
                if (e.target === popup) {
                    popup.style.display = 'none';
                }
            });
        }
    }
    
    // Initialize all home page functionality
    cycleTagline();
    cycleFooter();
    initCatTailEasterEgg();
    initContrastToggle();
    initContactPopup();
}

// Initialize auto-close on page load if countdown element exists
document.addEventListener('DOMContentLoaded', function() {
    const countdownElement = document.getElementById('countdown');
    if (countdownElement) {
        // Get the initial countdown value from the element
        const initialSeconds = parseInt(countdownElement.textContent) || 10;
        startAutoCloseCountdown(initialSeconds);
    }
    
    // Initialize home page if we're on the home page
    if (document.querySelector('.mascot-banner') && document.getElementById('dynamicTag')) {
        initializeHomePage();
    }
});

// Theme toggle functionality
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', savedTheme);
});

// Form validation helpers
function validateCSRFToken(form) {
    const csrfToken = form.querySelector('input[name="csrf_token"]');
    if (csrfToken && (!csrfToken.value || csrfToken.value.length < 32)) {
        console.error('Invalid CSRF token');
        return false;
    }
    return true;
}

// Enhanced form submission with security checks
function secureFormSubmit(form, callback) {
    if (!validateCSRFToken(form)) {
        alert('Security validation failed. Please refresh and try again.');
        return false;
    }
    
    if (callback && typeof callback === 'function') {
        return callback(form);
    }
    
    return true;
}

// Sanitize text content to prevent XSS
function sanitizeText(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Safe HTML insertion
function safeSetHTML(element, html) {
    // Simple XSS prevention - only allow basic formatting
    const sanitized = html
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        .replace(/javascript:/gi, '')
        .replace(/on\w+\s*=/gi, '');
    
    element.innerHTML = sanitized;
}

// Debug logging (only in development)
function debugLog(message, data = null) {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('[DEBUG]', message, data);
    }
}

// Rejection page functionality
function initializeRejectionPage() {
    // Create floating particles
    function createParticles() {
        const particlesContainer = document.getElementById('particles');
        if (!particlesContainer) return;
        
        for (let i = 0; i < 20; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 6 + 's';
            particle.style.animationDuration = (4 + Math.random() * 4) + 's';
            particlesContainer.appendChild(particle);
        }
    }
    
    // Show secret consolation message
    window.showSecretMessage = function() {
        const messages = [
            "🎉 Plot twist: Rejection is just redirection!",
            "🌟 Fun fact: Even Shakespeare got rejected 37 times!",
            "🚀 Success is just failure that kept trying!",
            "💫 Your request was too awesome for our current timeline!",
            "🎪 Rejection is just the universe's way of saying 'not yet'!",
            "🎭 Fun fact: The word 'no' is just 'yes' spelled backwards in mirror world!",
            "🔮 Your request is waiting for the perfect cosmic alignment!",
            "🎨 Consider this rejection a masterpiece of constructive criticism!",
            "🚁 Sometimes you need to crash land before you can fly!",
            "🎪 Welcome to the exclusive club of 'Almost But Not Quite'!"
        ];
        const randomMessage = messages[Math.floor(Math.random() * messages.length)];
        alert(randomMessage);
    };
    
    // Initialize particles
    createParticles();
    
    // Load witty rejection quotes
    loadRejectionQuotes();
}

// Load rejection quotes
function loadRejectionQuotes() {
    const rejectionQuotes = [
        "\"The only way to avoid criticism is to say nothing, do nothing, and be nothing.\" - Aristotle (But you did something, so... progress?)",
        "\"Rejection is not a reflection of your worth, it's a redirection to your path.\" - Someone Very Wise",
        "\"I have not failed. I've just found 10,000 ways that won't work.\" - Edison (You found one more!)",
        "\"Success is going from failure to failure without losing your enthusiasm.\" - Churchill",
        "\"Every rejection is a step closer to acceptance.\" - The Universe, probably",
        "\"Plot twist: This rejection is actually a blessing in disguise wearing a really good costume.\"",
        "\"Fun fact: Even Google's first investor said 'no' the first time. Look how that turned out!\"",
        "\"Your request was so unique, our algorithm needed time to appreciate its genius.\"",
        "\"Rejection is just success taking the scenic route.\"",
        "\"Consider this rejection a plot device in your success story.\""
    ];
    
    const quoteElement = document.getElementById('rejected-quote');
    if (quoteElement) {
        const randomQuote = rejectionQuotes[Math.floor(Math.random() * rejectionQuotes.length)];
        quoteElement.textContent = randomQuote;
    }
}

// Success page functionality
function initializeSuccessPage() {
    const jokes = [
        "Automation win unlocked! 🎧",
        "That was smoother than a freshly buttered cat.",
        "Mission accomplished. Quentin would be proud.",
        "All green lights, no manual intervention needed.",
        "You did it! (Or at least, the robot did.)"
    ];
    
    const quoteElement = document.getElementById('success-quote');
    if (quoteElement) {
        quoteElement.innerText = jokes[Math.floor(Math.random() * jokes.length)];
    }
}

// Token expired page functionality
function initializeTokenExpiredPage() {
    // Rotating joke
    const jokes = [
        "Much like socks in the dryer, this link has vanished into the unknown.",
        "Looks like this token got Isekai'd. Try again for a second life!",
        "This link was last seen with Schrödinger's cat. Status: Uncertain.",
        "404: Token not found. Did you feed it after midnight?",
        "The approval fairy took this link to a better place.",
        "This link hit its expiration like a slow SSD—RIP.",
        "If this was a potion, it's gone flat.",
        "Error: Token is now wandering with Dungeon Crawler Carl.",
        "Much like a lost anime filler episode, this link will never be seen again."
    ];
    
    const jokeElement = document.getElementById('joke');
    if (jokeElement) {
        jokeElement.innerText = jokes[Math.floor(Math.random() * jokes.length)];
    }

    // Cycling footer
    const footerPhrases = [
        "Automated by Quentin's Overkill Automation™ 🤖",
        "Page served by a caffeinated Quentin script.",
        "No tokens were harmed in the making of this page.",
        "All systems nominal. Humans? That's another story.",
        "Built with more enthusiasm than sleep.",
        "Powered by 24-core Threadripper and pure stubbornness.",
        "🔄 Refresh for a different error joke."
    ];
    
    let footerIdx = 0;
    function cycleFooter() {
        const footerElement = document.getElementById('footer');
        if (footerElement) {
            footerElement.innerText = footerPhrases[footerIdx % footerPhrases.length];
            footerIdx++;
            setTimeout(cycleFooter, 3700);
        }
    }
    cycleFooter();

    // Copy error info functionality
    const copyBtn = document.getElementById('copyErrorBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const msg = `Token: [REDACTED]
Page: Token Expired
Time: ${new Date().toLocaleString()}`;
            
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(msg).then(() => {
                    copyBtn.innerText = "Copied!";
                    setTimeout(() => {
                        copyBtn.innerText = "Copy Error Info";
                    }, 1500);
                }).catch(() => {
                    // Fallback for older browsers
                    fallbackCopyTextToClipboard(msg, copyBtn);
                });
            } else {
                fallbackCopyTextToClipboard(msg, copyBtn);
            }
        });
    }

    // Cat tail easter egg
    const catTail = document.querySelector('.cat-tail');
    const tip = document.getElementById('easterTip');
    if (catTail && tip) {
        catTail.addEventListener('click', () => {
            tip.style.display = 'block';
            setTimeout(() => { 
                tip.style.display = 'none'; 
            }, 3800);
        });
    }

    // High contrast mode toggle for token expired page
    const contrastToggle = document.getElementById('contrastToggle');
    if (contrastToggle) {
        contrastToggle.addEventListener('click', () => {
            document.body.classList.toggle('contrast');
            contrastToggle.classList.toggle('active');
            
            const infoBox = document.querySelector('.info-box');
            const footer = document.querySelector('.footer');
            
            if (document.body.classList.contains('contrast')) {
                document.body.style.background = "#000";
                document.body.style.color = "#ffb347";
                if (infoBox) infoBox.style.background = "#222";
                if (footer) footer.style.color = "#ffb347";
            } else {
                document.body.style.background = "";
                document.body.style.color = "";
                if (infoBox) infoBox.style.background = "";
                if (footer) footer.style.color = "";
            }
        });
    }
}

// Fallback copy function for older browsers
function fallbackCopyTextToClipboard(text, button) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful && button) {
            button.innerText = "Copied!";
            setTimeout(() => {
                button.innerText = "Copy Error Info";
            }, 1500);
        }
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
    }
    
    document.body.removeChild(textArea);
}

// Enhanced DOMContentLoaded event handler
document.addEventListener('DOMContentLoaded', function() {
    // Auto-close countdown functionality
    const countdownElement = document.getElementById('countdown');
    if (countdownElement) {
        const initialSeconds = parseInt(countdownElement.textContent) || 10;
        startAutoCloseCountdown(initialSeconds);
    }
    
    // Initialize based on page content
    if (document.querySelector('.mascot-banner') && document.getElementById('dynamicTag')) {
        initializeHomePage();
    } else if (document.getElementById('rejected-quote')) {
        initializeRejectionPage();
    } else if (document.getElementById('success-quote')) {
        initializeSuccessPage();
    } else if (document.getElementById('joke') && document.getElementById('easterTip')) {
        initializeTokenExpiredPage();
    }
    
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', savedTheme);
});
