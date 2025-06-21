// Feature Pages JavaScript - Conflict-free version
(function() {
    'use strict';
    
    // Avoid variable conflicts by wrapping in IIFE
    let localIsDayMode = true;
    let localCurrentTheme = 'light';

    // Theme toggle function
    function toggleTheme() {
        const body = document.body;
        const themeToggle = document.querySelector('.theme-toggle i');
        
        if (body.classList.contains('dark-mode')) {
            body.classList.remove('dark-mode');
            if (themeToggle) {
                themeToggle.classList.remove('fa-sun');
                themeToggle.classList.add('fa-moon');
            }
            localCurrentTheme = 'light';
            localIsDayMode = true;
        } else {
            body.classList.add('dark-mode');
            if (themeToggle) {
                themeToggle.classList.remove('fa-moon');
                themeToggle.classList.add('fa-sun');
            }
            localCurrentTheme = 'dark';
            localIsDayMode = false;
        }
        
        // Store theme preference
        localStorage.setItem('theme', localCurrentTheme);
    }

    // Initialize theme from localStorage
    function initializeTheme() {
        const savedTheme = localStorage.getItem('theme');
        const body = document.body;
        const themeToggle = document.querySelector('.theme-toggle i');
        
        if (savedTheme === 'dark') {
            body.classList.add('dark-mode');
            if (themeToggle) {
                themeToggle.classList.remove('fa-moon');
                themeToggle.classList.add('fa-sun');
            }
            localCurrentTheme = 'dark';
            localIsDayMode = false;
        } else {
            body.classList.remove('dark-mode');
            if (themeToggle) {
                themeToggle.classList.remove('fa-sun');
                themeToggle.classList.add('fa-moon');
            }
            localCurrentTheme = 'light';
            localIsDayMode = true;
        }
    }

    // Make toggleTheme available globally if it doesn't exist
    if (typeof window.toggleTheme === 'undefined') {
        window.toggleTheme = toggleTheme;
    }

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeTheme();
    });

    // Feature navigation functions
    window.navigateToFeature = function(featureName) {
        const featurePages = {
            'flashcards': 'flashcards.html',
            'mindmap': 'mindmap.html',
            'learning-path': 'learning-path.html',
            'sticky-notes': 'sticky-notes.html',
            'exam-booster': 'exam-booster.html',
            'youtube-summarizer': 'youtube-summarizer.html',
            'doc-qna': 'doc-qna.html'
        };
        
        if (featurePages[featureName]) {
            window.location.href = featurePages[featureName];
        }
    };

    // Smooth scrolling for anchor links
    document.addEventListener('click', function(e) {
        if (e.target.matches('a[href^="#"]')) {
            e.preventDefault();
            const target = document.querySelector(e.target.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    });

})();