/**
 * Error pages specific JavaScript functionality
 * Handles success, failure, 401, token expired, and rejection pages
 */

const ErrorPages = {
    // Success quotes for success page
    successQuotes: [
        "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
        "The only impossible journey is the one you never begin. - Tony Robbins",
        "Success is walking from failure to failure with no loss of enthusiasm. - Winston Churchill",
        "Don't be afraid to give up the good to go for the great. - John D. Rockefeller",
        "The way to get started is to quit talking and begin doing. - Walt Disney",
        "Innovation distinguishes between a leader and a follower. - Steve Jobs",
        "Your request has been processed with the efficiency of a well-oiled machine! 🤖",
        "Mission accomplished! Time to celebrate with a good audiobook. 📚🎉"
    ],

    // Rejection quotes for rejection page
    rejectionQuotes: [
        "Sometimes rejection is redirection. - Unknown",
        "Rejection is not a reflection of your worth. - Unknown",
        "Every rejection brings you closer to acceptance. - Unknown",
        "Don't take it personally. The algorithm is just being particularly picky today. 🤖",
        "Even the best audiobook requests sometimes need a second chance. 📚",
        "Rejection is just success waiting to happen. - Unknown",
        "The code has spoken. But codes can be wrong... sometimes. 🤷‍♂️",
        "Not all heroes wear capes. Some just need better book recommendations. 📖"
    ],

    // Dad jokes for token expired page
    dadJokes: [
        "Why don't scientists trust atoms? Because they make up everything!",
        "I told my wife she was drawing her eyebrows too high. She looked surprised.",
        "Why don't eggs tell jokes? They'd crack each other up!",
        "What do you call a fake noodle? An impasta!",
        "I'm reading a book on anti-gravity. It's impossible to put down!",
        "Why did the scarecrow win an award? He was outstanding in his field!",
        "What's the best thing about Switzerland? I don't know, but the flag is a big plus.",
        "Why don't tokens ever get old? Because they expire first! 🎭"
    ],

    // Initialize success page
    initSuccessPage: function() {
        if (!document.body.classList.contains('success-page')) return;

        const quoteElement = document.getElementById('success-quote');
        if (quoteElement) {
            const randomQuote = this.successQuotes[Math.floor(Math.random() * this.successQuotes.length)];
            quoteElement.textContent = randomQuote;
            quoteElement.style.fontStyle = 'italic';
            quoteElement.style.marginTop = '1rem';
        }
    },

    // Initialize rejection page
    initRejectionPage: function() {
        if (!document.body.classList.contains('rejection-page')) return;

        const quoteElement = document.getElementById('rejected-quote');
        if (quoteElement) {
            const randomQuote = this.rejectionQuotes[Math.floor(Math.random() * this.rejectionQuotes.length)];
            quoteElement.textContent = randomQuote;
        }

        // Add secret message for easter egg
        window.showSecretMessage = function() {
            alert("🎉 Secret message: Even rejected requests are loved. They just need to find their right home! 💝");
        };
    },

    // Initialize token expired page
    initTokenExpiredPage: function() {
        if (!document.body.classList.contains('token-expired-page')) return;

        const jokeElement = document.getElementById('joke');
        if (jokeElement) {
            const randomJoke = this.dadJokes[Math.floor(Math.random() * this.dadJokes.length)];
            jokeElement.textContent = randomJoke;
        }

        // Cycling footer for token expired page
        const footerElement = document.getElementById('footer');
        if (footerElement) {
            const footerPhrases = [
                "Powered by Quentin's Legendary Overkill Engineering™ 🤖",
                "Time waits for no token (but Quentin's code waits for coffee) ☕",
                "Even expired tokens deserve a good dad joke 🎭",
                "Brought to you by the Department of Digital Security 🔒"
            ];

            let idx = 0;
            setInterval(() => {
                footerElement.textContent = footerPhrases[idx % footerPhrases.length];
                idx++;
            }, 3000);
        }
    },

    // Initialize 401 error page
    init401Page: function() {
        if (!document.body.classList.contains('error-page')) return;

        // Add some interactive elements to make 401 page less boring
        const errorContainer = document.querySelector('.error-container');
        if (errorContainer) {
            errorContainer.addEventListener('click', function() {
                const messages = [
                    "Still unauthorized! 🚫",
                    "Nope, still can't let you in! 🔒",
                    "Access denied with style! 💅",
                    "The digital bouncer says no! 🚪"
                ];
                const randomMessage = messages[Math.floor(Math.random() * messages.length)];

                const tempMessage = document.createElement('div');
                tempMessage.textContent = randomMessage;
                tempMessage.style.cssText = 'position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #ff6b6b; color: white; padding: 1rem; border-radius: 8px; z-index: 1000; font-weight: bold;';
                document.body.appendChild(tempMessage);

                setTimeout(() => {
                    document.body.removeChild(tempMessage);
                }, 2000);
            });
        }
    },

    // Initialize all error page functionality
    init: function() {
        this.initSuccessPage();
        this.initRejectionPage();
        this.initTokenExpiredPage();
        this.init401Page();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    ErrorPages.init();
});
