import config from '../config';

// API endpoints
export const API_BASE = `${config.API_URL}/api`;

// Helper function to add auth headers
export const fetchWithAuth = async (url, options = {}) => {
    const token = localStorage.getItem('authToken');
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Token ${token}`,
                'Content-Type': 'application/json',
            },
        });

        console.log(`API ${options.method || 'GET'} ${url}:`, {
            status: response.status,
            statusText: response.statusText
        });

        if (!response.ok) {
            const errorData = await response.text();
            console.error('Response error:', errorData);
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
};
