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

    console.log('=== LOGIN DEBUG START ===');
    console.log('Config API URL:', config.API_URL);
    console.log('Window location:', window.location.href);
    console.log('Attempting login...');

    try {
      const loginUrl = `${config.API_URL}/api/login/`;
      console.log('Login URL:', loginUrl);
      console.log('Request payload:', { username, password: '***' });

      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);
      console.log('Response headers:', [...response.headers.entries()]);

      if (!response.ok) {
        let errorData;
        try {
          const responseText = await response.text();
          console.log('Error response text:', responseText);
          errorData = responseText ? JSON.parse(responseText) : { detail: `HTTP ${response.status}` };
        } catch (parseError) {
          console.log('Failed to parse error response:', parseError);
          errorData = { detail: `HTTP ${response.status}: ${response.statusText}` };
        }
        console.error('Login failed. Server response:', errorData);
        throw new Error(errorData.detail || `Login failed: ${response.status}`);
      }

      const data = await response.json();
      console.log('Login successful, received data:', data);

      // Validate response data
      if (!data.token || !data.user_id || !data.username) {
        console.error('Invalid login response data:', data);
        throw new Error('Invalid response from server');
      }

      console.log('=== LOGIN SUCCESS ===');
      onLogin(data);
    } catch (err) {
      console.error('=== LOGIN ERROR ===');
      console.error('Error details:', err);
      console.error('Error message:', err.message);
      console.error('Error stack:', err.stack);

      let errorMessage = 'Login failed. Please try again.';

      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError') || err.name === 'TypeError') {
        errorMessage = `Network error: Cannot connect to server at ${config.API_URL}. Please check if the backend server is running.`;
      } else if (err.message.includes('401')) {
        errorMessage = 'Invalid username or password.';
      } else if (err.message.includes('500')) {
        errorMessage = 'Server error. Please try again later.';
      } else {
        errorMessage = err.message || 'Login failed. Please try again.';
      }

      setError(errorMessage);
    } finally {
      setIsLoading(false);
      console.log('=== LOGIN DEBUG END ===');
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
