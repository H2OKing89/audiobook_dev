/**
 * Home page specific JavaScript functionality
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
        "Proof that over-engineering can be beautiful. 🛠️💎"
    ],

    // Enhanced cycling footer with more wit
    footerPhrases: [
        "Powered by Quentin's Legendary Overkill Engineering™ 🤖",
        "Serving pages with more precision than a Swiss chronometer ⏰",
        "No audiobooks were harmed in the making of this automation 📚",
        "All systems nominal. Humans? Well, that's debatable 🤷‍♂️",
        "Built with more caffeine than sleep, as tradition demands ☕",
        "Running on 24-core Threadripper and pure, unfiltered determination 💪",
        "🔄 Refresh for another dose of Quentin wisdom",
        "Where code meets chaos and somehow produces order 🌪️➡️📊",
        "Automating your audiobooks with the fury of a thousand algorithms ⚡",
        "Making your digital library so organized, Marie Kondo would weep 🧹✨",
        "Defying the laws of software development since day one 🚀",
        "Cyberpunk vibes meet audiobook organization. Deal with it. 😎"
    ],

    // Initialize dynamic tagline cycling
    initTaglineCycling: function() {
        let tagIdx = 0;
        const tagElement = document.getElementById('dynamicTag');
        if (!tagElement) return;

        const cycleTagline = () => {
            tagElement.classList.add('tagline-fade');
            setTimeout(() => {
                tagElement.innerText = this.taglines[tagIdx % this.taglines.length];
                tagIdx++;
                tagElement.classList.remove('tagline-fade');
            }, 250);
            setTimeout(cycleTagline, 6000); // Slower cycling for better readability
        };

        // Start cycling after initial load
        setTimeout(cycleTagline, 2000);
    },

    // Initialize footer cycling
    initFooterCycling: function() {
        let footerIdx = 0;
        const footerElement = document.getElementById('footer');
        if (!footerElement) return;

        const cycleFooter = () => {
            footerElement.classList.add('footer-fade');
            setTimeout(() => {
                footerElement.innerText = this.footerPhrases[footerIdx % this.footerPhrases.length];
                footerIdx++;
                footerElement.classList.remove('footer-fade');
            }, 250);
            setTimeout(cycleFooter, 5000);
        };

        // Start cycling
        setTimeout(cycleFooter, 3000);
    },

    // Cat tail easter egg
    initCatTailEasterEgg: function() {
        const catTail = document.querySelector('.cat-tail');
        const tip = document.getElementById('easterTip');
        
        if (catTail && tip) {
            catTail.addEventListener('click', () => {
                tip.style.display = 'block';
                setTimeout(() => { 
                    tip.style.display = 'none'; 
                }, 4000);
            });
        }
    },

    // Enhanced popup functionality
    initPopupFunctionality: function() {
        const contactButton = document.querySelector('[data-action="contact"]');
        const popup = document.getElementById('call-quentin-popup');
        const closeButtons = document.querySelectorAll('[data-action="close-popup"]');
        const backdrop = document.querySelector('.popup-backdrop');

        if (contactButton && popup) {
            contactButton.addEventListener('click', function() {
                popup.style.display = 'flex';
                // Add animation class
                setTimeout(() => {
                    popup.classList.add('show');
                }, 10);
            });
        }

        // Close popup functionality
        const closePopup = () => {
            if (popup) {
                popup.classList.remove('show');
                setTimeout(() => {
                    popup.style.display = 'none';
                }, 300);
            }
        };

        closeButtons.forEach(button => {
            button.addEventListener('click', closePopup);
        });

        if (backdrop) {
            backdrop.addEventListener('click', closePopup);
        }

        // Close on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && popup && popup.style.display === 'flex') {
                closePopup();
            }
        });
    },

    // Uptime counter animation
    initUptimeCounter: function() {
        const uptimeElement = document.getElementById('uptimeCounter');
        if (!uptimeElement) return;

        let uptime = 99.9;
        let increasing = true;

        setInterval(() => {
            if (increasing) {
                uptime += 0.001;
                if (uptime >= 99.999) increasing = false;
            } else {
                uptime -= 0.002;
                if (uptime <= 99.9) increasing = true;
            }
            uptimeElement.textContent = uptime.toFixed(3) + '%';
        }, 2000);
    },

    // Add smooth scrolling for internal links
    initSmoothScrolling: function() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    },

    // Add hover effects for feature cards
    initFeatureCardEffects: function() {
        const featureCards = document.querySelectorAll('.feature-card');
        featureCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-8px) scale(1.02)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
            });
        });
    },

    // Initialize all home page functionality
    init: function() {
        // Only run on home page
        if (!document.body.classList.contains('home-page')) return;

        console.log('🎧 Initializing Audiobook HQ homepage...');
        
        this.initTaglineCycling();
        this.initFooterCycling();
        this.initCatTailEasterEgg();
        this.initPopupFunctionality();
        this.initUptimeCounter();
        this.initSmoothScrolling();
        this.initFeatureCardEffects();

        console.log('✅ Homepage initialization complete!');
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    HomePage.init();
});
