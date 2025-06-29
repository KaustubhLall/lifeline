import React, { useState } from 'react';
import config from '../config';
import '../styles/components/Auth.css';

function Login({ onLogin, onSwitchToSignup }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const loginUrl = `${config.API_URL}/api/login/`;

      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: `Login failed: ${response.status} ${response.statusText}`
        }));
        setError(errorData.detail || 'Login failed. Please check your credentials.');
        return;
      }

      const data = await response.json();
      console.log('Login successful:', { username: data.username, userId: data.user_id });

      onLogin({
        token: data.token,
        user_id: data.user_id,
        username: data.username
      });

    } catch (error) {
      console.error('Login error:', error);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2 className="auth-title">🔐 Welcome Back</h2>
          <p className="auth-subtitle">Sign in to continue your conversations</p>
        </div>

        {error && (
          <div className="auth-error">
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label htmlFor="username" className="auth-label">Username</label>
            <input
              type="text"
              className="auth-input"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={isLoading}
              placeholder="Enter your username"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password" className="auth-label">Password</label>
            <input
              type="password"
              className="auth-input"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
              placeholder="Enter your password"
            />
          </div>

          <button
            type="submit"
            className="auth-button primary"
            disabled={isLoading || !username.trim() || !password.trim()}
          >
            {isLoading ? (
              <>
                <span className="auth-spinner"></span>
                Signing in...
              </>
            ) : (
              '🚀 Sign In'
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p className="auth-switch-text">
            Don't have an account?{' '}
            <button
              type="button"
              className="auth-link"
              onClick={onSwitchToSignup}
              disabled={isLoading}
            >
              Sign up here ✨
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
