import React, { useState } from 'react';
import config from '../config';
import '../styles/components/Auth.css';

function SignUp({ onLogin }) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords don't match");
      setIsLoading(false);
      return;
    }

    try {
      const registerUrl = `${config.API_URL}/api/register/`;

      const response = await fetch(registerUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: `Registration failed: ${response.status} ${response.statusText}`
        }));
        setError(errorData.detail || 'Registration failed. Please try again.');
        return;
      }

      const data = await response.json();
      console.log('Registration successful:', { username: data.username, userId: data.user_id });

      onLogin({
        token: data.token,
        user_id: data.user_id,
        username: data.username
      });

    } catch (error) {
      console.error('Registration error:', error);
      setError('Network error. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2 className="auth-title">✨ Create Account</h2>
          <p className="auth-subtitle">Join us to start your AI conversations</p>
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
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              disabled={isLoading}
              placeholder="Choose a username"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="email" className="auth-label">Email</label>
            <input
              type="email"
              className="auth-input"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              disabled={isLoading}
              placeholder="Enter your email"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password" className="auth-label">Password</label>
            <input
              type="password"
              className="auth-input"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              disabled={isLoading}
              placeholder="Create a password"
            />
          </div>

          <div className="auth-field">
            <label htmlFor="confirmPassword" className="auth-label">Confirm Password</label>
            <input
              type="password"
              className="auth-input"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              disabled={isLoading}
              placeholder="Confirm your password"
            />
          </div>

          <button
            type="submit"
            className="auth-button primary"
            disabled={isLoading || !formData.username.trim() || !formData.email.trim() || !formData.password.trim()}
          >
            {isLoading ? (
              <>
                <span className="auth-spinner"></span>
                Creating account...
              </>
            ) : (
              '🎉 Create Account'
            )}
          </button>
        </form>
      </div>
    </div>
  );
}

export default SignUp;
