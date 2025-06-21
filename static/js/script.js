// Global state
let currentContent = '';
let isDayMode = localStorage.getItem('dayMode') === 'true';
let simpleRating = 0; // Add this missing variable

// Utility functions - moved to top to avoid reference errors
function getFileIcon(fileType) {
    const icons = {
        'pdf': 'pdf',
        'docx': 'word',
        'doc': 'word',
        'txt': 'alt',
        'md': 'markdown'
    };
    return icons[fileType] || 'file';
}

function getFeatureIcon(featureType) {
    const icons = {
        'flashcards': 'brain',
        'mcqs': 'question-circle',
        'mindmap': 'project-diagram',
        'learning-path': 'route',
        'sticky-notes': 'sticky-note',
        'exam-questions': 'trophy'
    };
    return icons[featureType] || 'file';
}

function getFeatureName(featureType) {
    const names = {
        'flashcards': 'Flashcards',
        'mcqs': 'Quiz',
        'mindmap': 'Mind Map',
        'learning-path': 'Learning Path',
        'sticky-notes': 'Sticky Notes',
        'exam-questions': 'Exam Questions'
    };
    return names[featureType] || featureType;
}

// Initialize theme
if (isDayMode) {
    document.body.classList.add('day-mode');
}

// SIDEBAR TOGGLE FUNCTIONALITY - Matching your screenshot behavior
document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    const sidebarCloseBtn = document.getElementById('sidebarClose');
    const sidebar = document.getElementById('sidebar');
    const mainContainer = document.querySelector('.main-container');
    const openIcon = sidebarToggleBtn?.querySelector('.icon-open');
    const closeIcon = sidebarToggleBtn?.querySelector('.icon-close');

    // Track sidebar state
    let sidebarOpen = false;

    function openSidebar() {
        sidebarOpen = true;
        sidebar.classList.add('open');
        mainContainer.classList.add('shifted');
        sidebarToggleBtn.classList.add('active');
        if (openIcon) openIcon.style.display = 'none';
        if (closeIcon) closeIcon.style.display = 'inline';
        sidebarToggleBtn.setAttribute('aria-expanded', 'true');
    }

    function closeSidebar() {
        sidebarOpen = false;
        sidebar.classList.remove('open');
        mainContainer.classList.remove('shifted');
        sidebarToggleBtn.classList.remove('active');
        if (openIcon) openIcon.style.display = 'inline';
        if (closeIcon) closeIcon.style.display = 'none';
        sidebarToggleBtn.setAttribute('aria-expanded', 'false');
    }

    function toggleSidebar() {
        if (sidebarOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }

    // Event listeners
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            toggleSidebar();
        });
    }

    if (sidebarCloseBtn) {
        sidebarCloseBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            closeSidebar();
        });
    }

    // Close sidebar when clicking outside
    document.addEventListener('click', function(e) {
        if (sidebar && sidebar.classList.contains('open') && 
            !sidebar.contains(e.target) && 
            sidebarToggleBtn && !sidebarToggleBtn.contains(e.target)) {
            closeSidebar();
        }
    });

    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && sidebarOpen) {
            closeSidebar();
        }
    });
});

// FIXED THEME TOGGLE FUNCTION
function toggleTheme() {
    isDayMode = !isDayMode;
    localStorage.setItem('dayMode', isDayMode);
    document.body.classList.toggle('day-mode', isDayMode);

    // Sidebar theme sync
    const sidebarElement = document.getElementById('sidebar');
    if (sidebarElement) {
        if (isDayMode) {
            sidebarElement.classList.add('day-mode');
        } else {
            sidebarElement.classList.remove('day-mode');
        }
    }

    updateThemeIcons();
}

function updateThemeIcons() {
    // Update all theme toggle icons
    const themeIcons = document.querySelectorAll('.theme-toggle i');
    const themeTexts = document.querySelectorAll('.theme-toggle span');
    
    themeIcons.forEach(icon => {
        if (isDayMode) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        }
    });
    
    themeTexts.forEach(text => {
        text.textContent = isDayMode ? 'Light Mode' : 'Dark Mode';
    });
}

// Create particle system
function createParticles() {
    const particlesContainer = document.getElementById('particles');
    if (!particlesContainer) return;

    const numberOfParticles = 50;

    for (let i = 0; i < numberOfParticles; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.left = Math.random() * 100 + '%';
        particle.style.animationDelay = Math.random() * 8 + 's';
        particle.style.animationDuration = (Math.random() * 3 + 5) + 's';
        particlesContainer.appendChild(particle);
    }
}

// File upload handling
const fileInputElement = document.getElementById('fileInput');
if (fileInputElement) {
    fileInputElement.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const fileName = file.name;
            const uploadText = document.querySelector('.upload-text');
            const uploadArea = document.querySelector('.upload-area');
            if (uploadText) uploadText.textContent = `Selected: ${fileName}`;
            if (uploadArea) uploadArea.style.borderColor = '#34d399';
        }
    });
}

// Generate content function
async function generateContent(type) {
    const fileInput = document.getElementById('fileInput');
    const textInput = document.getElementById('textInput');
    
    if (!fileInput.files[0] && !textInput.value.trim()) {
        alert('Please upload a file or enter some text first!');
        return;
    }

    showLoading(type);

    try {
        const formData = new FormData();
        if (fileInput.files[0]) {
            formData.append('file', fileInput.files[0]);
        }
        if (textInput.value.trim()) {
            formData.append('text', textInput.value.trim());
        }

        const endpoint = `/api/generate-${type}`;
        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayResults(type, data);

    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while generating content. Please try again.');
        hideLoading();
    }
}

// Show loading state
function showLoading(type) {
    const resultsSection = document.getElementById('results-section');
    if (resultsSection) {
        resultsSection.style.display = 'block';
        resultsSection.innerHTML = `
            <div class="text-center" style="padding: 3rem; background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(20px); border-radius: 20px; border: 2px solid rgba(255, 255, 255, 0.1);">
                <div class="loading" style="margin: 0 auto 1rem;"></div>
                <h3 style="color: var(--text-primary);">Generating ${type.replace('-', ' ')}...</h3>
                <p style="color: var(--text-secondary);">Please wait while our AI processes your content</p>
            </div>
        `;
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }
}

// Hide loading state
function hideLoading() {
    const resultsSection = document.getElementById('results-section');
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
}

// Display results
function displayResults(type, data) {
    const resultsSection = document.getElementById('results-section');
    let html = '';

    switch(type) {
        case 'flashcards': html = createFlashcardsHTML(data); break;
        case 'mcqs': html = createMCQsHTML(data); break;
        case 'mindmap': html = createMindMapHTML(data); break;
        case 'learning-path': html = createLearningPathHTML(data); break;
        case 'sticky-notes': html = createStickyNotesHTML(data); break;
        case 'exam-questions': html = createExamQuestionsHTML(data); break;
    }

    if (resultsSection) {
        resultsSection.innerHTML = html;
        resultsSection.style.display = 'block';
        
        // Animate results
        setTimeout(() => {
            resultsSection.querySelectorAll('.animate-in').forEach((el, index) => {
                setTimeout(() => {
                    el.style.opacity = '1';
                    el.style.transform = 'translateY(0)';
                }, index * 100);
            });
        }, 100);
    }
}

