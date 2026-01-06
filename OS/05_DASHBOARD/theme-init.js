// ANTI-FLASHBANG: Must run before CSS to prevent white flash
// This file is loaded synchronously in <head> before style.css
(function () {
    var saved = localStorage.getItem('resilience_theme');
    // Default is dark (crisis mode), light only if explicitly chosen
    if (saved !== 'light') {
        document.documentElement.classList.add('night-mode');
    }
})();
