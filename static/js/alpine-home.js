/**
 * Alpine.js Home Page Component
 * Cyberpunk Audiobook Automation HQ
 */

// Wait for Alpine to be available
let homeRetryCount = 0;
const homeMaxRetries = 50;

function initializeHomePageComponents() {
    if (typeof Alpine === 'undefined') {
        homeRetryCount++;
        if (homeRetryCount < homeMaxRetries) {
            setTimeout(initializeHomePageComponents, 100);
        } else {
            console.error("Alpine.js not available for home components after 5 seconds");
        }
        return;
    }
    console.log("Alpine found, initializing home page components...");

    Alpine.data('homePage', () => ({
        // Loading state
        isLoading: true,
        loadingProgress: 0,
        
        // Dynamic content
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
        
        // Current rotating content
        currentTagline: '',
        currentFooterPhrase: '',
        
        // Stats
        stats: {
            requests: { value: 0, target: 1337, label: 'Requests Processed' },
            uptime: { value: 0, target: 99.9, label: 'Uptime %', suffix: '%' },
            satisfaction: { value: 0, target: 420, label: 'Dad Jokes Deployed' },
            caffeine: { value: 0, target: 9000, label: 'mg Caffeine Consumed' }
        },
        
        // UI state
        showCallPopup: false,
        showAboutDetails: false,
        mascotClicks: 0,
        easterEggActivated: false,
        
        // Particles
        particles: [],
        
        // FAB menu
        fabOpen: false,
        
        init() {
            this.initializeLoading();
            this.initializeContent();
            this.generateParticles();
            this.startRotations();
        },
        
        initializeLoading() {
            // Simulate loading
            const loadingInterval = setInterval(() => {
                this.loadingProgress += Math.random() * 15;
                
                if (this.loadingProgress >= 100) {
                    this.loadingProgress = 100;
                    clearInterval(loadingInterval);
                    
                    setTimeout(() => {
                        this.isLoading = false;
                        this.animateStats();
                    }, 500);
                }
            }, 100);
        },
        
        initializeContent() {
            this.currentTagline = this.taglines[0];
            this.currentFooterPhrase = this.footerPhrases[0];
        },
        
        generateParticles() {
            for (let i = 0; i < 50; i++) {
                this.particles.push({
                    id: i,
                    left: Math.random() * 100,
                    animationDelay: Math.random() * 2,
                    animationDuration: Math.random() * 3 + 2
                });
            }
        },
        
        startRotations() {
            // Tagline rotation
            setInterval(() => {
                const randomIndex = Math.floor(Math.random() * this.taglines.length);
                this.currentTagline = this.taglines[randomIndex];
            }, 4000);
            
            // Footer rotation
            setInterval(() => {
                const randomIndex = Math.floor(Math.random() * this.footerPhrases.length);
                this.currentFooterPhrase = this.footerPhrases[randomIndex];
            }, 6000);
        },
        
        animateStats() {
            Object.keys(this.stats).forEach(key => {
                const stat = this.stats[key];
                const duration = 2000;
                const startTime = Date.now();
                
                const animate = () => {
                    const elapsed = Date.now() - startTime;
                    const progress = Math.min(elapsed / duration, 1);
                    
                    stat.value = Math.floor(stat.target * progress);
                    
                    if (progress < 1) {
                        requestAnimationFrame(animate);
                    }
                };
                
                setTimeout(() => requestAnimationFrame(animate), Math.random() * 500);
            });
        },
        
        // Event handlers
        handleMascotClick() {
            this.mascotClicks++;
            
            if (this.mascotClicks >= 5) {
                this.triggerEasterEgg();
            } else {
                this.$notify(`🐱 Meow! (${this.mascotClicks}/5 for surprise)`, 'info');
            }
        },
        
        triggerEasterEgg() {
            this.easterEggActivated = true;
            this.$notify('🎉 Easter egg activated! You found the secret!', 'success');
            
            // Add some visual flair
            document.body.style.animation = 'rainbow 2s ease-in-out';
            setTimeout(() => {
                document.body.style.animation = '';
                this.easterEggActivated = false;
            }, 2000);
        },
        
        openCallPopup() {
            this.showCallPopup = true;
        },
        
        closeCallPopup() {
            this.showCallPopup = false;
        },
        
        toggleAboutDetails() {
            this.showAboutDetails = !this.showAboutDetails;
        },
        
        toggleFab() {
            this.fabOpen = !this.fabOpen;
        },
        
        // Quick actions
        quickAction(action) {
            switch (action) {
                case 'request':
                    window.location.href = '/request';
                    break;
                case 'status':
                    this.$notify('System status: All green! 🟢', 'success');
                    break;
                case 'help':
                    this.openCallPopup();
                    break;
                case 'theme':
                    this.$notify('Theme switcher coming soon! 🎨', 'info');
                    break;
            }
            this.fabOpen = false;
        },
        
        // Utility methods
        getStatDisplay(stat) {
            return stat.value + (stat.suffix || '');
        },
        
        formatUptime() {
            return this.stats.uptime.value.toFixed(1) + '%';
        }
    }));
}

// Initialize when ready
document.addEventListener('DOMContentLoaded', initializeHomePageComponents);

// Try to define global homePage for direct access if Alpine is already loaded
if (typeof Alpine !== 'undefined') {
    window.homePage = () => ({
        isLoading: true,
        loadingProgress: 0,
        currentTagline: 'Loading...',
        showCallPopup: false,
        easterEggActivated: false,
        stats: {
            requests: { value: 0, target: 1337, label: 'Requests Processed' },
            uptime: { value: 0, target: 99.9, label: 'System Uptime', suffix: '%' },
            satisfaction: { value: 0, target: 420, label: 'Dad Jokes Deployed' },
            caffeine: { value: 0, target: 9000, label: 'mg Caffeine Consumed' }
        },
        getStatDisplay(stat) {
            return stat.value + (stat.suffix || '');
        },
        formatUptime() {
            return '99.9%';
        }
    });
}

initializeHomePageComponents();
