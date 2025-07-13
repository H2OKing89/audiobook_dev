/**
 * Alpine.js Approval Page Component
 * Enhanced cyberpunk approval interface
 */

document.addEventListener('alpine:init', () => {
    Alpine.data('approvalPage', () => ({
        // Page state
        isLoading: true,
        scannerActive: true,
        showTechSpecs: false,
        showDescription: false,
        
        // Book data (will be populated from template)
        bookData: {
            title: '',
            author: '',
            narrator: '',
            duration: '',
            size: '',
            description: ''
        },
        
        // Decision state
        decisionMade: false,
        selectedAction: null,
        
        // Visual effects
        glitchActive: false,
        terminalLines: [],
        
        init() {
            this.initializeTerminal();
            this.startScanner();
            setTimeout(() => {
                this.isLoading = false;
            }, 1000);
        },
        
        initializeTerminal() {
            this.terminalLines = [
                '> Initializing approval protocol...',
                '> Loading book metadata...',
                '> Activating decision matrix...',
                '> Standing by for human input...'
            ];
            
            // Simulate typing effect
            let index = 0;
            const typeInterval = setInterval(() => {
                if (index < this.terminalLines.length) {
                    // Simulate typing with a delay
                    setTimeout(() => {
                        index++;
                    }, 500);
                } else {
                    clearInterval(typeInterval);
                }
            }, 800);
        },
        
        startScanner() {
            // Simulate the scanning line animation
            setInterval(() => {
                this.scannerActive = !this.scannerActive;
            }, 2000);
        },
        
        toggleTechSpecs() {
            this.showTechSpecs = !this.showTechSpecs;
        },
        
        toggleDescription() {
            this.showDescription = !this.showDescription;
        },
        
        triggerGlitch() {
            this.glitchActive = true;
            setTimeout(() => {
                this.glitchActive = false;
            }, 500);
        },
        
        // Decision handlers
        approve() {
            this.selectedAction = 'approve';
            this.triggerGlitch();
            this.$notify('🎉 Approval sequence initiated!', 'success');
            
            setTimeout(() => {
                window.location.href = this.$el.querySelector('.approve-matrix').href;
            }, 1000);
        },
        
        reject() {
            this.selectedAction = 'reject';
            this.triggerGlitch();
            this.$notify('🚫 Rejection protocol activated!', 'error');
            
            setTimeout(() => {
                window.location.href = this.$el.querySelector('.reject-matrix').href;
            }, 1000);
        },
        
        // Copy functionality
        copyBookInfo() {
            const bookInfo = `
Title: ${this.bookData.title}
Author: ${this.bookData.author}
Narrator: ${this.bookData.narrator}
Duration: ${this.bookData.duration}
Size: ${this.bookData.size}
            `.trim();
            
            this.$copy(bookInfo).then(() => {
                this.$notify('📋 Book info copied to clipboard!', 'success');
            });
        },
        
        // System stats simulation
        getSystemStats() {
            return {
                uptime: '99.9%',
                cpu: Math.floor(Math.random() * 20) + 5 + '%',
                memory: Math.floor(Math.random() * 200) + 300 + 'MB',
                dadJokes: '∞'
            };
        }
    }));
});
