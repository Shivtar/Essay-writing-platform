document.addEventListener('DOMContentLoaded', function() {
    // --- Element Selection ---
    const form = document.getElementById('correction-form');
    const submitBtn = document.getElementById('submit-btn');
    const saveBtn = document.getElementById('save-btn');
    const errorMessageDiv = document.getElementById('error-message');
    const essayTextarea = document.getElementById('essay');
    const darkModeToggle = document.getElementById('darkModeToggle');
    const clockDiv = document.getElementById('clock');
    
    // Stopwatch elements
    const stopwatchDisplay = document.getElementById('stopwatch-display');
    const startStopwatchBtn = document.getElementById('start-stopwatch-btn');
    const stopStopwatchBtn = document.getElementById('stop-stopwatch-btn');
    const resetStopwatchBtn = document.getElementById('reset-stopwatch-btn');

    // --- Event Listeners ---

    // Handles the "Check & Correct" button (standard form submission)
    if (form) {
        form.addEventListener('submit', function(event) {
            // This function lets the form submit normally to the '/' route
            // which reloads the page with the corrected text.
            submitBtn.textContent = 'Analyzing...';
            submitBtn.disabled = true;
            saveBtn.disabled = true;
        });
    }

    // Handles the "Save Manually" button (asynchronous fetch call)
    if (saveBtn) {
        saveBtn.addEventListener('click', function() {
            handleManualSave();
        });
    }

    // --- Core Functions ---

    function handleManualSave() {
        const formData = new FormData(form);
        const originalText = formData.get('text').trim();

        if (!originalText) {
            errorMessageDiv.textContent = 'Cannot save an empty essay.';
            return;
        }

        // Add the stats to the form data to be sent to the server
        formData.append('wordCount', document.getElementById('wordCount').textContent);
        formData.append('paragraphCount', document.getElementById('paragraphCount').textContent);
        formData.append('backspaceCount', document.getElementById('backspaceCount').textContent);

        // Update UI to show loading state
        saveBtn.textContent = 'Saving...';
        submitBtn.disabled = true;
        saveBtn.disabled = true;
        errorMessageDiv.textContent = '';

        // Send data to the '/save' route in your app.py
        fetch('/save', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Server responded with an error.');
        })
        .then(data => {
            // Show a success message from the server
            alert(data.message); 
        })
        .catch(error => {
            console.error('Save Error:', error);
            errorMessageDiv.textContent = 'An error occurred while saving. Please try again.';
        })
        .finally(() => {
            // Restore buttons to their original state
            saveBtn.textContent = 'Save Manually';
            submitBtn.disabled = false;
            saveBtn.disabled = false;
        });
    }

    // --- UI & Stats Logic ---

    // Word/Paragraph/Backspace Counter Logic
    if (essayTextarea) {
        essayTextarea.addEventListener('input', updateCounts);
        essayTextarea.addEventListener('keydown', function(event) {
            if (event.key === 'Backspace') {
                const backspaceCountSpan = document.getElementById('backspaceCount');
                let currentCount = parseInt(backspaceCountSpan.textContent, 10);
                backspaceCountSpan.textContent = currentCount + 1;
            }
        });
        updateCounts(); // Initial count on page load
    }

    function updateCounts() {
        const text = essayTextarea.value;
        const words = text.trim().split(/\s+/).filter(word => word.length > 0);
        document.getElementById('wordCount').textContent = words.length;
        const paragraphs = text.split('\n').filter(p => p.trim().length > 0);
        document.getElementById('paragraphCount').textContent = paragraphs.length;
    }

    // Dark Mode Toggle Logic
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleMode);
    }
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.body.classList.add('dark-mode');
    }

    function toggleMode() {
        document.body.classList.toggle('dark-mode');
        if (document.body.classList.contains('dark-mode')) {
            localStorage.setItem('darkMode', 'enabled');
        } else {
            localStorage.setItem('darkMode', 'disabled');
        }
    }

    // Clock Logic
    function updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        if (clockDiv) {
            clockDiv.textContent = timeString;
        }
    }
    setInterval(updateClock, 1000);
    updateClock(); // Initial call

    // Stopwatch Logic
    let stopwatchInterval;
    let stopwatchTime = 0;

    function formatTime(seconds) {
        const h = Math.floor(seconds / 3600).toString().padStart(2, '0');
        const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
        const s = (seconds % 60).toString().padStart(2, '0');
        return `${h}:${m}:${s}`;
    }

    if (startStopwatchBtn) {
        startStopwatchBtn.addEventListener('click', () => {
            startStopwatchBtn.style.display = 'none';
            stopStopwatchBtn.style.display = 'inline-block';
            stopwatchInterval = setInterval(() => {
                stopwatchTime++;
                stopwatchDisplay.textContent = formatTime(stopwatchTime);
            }, 1000);
        });
    }
    if (stopStopwatchBtn) {
        stopStopwatchBtn.addEventListener('click', () => {
            stopStopwatchBtn.style.display = 'none';
            startStopwatchBtn.style.display = 'inline-block';
            clearInterval(stopwatchInterval);
        });
    }
    if (resetStopwatchBtn) {
        resetStopwatchBtn.addEventListener('click', () => {
            clearInterval(stopwatchInterval);
            stopwatchTime = 0;
            stopwatchDisplay.textContent = '00:00:00';
            stopStopwatchBtn.style.display = 'none';
            startStopwatchBtn.style.display = 'inline-block';
        });
    }
});
