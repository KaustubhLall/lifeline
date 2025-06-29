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
    console.log('Window location:', window.location.href);

    // For development, use the current hostname (works for both localhost and network access)
    if (process.env.NODE_ENV === 'development') {
        const apiUrl = `${protocol}//${hostname}:8000`;
        console.log('Development API URL:', apiUrl);
        return apiUrl;
    }

    // For production, use current hostname
    const apiUrl = `${protocol}//${hostname}:8000`;
    console.log('Production API URL:', apiUrl);
    return apiUrl;
};

const config = {
    API_URL: getApiUrl()
};

console.log('=== CONFIG DEBUG ===');
console.log('Window location:', window.location);
console.log('API URL configured as:', config.API_URL);
console.log('===================');

export default config;
