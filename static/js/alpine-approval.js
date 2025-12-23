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
        terminalInterval: null,
        _scannerInterval: null,
        
        init() {
            this.initializeTerminal();
            this.startScanner();
            setTimeout(() => {
                this.isLoading = false;
            }, 1000);
        },
        
        initializeTerminal() {
            const fullLines = [
                '> Initializing approval protocol...',
                '> Loading book metadata...',
                '> Activating decision matrix...',
                '> Standing by for human input...'
            ];
            
            this.terminalLines = [];
            
            // Simulate typing effect
            let index = 0;
            this.terminalInterval = setInterval(() => {
                if (index < fullLines.length) {
                    this.terminalLines.push(fullLines[index]);
                    index++;
                } else {
                    clearInterval(this.terminalInterval);
                    this.terminalInterval = null;
                }
            }, 800);
        },
        
        destroy() {
            // Clean up intervals on component teardown
            if (this.terminalInterval) {
                clearInterval(this.terminalInterval);
                this.terminalInterval = null;
            }
            if (this._scannerInterval) {
                clearInterval(this._scannerInterval);
                this._scannerInterval = null;
            }
        },
        
        startScanner() {
            // Simulate the scanning line animation
            // Clear existing interval if present to avoid duplicates
            if (this._scannerInterval) {
                clearInterval(this._scannerInterval);
                this._scannerInterval = null;
            }
            this._scannerInterval = setInterval(() => {
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
                const link = this.$el.querySelector('.approve-matrix');
                if (link && link.href) {
                    window.location.href = link.href;
                } else {
                    console.error('[approval] Approve link (.approve-matrix) not found or missing href.');
                    this.$notify('🔗 Approval link not available. Please try again or use the admin dashboard.', 'error');
                }
            }, 1000);
        },
        
        reject() {
            this.selectedAction = 'reject';
            this.triggerGlitch();
            this.$notify('🚫 Rejection protocol activated!', 'error');
            
            setTimeout(() => {
                const link = this.$el.querySelector('.reject-matrix');
                if (link && link.href) {
                    window.location.href = link.href;
                } else {
                    console.error('[approval] Reject link (.reject-matrix) not found or missing href.');
                    this.$notify('🔗 Rejection link not available. Please try again or use the admin dashboard.', 'error');
                }
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