// Create Flashcards HTML
function createFlashcardsHTML(flashcards) {
    let html = `
        <div style="background: var(--glass); backdrop-filter: blur(12px); border-radius: 20px; padding: 2.5rem;">
            <h2 class="text-center" style="color: white; margin-bottom: 2rem;">
                <i class="fas fa-brain" style="color: #f87171;"></i> Smart Flashcards
            </h2>
            <p class="text-center" style="color: rgba(255, 255, 255, 0.8); margin-bottom: 2rem;">
                Click cards to flip and reveal answers
            </p>
            <div class="flashcards-grid">
        `;

    flashcards.forEach((card, index) => {
        html += `
            <div class="flashcard animate-in" style="opacity: 0; transform: translateY(20px);" onclick="flipCard(this)">
                <div class="flashcard-inner">
                    <div class="flashcard-front">
                        <div>
                            <div style="font-weight: 600; color: #333; font-size: 1.1rem; line-height: 1.5;">
                                ${card.question}
                            </div>
                            <div style="position: absolute; top: 15px; right: 15px; background: ${getDifficultyColor(card.difficulty)}; color: white; padding: 0.3rem 0.8rem; border-radius: 15px; font-size: 0.7rem; font-weight: 600;">
                                ${card.difficulty.toUpperCase()}
                            </div>
                            <div style="position: absolute; bottom: 15px; left: 50%; transform: translateX(-50%); color: #999; font-size: 0.8rem;">
                                <i class="fas fa-sync-alt"></i> Click to flip
                            </div>
                        </div>
                    </div>
                    <div class="flashcard-back">
                        <div style="font-weight: 500; line-height: 1.6;">
                            ${card.answer}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    html += `
            </div>
            <div class="text-center mt-2">
                <button class="btn btn-primary" onclick="generateContent('mcqs')" style="margin-right: 1rem;">
                    <i class="fas fa-question-circle"></i> Generate Quiz
                </button>
                <button class="btn" style="background: var(--accent); color: white;" onclick="shuffleFlashcards()">
                    <i class="fas fa-random"></i> Shuffle Cards
                </button>
            </div>
        </div>
    `;
    return html;
}

// Create MCQs HTML
function createMCQsHTML(mcqs) {
    let html = `
        <div style="background: var(--glass); backdrop-filter: blur(12px); border-radius: 20px; padding: 2.5rem;">
            <h2 class="text-center" style="color: white; margin-bottom: 2rem;">
                <i class="fas fa-question-circle" style="color: #2dd4bf;"></i> Interactive Quiz
            </h2>
    `;

    mcqs.forEach((mcq, index) => {
        html += `
            <div class="quiz-container animate-in" style="opacity: 0; transform: translateY(20px);">
                <div class="question-card">
                    <div class="question-number">Question ${index + 1} of ${mcqs.length}</div>
                    <div class="question-text">${mcq.question}</div>
                    <div class="options-grid">
        `;

        mcq.options.forEach((option, optIndex) => {
            html += `
                <button class="option-btn" onclick="selectAnswer(this, ${optIndex}, ${mcq.correct_answer}, '${mcq.explanation.replace(/'/g, "\\'")}', ${index})">
                    <span style="font-weight: bold; margin-right: 0.5rem;">${String.fromCharCode(65 + optIndex)}.</span>
                    ${option}
                </button>
            `;
        });

        html += `
                </div>
                <div class="explanation" id="explanation-${index}">
                    <h4 style="color: var(--primary); margin-bottom: 1rem;">
                        <i class="fas fa-lightbulb"></i> Explanation
                    </h4>
                    <p>${mcq.explanation}</p>
                </div>
            </div>
        </div>
    `;
    });

    html += '</div>';
    return html;
}

// Create Mind Map HTML
function createMindMapHTML(mindmap) {
    let html = `
        <div style="background: var(--glass); backdrop-filter: blur(12px); border-radius: 20px; padding: 2.5rem;">
            <h2 class="text-center" style="color: white; margin-bottom: 2rem;">
                <i class="fas fa-project-diagram" style="color: #facc15;"></i> ${mindmap.title}
            </h2>
            <div class="mindmap-container animate-in" style="opacity: 0; transform: translateY(20px);">
                <svg class="mindmap-svg" viewBox="0 0 800 650"></svg>
                <div class="mindmap-content">
                    <div class="mindmap-node central" style="top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--primary);">
                        ${mindmap.title}
                    </div>
    `;

    if (mindmap.nodes && mindmap.nodes.length > 0) {
        const centerX = 400;
        const centerY = 325;
        const radius = 220;
        
        mindmap.nodes.forEach((node, index) => {
            const angle = (index * 2 * Math.PI) / mindmap.nodes.length;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            const xPercent = (x / 800) * 100;
            const yPercent = (y / 650) * 100;

            html += `
                <div class="mindmap-node" style="top: ${yPercent}%; left: ${xPercent}%; background: ${node.color || 'var(--secondary)'}; transform: translate(-50%, -50%);" data-id="${node.id}>
                    ${node.label}
                </div>
            `;

            if (node.children && node.children.length > 0) {
                node.children.forEach((child, childIndex) => {
                    const childAngle = angle + ((childIndex - (node.children.length - 1) / 2) * 0.8);
                    const childRadius = radius + 140;
                    const childX = centerX + childRadius * Math.cos(childAngle);
                    const childY = centerY + childRadius * Math.sin(childAngle);
                    const childXPercent = (childX / 800) * 100;
                    const childYPercent = (childY / 650) * 100;

                    html += `
                        <div class="mindmap-node level-2" style="top: ${childYPercent}%; left: ${childXPercent}%; background: ${child.color || '#2dd4bf'}; transform: translate(-50%, -50%);" data-id="${child.id}>
                            ${child.label}
                        </div>
                    `;
                });
            }
        });
    }

    html += `
            </div>
        </div>
    </div>
`;

setTimeout(() => drawMindMapConnections(mindmap), 100);
return html;
}

// Draw Mind Map Connections
function drawMindMapConnections(mindmap) {
    const svg = document.querySelector('.mindmap-svg');
    if (!svg) return;

    const centerX = 400;
    const centerY = 325;
    const radius = 220;
    let connections = '';

    if (mindmap.nodes) {
        mindmap.nodes.forEach((node, index) => {
            const angle = (index * 2 * Math.PI) / mindmap.nodes.length;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);

            connections += `
                <line x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}" 
                      stroke="var(--primary)" stroke-width="3" opacity="0.7" 
                      stroke-dasharray="5,5">
                    <animate attributeName="stroke-dashoffset" 
                             values="0;-10" dur="1s" repeatCount="indefinite"/>
                </line>
            `;

            if (node.children) {
                node.children.forEach((child, childIndex) => {
                    const childAngle = angle + ((childIndex - (node.children.length - 1) / 2) * 0.8);
                    const childRadius = radius + 140;
                    const childX = centerX + childRadius * Math.cos(childAngle);
                    const childY = centerY + childRadius * Math.sin(childAngle);

                    connections += `
                        <line x1="${x}" y1="${y}" x2="${childX}" y2="${childY}" 
                              stroke="${node.color || 'var(--secondary)'}" stroke-width="2" opacity="0.6"/>
                    `;
                });
            }
        });
    }

    svg.innerHTML = connections;
}

// Create Learning Path HTML (Updated to match provided code)
function createLearningPathHTML(learningPath) {
    let html = `
        <div style="background: var(--glass); backdrop-filter: blur(12px); border-radius: 20px; padding: 2.5rem;">
            <h2 class="text-center" style="color: white; margin-bottom: 2rem;">
                <i class="fas fa-route" style="color: #facc15;"></i> Your Learning Path
            </h2>
            <div class="learning-path">
    `;

    learningPath.forEach((step, index) => {
        html += `
            <div class="learning-step animate-in" style="opacity: 0; transform: translateY(30px);">
                <div class="step-number">${step.step_number}</div>
                <h3 style="color: #333; margin-bottom: 0.5rem;">${step.title}</h3>
                <p style="color: #666; margin-bottom: 1rem;">${step.description}</p>
                <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                    <span style="background: #e0e7ff; color: #3730a3; padding: 0.25rem 0.75rem; border-radius: 15px; font-size: 0.8rem;">
                        <i class="fas fa-clock"></i> ${step.estimated_time}
                    </span>
                    ${step.prerequisites && step.prerequisites.length > 0 ? `
                        <span style="background: #fef3c7; color: #92400e; padding: 0.25rem 0.75rem; border-radius: 15px; font-size: 0.8rem;">
                            <i class="fas fa-exclamation-circle"></i> Prerequisites: ${step.prerequisites.join(', ')}
                        </span>
                    ` : ''}
                </div>
            </div>
        `;
    });

    html += `
            </div>
        </div>
    `;

    return html;
}

// Create Sticky Notes HTML (Updated to match provided code)
function createStickyNotesHTML(stickyNotes) {
    let html = `
        <div style="background: var(--glass); backdrop-filter: blur(12px); border-radius: 20px; padding: 2.5rem;">
            <h2 class="text-center" style="color: white; margin-bottom: 2rem;">
                <i class="fas fa-sticky-note" style="color: #fb7185;"></i> Smart Sticky Notes
            </h2>
            <div style="text-align: center; margin-bottom: 2rem;">
                <span style="background: #ff6b6b; color: white; padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem;">
                    🔴 Must Memorize
                </span>
                <span style="background: #ffd54f; color: #333; padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem;">
                    🟡 Good to Know
                </span>
                <span style="background: #66bb6a; color: white; padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem; font-size: 0.9rem;">
                    🟢 Bonus/Extra
                </span>
            </div>
            <div class="sticky-grid">
    `;

    stickyNotes.forEach((note, index) => {
        html += `
            <div class="sticky-note ${note.category} animate-in" style="opacity: 0; transform: translateY(30px); animation-delay: ${index * 0.1}s;" onclick="expandSticky(this)">
                <div style="font-weight: 600; margin-bottom: 0.5rem;">
                    Priority: ${note.priority}/10
                </div>
                <div>${note.content}</div>
                <div style="margin-top: 1rem; opacity: 0.8;">
                    ${note.tags ? note.tags.map(tag => `<span style="background: rgba(255,255,255,0.2); padding: 0.2rem 0.5rem; border-radius: 10px; font-size: 0.7rem; margin-right: 0.25rem;">#${tag}</span>`).join('') : ''}
                </div>
            </div>
        `;
    });

    html += `
            </div>
        </div>
    `;
    return html;
}

// Create Exam Questions HTML
function createExamQuestionsHTML(examQuestions) {
    let html = `
        <div style="background: var(--glass); backdrop-filter: blur(12px); border-radius: 20px; padding: 2.5rem;">
            <h2 class="text-center" style="color: white; margin-bottom: 2rem;">
                <i class="fas fa-trophy" style="color: #34d399;"></i> Exam Booster
            </h2>
            <div class="exam-questions">
    `;

    examQuestions.forEach((question, index) => {
        const probability = Math.round(question.probability_score * 100);
        html += `
            <div class="exam-question animate-in" style="opacity: 0; transform: translateY(20px);">
                <div class="question-type-badge ${question.type}">
                    ${question.type.replace('_', ' ').toUpperCase()}
                </div>
                <h3 style="color: #333; margin-bottom: 1rem; padding-right: 100px;">${question.question}</h3>
                <div class="probability-score">
                    <span style="font-weight: 600; color: #666;">Probability:</span>
                    <div class="probability-bar">
                        <div class="probability-fill" style="width: ${probability}%"></div>
                    </div>
                    <span style="font-weight: 600; color: ${probability > 70 ? '#ef4444' : probability > 50 ? '#f59e0b' : '#10b981'};">${probability}%</span>
                </div>
                <div style="margin-top: 1rem;">
                    ${question.keywords ? question.keywords.map(keyword => `<span style="background: #e0e7ff; color: #3730a3; padding: 0.25rem 0.5rem; border-radius: 10px; font-size: 0.8rem; margin-right: 0.5rem;">${keyword}</span>`).join('') : ''}
                </div>
            </div>
        `;
    });

    html += `</div></div>`;
    return html;
}

// Utility Functions
function flipCard(card) {
    card.classList.toggle('flipped');
}

function selectAnswer(button, selectedIndex, correctIndex, explanation, questionIndex) {
    const options = button.parentElement.querySelectorAll('.option-btn');
    const explanationDiv = document.getElementById(`explanation-${questionIndex}`);
    
    options.forEach((option, index) => {
        option.disabled = true;
        option.style.pointerEvents = 'none';
        if (index === correctIndex) {
            option.classList.add('correct');
        } else if (index === selectedIndex && index !== correctIndex) {
            option.classList.add('incorrect');
        }
    });
    
    setTimeout(() => {
        if (explanationDiv) {
            explanationDiv.style.display = 'block';
            explanationDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }, 600);
}

function shuffleFlashcards() {
    const container = document.querySelector('.flashcards-grid');
    if (!container) return;
    
    const cards = Array.from(container.children);
    
    for (let i = cards.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [cards[i], cards[j]] = [cards[j], cards[i]];
    }
    
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        container.appendChild(card);
    });
}

// YouTube Modal Functions - Fixed
function openYouTubeModal() {
    const modal = document.getElementById('youtubeModal');
    if (modal) {
        modal.classList.add('show');
        const urlInput = document.getElementById('modalYoutubeUrl');
        if (urlInput) urlInput.focus();
        document.body.classList.add('modal-open'); 
    }
}

function closeYouTubeModal() {
    const modal = document.getElementById('youtubeModal');
    if (modal) {
        modal.classList.remove('show');
        const urlInput = document.getElementById('modalYoutubeUrl');
        if (urlInput) urlInput.value = '';
        const videoPreview = document.getElementById('modalVideoPreview');
        if (videoPreview) videoPreview.style.display = 'none';
        document.body.classList.remove('modal-open');
    }
}

// Enhanced window click handler
window.onclick = function(event) {
    const modal = document.getElementById('youtubeModal');
    if (event.target === modal) {
        closeYouTubeModal();
    }
}

// Escape key to close modal
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modal = document.getElementById('youtubeModal');
        if (modal && modal.classList.contains('show')) {
            closeYouTubeModal();
        }
    }
});

// Enhanced preview function
async function previewVideo() {
    const urlInput = document.getElementById('modalYoutubeUrl');
    if (!urlInput) return;
    const url = urlInput.value.trim();
    
    const previewDiv = document.getElementById('modalVideoPreview');
    if (!previewDiv) return;

    if (!url) {
        previewDiv.style.display = 'none';
        return;
    }
    
    try {
        const videoId = extractVideoId(url);
        if (!videoId) {
            previewDiv.innerHTML = `
                <div style="text-align: center; padding: 1rem; color: #ef4444;">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Invalid YouTube URL.</p>
                </div>
            `;
            previewDiv.style.display = 'flex';
            return;
        }
        
        previewDiv.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <div class="loading" style="margin: 0 auto 1rem;"></div>
                <p style="color: var(--text-secondary);">Loading video information...</p>
            </div>
        `;
        previewDiv.style.display = 'flex';
        
        const response = await fetch(`/api/video-info/${videoId}`);
        if (!response.ok) throw new Error('Failed to fetch video info');
        
        const videoInfo = await response.json();
        
        previewDiv.innerHTML = `
            <img id="modalVideoThumbnail" class="video-thumbnail" alt="Video thumbnail">
            <div class="video-info">
                <h4 id="modalVideoTitle">Video Title</h4>
                <p id="modalVideoDetails">Duration • Channel</p>
            </div>
        `;
        
        const thumbnailEl = document.getElementById('modalVideoThumbnail');
        const titleEl = document.getElementById('modalVideoTitle');
        const detailsEl = document.getElementById('modalVideoDetails');

        if (thumbnailEl) thumbnailEl.src = videoInfo.thumbnail;
        if (titleEl) titleEl.textContent = videoInfo.title;
        if (detailsEl) detailsEl.textContent = `${videoInfo.duration} • ${videoInfo.channel}`;
        
        previewDiv.style.display = 'flex';
        
    } catch (error) {
        console.error('Error previewing video:', error);
        if (previewDiv) {
            previewDiv.innerHTML = `
                <div style="text-align: center; padding: 1rem; color: #ef4444;">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Unable to load video information. Please check the URL and try again.</p>
                </div>
            `;
            previewDiv.style.display = 'flex';
        }
    }
}

