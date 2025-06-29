const getApiUrl = () => {
    // If explicitly set via environment variable, use that
    if (process.env.REACT_APP_API_URL) {
        return process.env.REACT_APP_API_URL;
    }

    // Get current hostname
    const hostname = window.location.hostname;

    // Log for debugging
    console.log('Detected hostname:', hostname);
    console.log('Window location:', window.location.href);

    // For development, always use HTTP for backend API calls
    // This allows HTTPS frontend to communicate with HTTP backend
    if (process.env.NODE_ENV === 'development') {
        const apiUrl = `http://${hostname}:8000`;
        console.log('Development API URL:', apiUrl);
        return apiUrl;
    }

    // For production, you would use HTTPS
    return `https://${hostname}:8000`;
};

const config = {
    API_URL: getApiUrl()
};

export default config;
