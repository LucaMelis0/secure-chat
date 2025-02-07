// Check if the user is refreshing the page
if (performance.navigation.type === 1) {
    sessionStorage.removeItem('chatSession');
}

// Redirects to authentication page
function goToAuth() {
    window.location.href = '/auth';
}

// Redirects unauthorized users trying to access chat
if (window.location.pathname === '/chat' && !sessionStorage.getItem('authenticated')) {
    window.location.href = '/auth';
}
