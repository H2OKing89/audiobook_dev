// Approval Page JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initApprovalPage();
});

function initApprovalPage() {
    // Add confirmation dialogs for approval actions
    addActionConfirmations();
    
    // Add interactive elements
    addCoverImageEffects();
    addButtonAnimations();
    addTooltips();
    
    // Add keyboard shortcuts
    addKeyboardShortcuts();
    
    console.log('Approval page initialized');
}

function addActionConfirmations() {
    const approveBtn = document.querySelector('.btn-approve');
    const rejectBtn = document.querySelector('.btn-reject');
    
    if (approveBtn) {
        approveBtn.addEventListener('click', function(e) {
            const confirmed = confirm('Are you sure you want to approve this audiobook request?');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    }
    
    if (rejectBtn) {
        rejectBtn.addEventListener('click', function(e) {
            const confirmed = confirm('Are you sure you want to reject this audiobook request?');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    }
}

function addCoverImageEffects() {
    const coverContainer = document.querySelector('.cover-container');
    
    if (coverContainer) {
        // Add click to view full size (if cover exists)
        const coverImg = coverContainer.querySelector('.audiobook-cover');
        if (coverImg) {
            coverContainer.style.cursor = 'pointer';
            coverContainer.addEventListener('click', function() {
                // Create modal overlay for full-size image
                const modal = document.createElement('div');
                modal.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.9);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 10000;
                    cursor: pointer;
                    backdrop-filter: blur(10px);
                `;
                
                const fullImg = document.createElement('img');
                fullImg.src = coverImg.src;
                fullImg.style.cssText = `
                    max-width: 90%;
                    max-height: 90%;
                    border-radius: 15px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
                `;
                
                modal.appendChild(fullImg);
                document.body.appendChild(modal);
                
                // Close modal on click
                modal.addEventListener('click', function() {
                    document.body.removeChild(modal);
                });
                
                // Close modal on escape key
                const closeOnEscape = function(e) {
                    if (e.key === 'Escape') {
                        document.body.removeChild(modal);
                        document.removeEventListener('keydown', closeOnEscape);
                    }
                };
                document.addEventListener('keydown', closeOnEscape);
            });
        }
    }
}

function addButtonAnimations() {
    const buttons = document.querySelectorAll('.btn');
    
    buttons.forEach(button => {
        // Add ripple effect on click
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = button.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
            `;
            
            button.appendChild(ripple);
            
            setTimeout(() => {
                if (ripple.parentNode) {
                    ripple.parentNode.removeChild(ripple);
                }
            }, 600);
        });
    });
    
    // Add CSS for ripple animation if not already present
    if (!document.querySelector('#ripple-keyframes')) {
        const style = document.createElement('style');
        style.id = 'ripple-keyframes';
        style.textContent = `
            @keyframes ripple {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

function addTooltips() {
    const detailItems = document.querySelectorAll('.detail-item');
    
    detailItems.forEach(item => {
        const label = item.querySelector('.detail-label');
        const value = item.querySelector('.detail-value');
        
        if (label && value) {
            // Add tooltip for truncated content
            if (value.scrollWidth > value.clientWidth) {
                value.title = value.textContent.trim();
            }
        }
    });
}

function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Only activate shortcuts if no input is focused
        if (document.activeElement.tagName === 'INPUT' || 
            document.activeElement.tagName === 'TEXTAREA') {
            return;
        }
        
        switch(e.key.toLowerCase()) {
            case 'a':
                e.preventDefault();
                const approveBtn = document.querySelector('.btn-approve');
                if (approveBtn) {
                    approveBtn.click();
                }
                break;
                
            case 'r':
                e.preventDefault();
                const rejectBtn = document.querySelector('.btn-reject');
                if (rejectBtn) {
                    rejectBtn.click();
                }
                break;
                
            case 'escape':
                // Close any open modals or go back
                const modal = document.querySelector('[style*="position: fixed"]');
                if (modal) {
                    modal.click();
                } else {
                    window.history.back();
                }
                break;
        }
    });
    
    // Add keyboard shortcut hints
    addKeyboardHints();
}

function addKeyboardHints() {
    const approveBtn = document.querySelector('.btn-approve');
    const rejectBtn = document.querySelector('.btn-reject');
    
    if (approveBtn) {
        const hint = document.createElement('small');
        hint.textContent = ' (Press A)';
        hint.style.opacity = '0.7';
        hint.style.fontSize = '0.8em';
        approveBtn.appendChild(hint);
    }
    
    if (rejectBtn) {
        const hint = document.createElement('small');
        hint.textContent = ' (Press R)';
        hint.style.opacity = '0.7';
        hint.style.fontSize = '0.8em';
        rejectBtn.appendChild(hint);
    }
}

// Helper function to create loading state
function setButtonLoading(button, isLoading) {
    if (isLoading) {
        button.style.opacity = '0.7';
        button.style.pointerEvents = 'none';
        button.innerHTML = '<i class="icon-loading"></i> Processing...';
    }
}

// Add CSS for loading spinner
document.addEventListener('DOMContentLoaded', function() {
    if (!document.querySelector('#loading-spinner')) {
        const style = document.createElement('style');
        style.id = 'loading-spinner';
        style.textContent = `
            .icon-loading::before {
                content: "⟳";
                animation: spin 1s linear infinite;
            }
            
            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
    }
});
