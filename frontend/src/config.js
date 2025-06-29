const getApiUrl = () => {
    // If explicitly set via environment variable, use that
    if (process.env.REACT_APP_API_URL) {
        return process.env.REACT_APP_API_URL;
    }

    // Get current hostname and protocol
    const hostname = window.location.hostname.split(':')[0]; // strip port if present
    const protocol = window.location.protocol;

    // For development, use the current hostname (works for both localhost and network access)
    if (process.env.NODE_ENV === 'development') {
        return `${protocol}//${hostname}:8000`;
    }

    // For production, use current hostname
    return `${protocol}//${hostname}:8000`;
};

const config = {
    API_URL: getApiUrl()
};

console.log('API URL configured as:', config.API_URL);

export default config;
