const getApiUrl = () => {
    // If explicitly set via environment variable, use that
    if (process.env.REACT_APP_API_URL) {
        return process.env.REACT_APP_API_URL;
    }

    // Get current hostname, protocol and port
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    const port = window.location.port;

    // Debug information
    console.log('API URL Configuration:', {
        hostname,
        protocol,
        port,
        environment: process.env.NODE_ENV,
        userAgent: navigator.userAgent
    });

    // For development
    if (process.env.NODE_ENV === 'development') {
        // Use development proxy when serving from React dev server
        if (port === '3000') {
            // Using relative URL to avoid CORS issues with HTTP/HTTPS mismatch
            console.log('Using development proxy for API calls');
            return '/api';
        }

        // For localhost/127.0.0.1, use HTTP for backend
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            const apiUrl = `http://${hostname}:8000`;
            console.log('Localhost API URL:', apiUrl);
            return apiUrl;
        }

        // For network IPs (like 192.168.x.x), force HTTP to avoid certificate issues
        const isNetworkIP = /^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)/.test(hostname);
        if (isNetworkIP) {
            const apiUrl = `http://${hostname}:8000`;
            console.log('Network IP API URL (using HTTP):', apiUrl);
            return apiUrl;
        }

        // Default development fallback
        const apiUrl = `${protocol}//${hostname}:8000`;
        console.log('Default development API URL:', apiUrl);
        return apiUrl;
    }

    // For production, we need HTTPS for voice features (getUserMedia requirement)
    // Always use HTTPS in production for microphone access
    const apiUrl = `https://${hostname}/api`;
    console.log('Production API URL (HTTPS required for voice):', apiUrl);
    return apiUrl;
};

const config = {
    API_URL: getApiUrl(),
    DEBUG: process.env.NODE_ENV === 'development'
};

export default config;
