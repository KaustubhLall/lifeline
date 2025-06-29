import React, { useState } from 'react';
import config from './config';

function Login({ onLogin, onSwitchToSignup }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    console.log('Attempting login...');

    try {
      const loginUrl = `${config.API_URL}/api/login/`;
      console.log('Making login request to:', loginUrl);

      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      console.log('Login response status:', response.status);
      const contentType = response.headers.get("content-type");
      console.log('Response content type:', contentType);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Login failed. Server response:', errorText);
        throw new Error(`Login failed: ${response.status}`);
      }

      const data = await response.json();
      console.log('Login successful, received data:', data);
      onLogin(data);
    } catch (err) {
      console.error('Login error:', err);
      setError('Login failed. Please check your credentials and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container-fluid vh-100 d-flex align-items-center justify-content-center" style={{background: 'var(--primary-bg)'}}>
      <div className="row w-100 justify-content-center">
        <div className="col-12 col-sm-8 col-md-6 col-lg-4 col-xl-3">
          <div className="card" style={{background: 'var(--secondary-bg)', border: '2px solid var(--border-color)'}}>
            <div className="card-body p-4">
              <h2 className="card-title text-center mb-4" style={{color: 'var(--text-primary)'}}>Login</h2>
              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                </div>
              )}
              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label htmlFor="username" className="form-label" style={{color: 'var(--text-primary)'}}>Username</label>
                  <input
                    type="text"
                    className="form-control"
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={isLoading}
                    required
                    style={{
                      background: 'var(--primary-bg)',
                      border: '2px solid var(--border-color)',
                      color: 'var(--text-primary)'
                    }}
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="password" className="form-label" style={{color: 'var(--text-primary)'}}>Password</label>
                  <input
                    type="password"
                    className="form-control"
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                    required
                    style={{
                      background: 'var(--primary-bg)',
                      border: '2px solid var(--border-color)',
                      color: 'var(--text-primary)'
                    }}
                  />
                </div>
                <button
                  type="submit"
                  className="btn w-100 mb-3"
                  disabled={isLoading}
                  style={{
                    background: 'var(--message-user)',
                    border: 'none',
                    color: 'white',
                    padding: '12px',
                    borderRadius: '8px',
                    fontSize: '1rem',
                    fontWeight: '600'
                  }}
                >
                  {isLoading ? 'Logging in...' : 'Login'}
                </button>
                <div className="text-center">
                  <button
                    className="btn btn-link"
                    onClick={onSwitchToSignup}
                    type="button"
                    disabled={isLoading}
                    style={{color: 'var(--text-secondary)', textDecoration: 'none'}}
                  >
                    Don't have an account? Sign up
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
