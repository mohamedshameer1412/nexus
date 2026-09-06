// This script runs BEFORE React hydration to prevent flash
(function () {
    try {
        // Check localStorage for user preferences
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const darkMode = user.preference_dark_mode;

        // Apply dark mode class immediately
        if (darkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    } catch (e) {
        // Fail silently - default to light mode
        console.error('Dark mode init error:', e);
    }
})();