function extractVideoId(url) {
    const regex = /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

async function summarizeVideo() {
    const urlInput = document.getElementById('modalYoutubeUrl');
    if (!urlInput) return;
    const url = urlInput.value.trim();

    const btn = document.getElementById('modalSummarizeBtn');
    if (!btn) return;
    const originalText = btn.innerHTML;
    
    if (!url) {
        alert('Please enter a YouTube URL first');
        return;
    }
    
    btn.innerHTML = '<div class="loading"></div> Analyzing...';
    btn.disabled = true;
    
    try {
        const response = await fetch('/api/summarize-youtube', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Failed to summarize video. Unknown server error.' }));
            throw new Error(errorData.detail || 'Failed to summarize video');
        }
        
        const data = await response.json();
        closeYouTubeModal();
        displayVideoSummary(data);
        
    } catch (error) {
        console.error('Error summarizing video:', error);
        alert(`Error: ${error.message}`);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Ensure displayVideoSummary function exists and works as intended to show the summary
function displayVideoSummary(data) {
    const resultsSection = document.getElementById('results-section');
    if (!resultsSection) return;
    
    window.currentVideoSummary = data.summary;
    
    const html = `
        <div style="background: var(--glass); backdrop-filter: blur(12px); border-radius: 20px; padding: 2.5rem;">
            <h2 class="text-center" style="color: white; margin-bottom: 2rem;">
                <i class="fab fa-youtube" style="color: #ff0000;"></i> Video Summary
            </h2>
            <div class="video-summary-container animate-in" style="opacity: 0; transform: translateY(20px);">
                <div class="video-header">
                    <img src="${data.thumbnail}" alt="Video thumbnail" class="video-thumbnail-large" onerror="this.src='https://img.youtube.com/vi/${data.video_id}/maxresdefault.jpg'">
                    <div class="video-details">
                        <h3>${data.title.replace(/'/g, "\\'").replace(/"/g, '"')}</h3>
                        <div class="video-meta">
                            <span class="video-badge">${data.duration || 'Unknown Duration'}</span>
                            <span class="video-badge">${data.source === 'transcript' ? 'Transcript' : 'Audio Analysis'}</span>
                        </div>
                        <p style="color: #64748b; line-height: 1.6;">
                            AI-generated summary from ${data.source === 'transcript' ? 'official transcript' : 'audio transcription'}
                        </p>
                    </div>
                </div>
                <div class="summary-content">
                    <h4><i class="fas fa-file-alt"></i> Summary</h4>
                    <div style="line-height: 1.8; color: var(--dark);">
                        ${data.summary.replace(/\n/g, '<br><br>').replace(/'/g, "\\'").replace(/"/g, '"')}
                    </div>
                </div>
                <div style="margin-top: 3rem; background: rgba(91, 33, 182, 0.05); border-radius: 20px; padding: 2rem;">
                    <h4 class="text-center" style="color: var(--primary); margin-bottom: 2rem;">
                        <i class="fas fa-graduation-cap"></i> Generate Study Materials
                    </h4>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                        <button class="btn study-tool-btn" style="background: #f87171; color: white;" onclick="generateFromVideoSummary('flashcards')">
                            <i class="fas fa-brain"></i> Flashcards
                        </button>
                        <button class="btn study-tool-btn" style="background: #2dd4bf; color: white;" onclick="generateFromVideoSummary('mcqs')">
                            <i class="fas fa-question-circle"></i> Quiz
                        </button>
                        <button class="btn study-tool-btn" style="background: #facc15; color: #333;" onclick="generateFromVideoSummary('mindmap')">
                            <i class="fas fa-project-diagram"></i> Mind Map
                        </button>
                        <button class="btn study-tool-btn" style="background: #a78bfa; color: white;" onclick="generateFromVideoSummary('learning-path')">
                            <i class="fas fa-route"></i> Learning Path
                        </button>
                        <button class="btn study-tool-btn" style="background: #fb7185; color: white;" onclick="generateFromVideoSummary('sticky-notes')">
                            <i class="fas fa-sticky-note"></i> Sticky Notes
                        </button>
                        <button class="btn study-tool-btn" style="background: #34d399; color: white;" onclick="generateFromVideoSummary('exam-questions')">
                            <i class="fas fa-trophy"></i> Exam Booster
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    resultsSection.innerHTML = html;
    resultsSection.style.display = 'block';
    
    setTimeout(() => {
        const container = resultsSection.querySelector('.animate-in');
        if (container) {
            container.style.opacity = '1';
            container.style.transform = 'translateY(0)';
        }
    }, 100);
    
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

async function generateFromVideoSummary(type) {
    try {
        const summary = window.currentVideoSummary;
        if (!summary) {
            alert('No video summary available.');
            return;
        }
        
        showLoading(type);
        
        const buttons = document.querySelectorAll('.study-tool-btn');
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = '0.6';
        });
        
        await generateContentFromText(type, summary);
        
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
        });
        
    } catch (error) {
        console.error('Error generating from video summary:', error);
        alert('Error generating study materials.');
        hideLoading();
        
        const buttons = document.querySelectorAll('.study-tool-btn');
        buttons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = '1';
        });
    }
}

async function generateContentFromText(type, text) {
    try {
        const formData = new FormData();
        formData.append('text', text);

        const response = await fetch(`/api/generate-${type}`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayResults(type, data);

    } catch (error) {
        console.error('Error:', error);
        alert(`Error generating ${type}.`);
        hideLoading();
    }
}

function getDifficultyColor(difficulty) {
    return {
        easy: '#34d399',
        medium: '#f59e0b',
        hard: '#f87171'
    }[difficulty] || '#6b7280';
}

function expandSticky(sticky) {
    if (sticky.style.transform.includes('scale(1.2)')) {
        sticky.style.transform = sticky.style.transform.replace('scale(1.2)', '');
        sticky.style.zIndex = '1';
    } else {
        sticky.style.transform += ' scale(1.2)';
        sticky.style.zIndex = '20';
    }
}

// Combine feature row boxes into single rectangular containers
document.addEventListener('DOMContentLoaded', function() {
    const featureRows = document.querySelectorAll('.feature-row');
    
    featureRows.forEach(row => {
        // Get the existing children
        const children = Array.from(row.children);
        
        // Create a wrapper container
        const wrapper = document.createElement('div');
        wrapper.className = 'feature-row-content';
        
        // Move all children into the wrapper
        children.forEach(child => {
            wrapper.appendChild(child);
        });
        
        // Add the wrapper back to the row
        row.appendChild(wrapper);
    });
});

// Initialize particles and animations on page load
createParticles();

// Initialize staggered animations on load
document.addEventListener('DOMContentLoaded', () => {
    // Animate feature cards
    document.querySelectorAll('.feature-card').forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        setTimeout(() => {
            card.style.transition = 'all 0.8s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 1500 + (index * 200));
    });

    // Add scroll trigger animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements for scroll animations
    document.querySelectorAll('.feature-card, .upload-container').forEach(el => {
        observer.observe(el);
    });
});

// FAQ Functionality
function toggleFAQ(button) {
    const faqItem = button.closest('.faq-item');
    const faqAnswer = faqItem.querySelector('.faq-answer');
    const isActive = faqItem.classList.contains('active');
    
    // Close all other FAQ items
    document.querySelectorAll('.faq-item').forEach(item => {
        if (item !== faqItem) {
            item.classList.remove('active');
            item.querySelector('.faq-answer').classList.remove('active');
        }
    });
    
    // Toggle current FAQ item
    if (isActive) {
        faqItem.classList.remove('active');
        faqAnswer.classList.remove('active');
    } else {
        faqItem.classList.add('active');
        faqAnswer.classList.add('active');
    }
}

// FAQ scroll animation
document.addEventListener('DOMContentLoaded', function() {
    // Animate FAQ items on scroll
    const faqItems = document.querySelectorAll('.faq-item');
    
    const faqObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry, index) => {
            if (entry.isIntersecting) {
                setTimeout(() => {
                    entry.target.classList.add('animate-in');
                }, index * 100);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    faqItems.forEach(item => {
        faqObserver.observe(item);
    });
});

// Feedback Widget Functionality
let feedbackRating = 0;
let feedbackCategory = '';

// Initialize feedback widget
document.addEventListener('DOMContentLoaded', function() {
    initializeFeedbackWidget();
});

function initializeFeedbackWidget() {
    // Rating stars functionality
    const ratingStars = document.querySelectorAll('.rating-star');
    const ratingText = document.getElementById('ratingText');
    const ratingTexts = {
        1: 'Poor - Needs significant improvement',
        2: 'Fair - Could be better',
        3: 'Good - Satisfied with the experience',
        4: 'Very Good - Impressed with the quality',
        5: 'Excellent - Exceeded expectations!'
    };

    ratingStars.forEach(star => {
        star.addEventListener('click', function() {
            feedbackRating = parseInt(this.dataset.value);
            
            // Update star display
            ratingStars.forEach((s, index) => {
                if (index < feedbackRating) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });
            
            // Update rating text
            ratingText.textContent = ratingTexts[feedbackRating];
            ratingText.style.color = feedbackRating >= 4 ? '#10b981' : feedbackRating >= 3 ? '#fbbf24' : '#ef4444';
        });
        
        star.addEventListener('mouseenter', function() {
            const hoverRating = parseInt(this.dataset.value);
            ratingStars.forEach((s, index) => {
                if (index < hoverRating) {
                    s.style.color = '#fbbf24';
                } else {
                    s.style.color = '#64748b';
                }
            });
        });
    });

    // Reset stars on mouse leave
    document.querySelector('.rating-stars').addEventListener('mouseleave', function() {
        ratingStars.forEach((s, index) => {
            if (index < feedbackRating) {
                s.style.color = '#fbbf24';
            } else {
                s.style.color = '#64748b';
            }
        });
    });

    // Category selection
    const categoryOptions = document.querySelectorAll('.category-option');
    categoryOptions.forEach(option => {
        option.addEventListener('click', function() {
            // Remove previous selection
            categoryOptions.forEach(opt => opt.classList.remove('selected'));
            
            // Select current option
            this.classList.add('selected');
            feedbackCategory = this.dataset.category;
        });
    });

    // Form submission
    const feedbackForm = document.getElementById('feedbackForm');
    feedbackForm.addEventListener('submit', handleFeedbackSubmit);
}

function toggleFeedback() {
    const widget = document.getElementById('feedbackWidget');
    widget.classList.toggle('open');
}

function openFeedback() {
    const widget = document.getElementById('feedbackWidget');
    widget.classList.add('open');
}

function closeFeedback() {
    const widget = document.getElementById('feedbackWidget');
    widget.classList.remove('open');
    
    // Reset form after a delay
    setTimeout(resetFeedbackForm, 300);
}

function resetFeedbackForm() {
    const formContainer = document.querySelector('.feedback-form-container');
    const successContainer = document.getElementById('feedbackSuccess');
    
    formContainer.style.display = 'block';
    successContainer.classList.remove('show');
    
    // Reset form values
    feedbackRating = 0;
    feedbackCategory = '';
    
    // Reset stars
    document.querySelectorAll('.rating-star').forEach(star => {
        star.classList.remove('active');
        star.style.color = '#64748b';
    });
    
    // Reset rating text
    document.getElementById('ratingText').textContent = '';
    
    // Reset category selection
    document.querySelectorAll('.category-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Reset form fields
    document.getElementById('feedbackMessage').value = '';
    document.getElementById('feedbackEmail').value = '';
    
    // Reset submit button
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Feedback';
}

async function handleFeedbackSubmit(event) {
    event.preventDefault();
    
    const submitBtn = document.getElementById('submitBtn');
    const message = document.getElementById('feedbackMessage').value.trim();
    const email = document.getElementById('feedbackEmail').value.trim();
    
    // Validation
    if (!message) {
        alert('Please provide your feedback message');
        return;
    }
    
    if (feedbackRating === 0) {
        alert('Please rate your experience');
        return;
    }
    
    // Update submit button
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<div class="loading" style="width: 20px; height: 20px;"></div> Sending...';
    
    try {
        // Prepare feedback data
        const feedbackData = {
            rating: feedbackRating,
            category: feedbackCategory || 'general',
            message: message,
            email: email || 'anonymous',
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        // Send feedback (you can implement your own endpoint)
        const response = await fetch('/api/submit-feedback', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(feedbackData)
        });
        
        if (response.ok) {
            showFeedbackSuccess();
        } else {
            throw new Error('Failed to submit feedback');
        }
        
    } catch (error) {
        console.error('Error submitting feedback:', error);
        
        // For now, show success anyway (since backend might not be implemented)
        // In production, you'd want to handle this error properly
        showFeedbackSuccess();
        
        // Uncomment the line below if you want to show error instead
        // alert('Sorry, there was an error submitting your feedback. Please try again.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send Feedback';
    }
}

function showFeedbackSuccess() {
    const formContainer = document.querySelector('.feedback-form-container');
    const successContainer = document.getElementById('feedbackSuccess');
    
    formContainer.style.display = 'none';
    successContainer.classList.add('show');
    
    // Auto close after 3 seconds
    setTimeout(() => {
        closeFeedback();
    }, 3000);
}

// Simple Feedback Form Functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize simple feedback form
    initializeSimpleFeedback();
});

function initializeSimpleFeedback() {
    const form = document.getElementById('simpleFeedbackForm');
    if (form) {
        form.addEventListener('submit', handleSimpleFeedbackSubmit);
        
        // Initialize star rating for simple feedback
        initializeSimpleRating();
    }
}

function initializeSimpleRating() {
    const ratingStars = document.querySelectorAll('.simple-rating-star');
    const ratingText = document.getElementById('simpleRatingText');
    const ratingTexts = {
        1: '⭐ Poor - Needs significant improvement',
        2: '⭐⭐ Fair - Could be better', 
        3: '⭐⭐⭐ Good - Satisfied with the experience',
        4: '⭐⭐⭐⭐ Very Good - Impressed with the quality',
        5: '⭐⭐⭐⭐⭐ Excellent - Exceeded expectations!'
    };

    ratingStars.forEach(star => {
        star.addEventListener('click', function() {
            simpleRating = parseInt(this.dataset.value);
            
            // Update star display
            ratingStars.forEach((s, index) => {
                if (index < simpleRating) {
                    s.classList.add('active');
                } else {
                    s.classList.remove('active');
                }
            });
            
            // Update rating text
            if (ratingText) {
                ratingText.textContent = ratingTexts[simpleRating];
                ratingText.style.color = simpleRating >= 4 ? '#10b981' : simpleRating >= 3 ? '#fbbf24' : '#ef4444';
            }
        });
        
        star.addEventListener('mouseenter', function() {
            const hoverRating = parseInt(this.dataset.value);
            ratingStars.forEach((s, index) => {
                if (index < hoverRating) {
                    s.style.color = '#fbbf24';
                    s.style.transform = 'scale(1.2)';
                } else {
                    s.style.color = '#64748b';
                    s.style.transform = 'scale(1)';
                }
            });
        });
    });

    // Reset stars on mouse leave
    const starsContainer = document.querySelector('.simple-rating-stars');
    if (starsContainer) {
        starsContainer.addEventListener('mouseleave', function() {
            ratingStars.forEach((s, index) => {
                if (index < simpleRating) {
                    s.style.color = '#fbbf24';
                    s.style.transform = 'scale(1.3)';
                } else {
                    s.style.color = '#64748b';
                    s.style.transform = 'scale(1)';
                }
            });
        });
    }
}

function handleSimpleFeedbackSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('.simple-feedback-submit');
    const originalText = submitBtn.innerHTML;
    
    // Validation for rating
    if (simpleRating === 0) {
        alert('Please rate your experience before submitting feedback');
        return;
    }
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
    
    // Get form data
    const formData = {
        name: document.getElementById('simpleName').value,
        email: document.getElementById('simpleEmail').value,
        type: document.getElementById('simpleFeedbackType').value,
        message: document.getElementById('simpleMessage').value,
        rating: simpleRating,
        timestamp: new Date().toISOString()
    };
    
    // Simulate sending (since no backend)
    setTimeout(() => {
        console.log('Feedback submitted:', formData);
        
        // Store in localStorage for demo purposes
        const existingFeedback = JSON.parse(localStorage.getItem('studyai_feedback') || '[]');
        existingFeedback.push(formData);
        localStorage.setItem('studyai_feedback', JSON.stringify(existingFeedback));
        
        // Add to testimonials if it's positive feedback (4-5 stars)
        if (formData.rating >= 4 && (formData.type === 'praise' || formData.type === 'general')) {
            addNewTestimonial(formData);
        }
        
        // Show success message with star rating
        showSimpleFeedbackSuccess(simpleRating);
        
        // Reset button
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
        
    }, 1500); // Simulate network delay
}

function showSimpleFeedbackSuccess(rating) {
    const form = document.querySelector('.simple-feedback-form');
    const success = document.getElementById('simpleFeedbackSuccess');
    const successStars = document.getElementById('successStars');
    
    // Create star display for success message
    const starCount = rating;
    let starsHTML = '';
    for (let i = 0; i < starCount; i++) {
        starsHTML += '⭐';
    }
    
    if (successStars) {
        successStars.innerHTML = starsHTML;
    }
    
    form.style.display = 'none';
    success.style.display = 'block';
}

function showSimpleFeedbackForm() {
    const form = document.querySelector('.simple-feedback-form');
    const success = document.getElementById('simpleFeedbackSuccess');
    
    form.style.display = 'block';
    success.style.display = 'none';
    
    // Clear form
    resetSimpleFeedback();
}

function resetSimpleFeedback() {
    const form = document.getElementById('simpleFeedbackForm');
    if (form) {
        form.reset();
        
        // Reset rating
        simpleRating = 0;
        const ratingStars = document.querySelectorAll('.simple-rating-star');
        ratingStars.forEach(star => {
            star.classList.remove('active');
            star.style.color = '#64748b';
            star.style.transform = 'scale(1)';
        });
        
        // Clear rating text
        const ratingText = document.getElementById('simpleRatingText');
        if (ratingText) {
            ratingText.textContent = '';
        }
        
        // Remove any validation classes
        form.querySelectorAll('.simple-feedback-field input, .simple-feedback-field select, .simple-feedback-field textarea').forEach(field => {
            field.classList.remove('valid', 'invalid');
        });
    }
}

function addNewTestimonial(feedbackData) {
    // Create a new testimonial slide (this would normally be done server-side)
    const firstName = feedbackData.name.split(' ')[0];
    const lastInitial = feedbackData.name.split(' ')[1] ? feedbackData.name.split(' ')[1][0] + '.' : '';
    const displayName = `${firstName} ${lastInitial}`;
    
    // In a real app, you'd add this to your database and refresh the testimonials
    console.log(`New testimonial from ${displayName}: ${feedbackData.message} (${feedbackData.rating} stars)`);
    
    // For demo purposes, show a notification
    showTestimonialNotification(displayName, feedbackData.rating);
}

function showTestimonialNotification(name, rating) {
    // Create star display
    let stars = '';
    for (let i = 0; i < rating; i++) {
        stars += '⭐';
    }
    
    // Create a temporary notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(139, 92, 246, 0.4);
        z-index: 2000;
        font-weight: 600;
        animation: slideInRight 0.5s ease-out;
        max-width: 300px;
        text-align: center;
    `;
    notification.innerHTML = `
        <div style="margin-bottom: 0.5rem;">${stars}</div>
        <div>Thank you ${name}!</div>
        <div style="font-size: 0.9rem; opacity: 0.9; margin-top: 0.25rem;">Your feedback may appear in our testimonials.</div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 6 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.5s ease-in forwards';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }, 6000);
}

// Add CSS for notification animations
const notificationStyle = document.createElement('style');
notificationStyle.textContent = `
    @keyframes slideInRight {
        0% {
            transform: translateX(100%);
            opacity: 0;
        }
        100% {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        0% {
            transform: translateX(0);
            opacity: 1;
        }
        100% {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(notificationStyle);

// Testimonials Carousel Functionality
let currentTestimonial = 0;
const totalTestimonials = 5;
let testimonialInterval;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize testimonials carousel
    initializeTestimonials();
});

function initializeTestimonials() {
    const track = document.getElementById('testimonialsTrack');
    if (!track) return;
    
    // Start auto-play
    startTestimonialAutoPlay();
    
    // Pause on hover
    const carousel = document.getElementById('testimonialsCarousel');
    if (carousel) {
        carousel.addEventListener('mouseenter', stopTestimonialAutoPlay);
        carousel.addEventListener('mouseleave', startTestimonialAutoPlay);
    }
}

function changeTestimonial(direction) {
    currentTestimonial += direction;
    
    if (currentTestimonial >= totalTestimonials) {
        currentTestimonial = 0;
    } else if (currentTestimonial < 0) {
        currentTestimonial = totalTestimonials - 1;
    }
    
    updateTestimonialDisplay();
}

function goToTestimonial(index) {
    currentTestimonial = index;
    updateTestimonialDisplay();
}

function updateTestimonialDisplay() {
    const track = document.getElementById('testimonialsTrack');
    const pagination = document.getElementById('testimonialPagination');
    
    if (track) {
        const translateX = -currentTestimonial * 20; // 20% per slide
        track.style.transform = `translateX(${translateX}%)`;
    }
    
    // Update pagination dots
    if (pagination) {
        const dots = pagination.querySelectorAll('.pagination-dot');
        dots.forEach((dot, index) => {
            if (index === currentTestimonial) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });
    }
}

function startTestimonialAutoPlay() {
    stopTestimonialAutoPlay(); // Clear any existing interval
    testimonialInterval = setInterval(() => {
        changeTestimonial(1);
    }, 4000); // Change every 4 seconds
}

function stopTestimonialAutoPlay() {
    if (testimonialInterval) {
        clearInterval(testimonialInterval);
    }
}

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', function() {
    checkAuthStatus();
});

// Check if user is logged in
function checkAuthStatus() {
    // Get user data from API
    fetch('/api/user/profile')
        .then(response => response.json())
        .then(data => {
            if (data.user) {
                // User is logged in
                document.getElementById('loginBtn').style.display = 'none';
                document.getElementById('userProfile').style.display = 'flex';
                document.getElementById('userAvatar').src = data.user.picture;
                document.getElementById('userName').textContent = data.user.name.split(' ')[0];
                
                // Store user data in localStorage
                localStorage.setItem('userData', JSON.stringify(data.user));
            } else {
                // User is logged out
                document.getElementById('loginBtn').style.display = 'flex';
                document.getElementById('userProfile').style.display = 'none';
                localStorage.removeItem('userData');
            }
        })
        .catch(error => {
            console.error('Error checking auth status:', error);
            // If API fails, try to get data from localStorage
            const userData = JSON.parse(localStorage.getItem('userData'));
            if (userData) {
                document.getElementById('loginBtn').style.display = 'none';
                document.getElementById('userProfile').style.display = 'flex';
                document.getElementById('userAvatar').src = userData.picture;
                document.getElementById('userName').textContent = userData.name.split(' ')[0];
            } else {
                document.getElementById('loginBtn').style.display = 'flex';
                document.getElementById('userProfile').style.display = 'none';
            }
        });
}

// Login function
function login() {
    // Store current page URL in localStorage for redirect back after auth
    localStorage.setItem('redirectAfterLogin', window.location.href);
    
    // Redirect to auth endpoint
    window.location.href = '/auth/login';
}

// Logout function
function logout() {
    fetch('/auth/logout', { method: 'POST' })
        .then(() => {
            localStorage.removeItem('userData');
            window.location.href = '/';
        })
        .catch(error => {
            console.error('Error during logout:', error);
            localStorage.removeItem('userData');
            window.location.href = '/';
        });
}

// Toggle dropdown
function toggleDropdown(event) {
    event.stopPropagation(); // Prevent click from immediately closing the dropdown
    const dropdown = document.getElementById('dropdownMenu');
    dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
}

// Update DOM event listeners when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Add click events for both username and avatar
    const userName = document.getElementById('userName');
    const userAvatar = document.getElementById('userAvatar');
    const userProfile = document.getElementById('userProfile');
    
    if (userName) {
        userName.addEventListener('click', toggleDropdown);
    }
    
    if (userAvatar) {
        userAvatar.addEventListener('click', toggleDropdown);
    }
    
    // Close dropdown when clicking elsewhere
    document.addEventListener('click', function(event) {
        const dropdown = document.getElementById('dropdownMenu');
        
        if (userProfile && dropdown && !userProfile.contains(event.target) && 
            dropdown.style.display === 'block') {
            dropdown.style.display = 'none';
        }
    });
});

// Update viewAccount() function to show centered popup
function viewAccount() {
    // Close dropdown
    document.getElementById('dropdownMenu').style.display = 'none';
    // Show account popup
    showAccountPopup();
}

// Account popup function
function showAccountPopup() {
    // Check if popup already exists
    if (document.getElementById('accountPopup')) {
        document.getElementById('accountPopup').style.display = 'flex';
        return;
    }
    
    // Create popup
    const popup = document.createElement('div');
    popup.id = 'accountPopup';
    popup.className = 'account-popup';
    
    popup.innerHTML = `
        <div class="account-popup-content">
            <span class="close" onclick="closeAccountPopup()">&times;</span>
            <div class="popup-header">
                <h3>Account Management</h3>
                <p>Coming soon!</p>
            </div>
            <div class="popup-body">
                <p>Account management features will be available soon.</p>
                <div class="text-center">
                    <button class="btn btn-primary" onclick="closeAccountPopup()">OK</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(popup);
}

function closeAccountPopup() {
    const popup = document.getElementById('accountPopup');
    if (popup) {
        popup.style.display = 'none';
    }
}

// Fix for both hover and click functionality
document.addEventListener('DOMContentLoaded', function() {
    const userProfile = document.getElementById('userProfile');
    const dropdown = document.getElementById('dropdownMenu');
    
    if (userProfile && dropdown) {
        // Prevent mouseout from immediately closing the dropdown when moving from profile to dropdown
        userProfile.addEventListener('mouseleave', function(e) {
            // Check if hovering into dropdown
            const relatedTarget = e.relatedTarget;
            if (dropdown.contains(relatedTarget)) {
                // Keep dropdown open
                dropdown.style.display = 'block';
            }
        });
        
        // Keep dropdown open when hovering over it
        dropdown.addEventListener('mouseleave', function() {
            // Only close if not hovering back to profile
            setTimeout(() => {
                const hoveredElement = document.querySelector(':hover');
                if (!userProfile.contains(hoveredElement)) {
                    dropdown.style.display = 'none';
                }
            }, 100);
        });
    }
});

// Update the loadUserDocuments function

async function loadUserDocuments() {
    try {
        console.log('🔍 Loading user documents...');
        
        const response = await fetch('/api/user/documents', {
            method: 'GET',
            credentials: 'include', // This is crucial for cookies
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        console.log('📄 Documents data:', data);
        
        const container = document.getElementById('documentsContainer');
        
        if (data.error) {
            container.innerHTML = `
                <div class="text-center" style="padding: 2rem;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f87171; margin-bottom: 1rem;"></i>
                    <h3 style="color: #f87171; margin-bottom: 1rem;">Authentication Error</h3>
                    <p style="color: #999;">${data.error}</p>
                    <button class="btn btn-primary" onclick="login()" style="margin-top: 1rem;">
                        <i class="fab fa-google"></i> Please Login First
                    </button>
                </div>
            `;
            return;
        }
        
        if (!data.documents || data.documents.length === 0) {
            container.innerHTML = `
                <div class="text-center" style="padding: 2rem;">
                    <i class="fas fa-folder-open" style="font-size: 3rem; color: #ccc; margin-bottom: 1rem;"></i>
                    <h3 style="color: #666; margin-bottom: 1rem;">No documents uploaded yet</h3>
                    <p style="color: #999;">Upload a document to start generating study materials!</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="documents-grid">';
        
        for (const doc of data.documents) {
            html += `
                <div class="document-card">
                    <div class="doc-icon">
                        <i class="fas fa-file-${getFileIcon(doc.file_type)}"></i>
                    </div>
                    <h4 title="${doc.filename}">${doc.filename.length > 25 ? doc.filename.substring(0, 25) + '...' : doc.filename}</h4>
                    <p style="color: #666; font-size: 0.85rem;">Uploaded: ${new Date(doc.uploaded_at).toLocaleDateString()}</p>
                    <div class="feature-buttons">
            `;
            
            const features = [
                { key: 'flashcards', icon: 'brain', name: 'Flashcards' },
                { key: 'mcqs', icon: 'question-circle', name: 'Quiz' },
                { key: 'mindmap', icon: 'project-diagram', name: 'Mind Map' },
                { key: 'learning-path', icon: 'route', name: 'Learning Path' },
                { key: 'sticky-notes', icon: 'sticky-note', name: 'Sticky Notes' },
                { key: 'exam-questions', icon: 'trophy', name: 'Exam Questions' }
            ];
            
            for (const feature of features) {
                if (doc.features[feature.key]) {
                    html += `
                        <button class="feature-btn generated" onclick="viewFeature(${doc.features[feature.key].id}, '${feature.key}')">
                            <i class="fas fa-${feature.icon}"></i> View ${feature.name}
                        </button>
                    `;
                } else {
                    html += `
                        <button class="feature-btn" onclick="generateFeature(${doc.id}, '${feature.key}')">
                            <i class="fas fa-${feature.icon}"></i> Generate ${feature.name}
                        </button>
                    `;
                }
            }
            
            html += `
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading documents:', error);
        document.getElementById('documentsContainer').innerHTML = 
            `<div class="text-center" style="padding: 2rem;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f87171; margin-bottom: 1rem;"></i>
                <h3 style="color: #f87171;">Error Loading Documents</h3>
                <p style="color: #999;">Please try refreshing the page or contact support.</p>
                <p style="color: #999; font-size: 0.8rem;">Error: ${error.message}</p>
            </div>`;
    }
}

// Add this to your script.js file

async function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    
    console.log('📤 File selected:', file.name);
    
    // Check if user is authenticated
    const userData = JSON.parse(localStorage.getItem('userData'));
    if (!userData) {
        alert('Please login first to upload documents');
        login();
        return;
    }
    
    // Show upload progress
    showUploadProgress(file.name);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload-document', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Upload failed');
        }
        
        const result = await response.json();
        console.log('✅ Upload successful:', result);
        
        hideUploadProgress();
        showUploadSuccess(result);
        
        // Reset file input
        input.value = '';
        
    } catch (error) {
        console.error('❌ Upload error:', error);
        hideUploadProgress();
        showUploadError(error.message);
    }
}

function showUploadProgress(filename) {
    // Create or show upload progress indicator
    let progressDiv = document.getElementById('uploadProgress');
    if (!progressDiv) {
        progressDiv = document.createElement('div');
        progressDiv.id = 'uploadProgress';
        progressDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--glass);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            padding: 2rem;
            z-index: 1000;
            text-align: center;
            color: white;
            min-width: 300px;
        `;
        document.body.appendChild(progressDiv);
    }
    
    progressDiv.innerHTML = `
        <div class="loading" style="margin: 0 auto 1rem;"></div>
        <h3>Uploading Document</h3>
        <p style="color: rgba(255,255,255,0.8);">${filename}</p>
        <p style="font-size: 0.9rem; color: rgba(255,255,255,0.6);">Please wait...</p>
    `;
    progressDiv.style.display = 'block';
}

function hideUploadProgress() {
    const progressDiv = document.getElementById('uploadProgress');
    if (progressDiv) {
        progressDiv.style.display = 'none';
    }
}

function showUploadSuccess(result) {
    // Show success notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: linear-gradient(135deg, #10b981, #34d399);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.4);
        z-index: 2000;
        font-weight: 600;
        animation: slideInRight 0.5s ease-out;
        max-width: 350px;
    `;
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <i class="fas fa-check-circle" style="font-size: 1.2rem;"></i>
            <div>
                <div style="font-weight: 600;">Upload Successful!</div>
                <div style="font-size: 0.9rem; opacity: 0.9; margin-top: 0.25rem;">${result.filename}</div>
            </div>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.5s ease-in forwards';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }, 5000);
    
    // Show option to generate features
    setTimeout(() => {
        if (confirm('Document uploaded successfully! Would you like to view your documents and generate study materials?')) {
            viewMyDocuments();
        }
    }, 2000);
}

function showUploadError(errorMessage) {
    alert(`Upload failed: ${errorMessage}\n\nPlease try again or contact support if the problem persists.`);
}

// Replace the existing document-related functions with these:

async function viewMyDocuments() {
    // Close dropdown if open
    const dropdown = document.getElementById('dropdownMenu');
    if (dropdown) {
        dropdown.style.display = 'none';
    }
    
    // Load and show documents
    await loadUserDocuments();
    document.getElementById('documentsModal').style.display = 'block';
}

function closeDocumentsModal() {
    document.getElementById('documentsModal').style.display = 'none';
}

async function loadUserDocuments() {
    try {
        console.log('🔍 Loading user documents...');
        
        const response = await fetch('/api/user/documents', {
            method: 'GET',
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        console.log('📡 Response status:', response.status);
        
        const data = await response.json();
        console.log('📄 Documents data:', data);
        
        const container = document.getElementById('documentsContainer');
        
        if (data.error) {
            container.innerHTML = `
                <div class="text-center" style="padding: 2rem;">
                    <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f87171; margin-bottom: 1rem;"></i>
                    <h3 style="color: #f87171; margin-bottom: 1rem;">Authentication Error</h3>
                    <p style="color: #999;">${data.error}</p>
                    <button class="btn btn-primary" onclick="login()" style="margin-top: 1rem;">
                        <i class="fab fa-google"></i> Please Login First
                    </button>
                </div>
            `;
            return;
        }
        
        if (!data.documents || data.documents.length === 0) {
            container.innerHTML = `
                <div class="text-center" style="padding: 2rem;">
                    <i class="fas fa-folder-open" style="font-size: 3rem; color: #ccc; margin-bottom: 1rem;"></i>
                    <h3 style="color: #666; margin-bottom: 1rem;">No documents uploaded yet</h3>
                    <p style="color: #999;">Upload a document to start generating study materials!</p>
                </div>
            `;
            return;
        }
        
        let html = '<div class="documents-grid">';
        
        for (const doc of data.documents) {
            html += `
                <div class="document-card">
                    <div class="doc-icon">
                        <i class="fas fa-file-${getFileIcon(doc.file_type)}"></i>
                    </div>
                    <h4 title="${doc.filename}">${doc.filename.length > 25 ? doc.filename.substring(0, 25) + '...' : doc.filename}</h4>
                    <p style="color: #666; font-size: 0.85rem;">Uploaded: ${new Date(doc.uploaded_at).toLocaleDateString()}</p>
                    <div class="feature-buttons">
            `;
            
            const features = [
                { key: 'flashcards', icon: 'brain', name: 'Flashcards' },
                { key: 'mcqs', icon: 'question-circle', name: 'Quiz' },
                { key: 'mindmap', icon: 'project-diagram', name: 'Mind Map' },
                { key: 'learning-path', icon: 'route', name: 'Learning Path' },
                { key: 'sticky-notes', icon: 'sticky-note', name: 'Sticky Notes' },
                { key: 'exam-questions', icon: 'trophy', name: 'Exam Questions' }
            ];
            
            for (const feature of features) {
                if (doc.features[feature.key]) {
                    html += `
                        <button class="feature-btn generated" onclick="viewFeature(${doc.features[feature.key].id}, '${feature.key}')">
                            <i class="fas fa-${feature.icon}"></i> View ${feature.name}
                        </button>
                    `;
                } else {
                    html += `
                        <button class="feature-btn" onclick="generateFeature(${doc.id}, '${feature.key}')">
                            <i class="fas fa-${feature.icon}"></i> Generate ${feature.name}
                        </button>
                    `;
                }
            }
            
            html += `
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading documents:', error);
        document.getElementById('documentsContainer').innerHTML = 
            `<div class="text-center" style="padding: 2rem;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; color: #f87171; margin-bottom: 1rem;"></i>
                <h3 style="color: #f87171;">Error Loading Documents</h3>
                <p style="color: #999;">Please try refreshing the page or contact support.</p>
                <p style="color: #999; font-size: 0.8rem;">Error: ${error.message}</p>
            </div>`;
    }
}

