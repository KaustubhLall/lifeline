const getApiUrl = () => {
    // If explicitly set via environment variable, use that
    if (process.env.REACT_APP_API_URL) {
        return process.env.REACT_APP_API_URL;
    }

    // Get current hostname and protocol
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;

    // Log for debugging
    console.log('Detected hostname:', hostname);
    console.log('Current protocol:', protocol);
    console.log('Window location:', window.location.href);

    // For development
    if (process.env.NODE_ENV === 'development') {
        // For localhost/127.0.0.1, use HTTP for backend even if frontend is HTTPS
        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            const apiUrl = `http://${hostname}:8000`;
            console.log('Localhost API URL (forcing HTTP for backend):', apiUrl);
            return apiUrl;
        }

        // For network IPs (like 10.5.0.2, 192.168.x.x), always use HTTP for backend in development
        // This handles the case where frontend is HTTPS but backend is HTTP
        const isNetworkIP = /^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)/.test(hostname);
        if (isNetworkIP) {
            const apiUrl = `http://${hostname}:8000`;
            console.log('Network IP API URL (forcing HTTP for backend):', apiUrl);
            return apiUrl;
        }

        // For other development scenarios, match the frontend protocol
        if (protocol === 'https:') {
            const apiUrl = `https://${hostname}:8000`;
            console.log('Development HTTPS API URL:', apiUrl);
            return apiUrl;
        } else {
            // Otherwise use HTTP
            const apiUrl = `http://${hostname}:8000`;
            console.log('Development HTTP API URL:', apiUrl);
            return apiUrl;
        }
    }

    // For production, always use HTTPS
    return `https://${hostname}:8000`;
};

const config = {
    API_URL: getApiUrl()
};

export default config;
