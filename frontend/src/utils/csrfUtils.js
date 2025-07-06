export function getCsrfToken() {
    // First try to get from cookie
    let csrfToken = null;

    // Parse cookies properly
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            csrfToken = value;
            break;
        }
    }

    // If no token in cookie, try to get from DOM meta tag
    if (!csrfToken) {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            csrfToken = metaTag.getAttribute('content');
        }
    }

    // If still no token, try to get from Django's template variable
    if (!csrfToken && window.csrftoken) {
        csrfToken = window.csrftoken;
    }

    // If token exists but is malformed, return null to skip CSRF header
    if (csrfToken && (csrfToken.length < 32 || csrfToken.length > 64)) {
        console.warn('CSRF token has incorrect length:', csrfToken.length);
        return null;
    }

    return csrfToken;
}
