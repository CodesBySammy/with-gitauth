document.addEventListener('DOMContentLoaded', () => {
    
    // --- 3D Tilt Effect ---
    const card = document.getElementById('mainCard');
    const container = document.querySelector('.container');

    // Only apply tilt on desktop devices (non-touch)
    if (window.matchMedia("(pointer: fine)").matches) {
        container.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            // Calculate mouse position relative to card center (-1 to 1)
            const x = (e.clientX - rect.left - rect.width / 2) / (rect.width / 2);
            const y = (e.clientY - rect.top - rect.height / 2) / (rect.height / 2);
            
            // Adjust sensitivity here (max rotation in degrees)
            const maxTilt = 8;
            
            // Apply transform
            card.style.transform = `rotateY(${x * maxTilt}deg) rotateX(${-y * maxTilt}deg)`;
        });

        container.addEventListener('mouseleave', () => {
            // Reset position softly
            card.style.transition = 'transform 0.5s cubic-bezier(0.23, 1, 0.32, 1)';
            card.style.transform = 'rotateY(0deg) rotateX(0deg)';
            
            // Remove transition so it tracks mouse instantly again
            setTimeout(() => {
                card.style.transition = 'transform 0.1s ease';
            }, 500);
        });
    }

    // --- Auth State Management ---
    const urlParams = new URLSearchParams(window.location.search);
    
    // If returning from successful OAuth callback
    if (urlParams.get('logged_in') === '1') {
        localStorage.setItem('xai_logged_in', 'true');
        window.location.href = '/dashboard.html';
        return;
    }

    // If already logged in
    if (localStorage.getItem('xai_logged_in') === 'true') {
        window.location.href = '/dashboard.html';
        return;
    }

    // If OAuth failed
    if (urlParams.get('error')) {
        alert('Authentication failed. Please check your GitHub config.');
        window.history.replaceState({}, document.title, window.location.pathname);
        localStorage.removeItem('xai_logged_in');
    }
});
