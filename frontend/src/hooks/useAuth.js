import { useState, useCallback } from 'react';

export function useAuth() {
    const [authenticated, setAuthenticated] = useState(!!localStorage.getItem('authToken'));
    const [userId, setUserId] = useState(localStorage.getItem('userId'));
    const [username, setUsername] = useState(localStorage.getItem('username'));

    const handleLogin = useCallback((userData) => {
        // Store auth data first
        localStorage.setItem('authToken', userData.token);
        localStorage.setItem('userId', userData.user_id.toString());
        localStorage.setItem('username', userData.username);

        // Update state
        setUserId(userData.user_id.toString());
        setUsername(userData.username);

        // Set authenticated last to ensure everything is ready
        setTimeout(() => {
            setAuthenticated(true);
        }, 100);
    }, []);

    const handleLogout = useCallback(() => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('userId');
        localStorage.removeItem('username');
        setUserId(null);
        setUsername(null);
        setAuthenticated(false);
    }, []);

    return {
        authenticated,
        userId,
        username,
        handleLogin,
        handleLogout
    };
}