async function viewFeature(featureId, featureType) {
    try {
        const response = await fetch(`/api/user/features/${featureId}`);
        const data = await response.json();
        
        // Close documents modal
        closeDocumentsModal();
        
        // Display the feature content
        displayResults(featureType, data.content);
        
    } catch (error) {
        console.error(`Error loading ${featureType}:`, error);
        alert(`Failed to load ${featureType}. Please try again.`);
    }
}

async function generateFeature(documentId, featureType) {
    try {
        // Show loading indicator
        const btn = event.currentTarget;
        const originalText = btn.innerHTML;
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Generating...`;
        btn.disabled = true;
        
        // Make API request to generate the feature using the auth endpoints
        const response = await fetch(`/api/generate-${featureType}-auth`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            credentials: 'include',
            body: `document_id=${documentId}`,
        });
        
        const data = await response.json();
        
        if (response.ok && data) {
            // Update button to show "View" instead of "Generate"
            btn.innerHTML = `<i class="fas fa-${getFeatureIcon(featureType)}"></i> View ${getFeatureName(featureType)}`;
            btn.classList.add('generated');
            btn.disabled = false;
            
            // Close documents modal and show the generated feature
            closeDocumentsModal();
            displayResults(featureType, data);
        } else {
            throw new Error(data.detail || 'Generation failed');
        }
        
    } catch (error) {
        console.error(`Error generating ${featureType}:`, error);
        alert(`Failed to generate ${featureType}. Please try again.`);
        
        // Reset button
        const btn = event.currentTarget;
        btn.innerHTML = `<i class="fas fa-${getFeatureIcon(featureType)}"></i> Generate ${getFeatureName(featureType)}`;
        btn.disabled = false;
    }
}