import React, { useState } from 'react';

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
      console.log('Making login request to:', '/api/login/');
      const response = await fetch('/api/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
        credentials: 'include'
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
      console.log('Login successful, received token');
      localStorage.setItem('authToken', data.token);
      onLogin(data.token);
    } catch (err) {
      console.error('Login error:', err);
      setError('Login failed. Please check your credentials and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="row justify-content-center align-items-center min-vh-100">
        <div className="col-12 col-sm-8 col-md-6 col-lg-4">
          <div className="card">
            <div className="card-body">
              <h2 className="card-title text-center mb-4">Login</h2>
              {error && (
                <div className="alert alert-danger" role="alert">
                  {error}
                </div>
              )}
              <form onSubmit={handleSubmit}>
                <div className="mb-3">
                  <label htmlFor="username" className="form-label">Username</label>
                  <input
                    type="text"
                    className="form-control"
                    id="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="password" className="form-label">Password</label>
                  <input
                    type="password"
                    className="form-control"
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-primary w-100 mb-3"
                  disabled={isLoading}
                >
                  {isLoading ? 'Logging in...' : 'Login'}
                </button>
                <div className="text-center">
                  <button
                    className="btn btn-link"
                    onClick={onSwitchToSignup}
                    type="button"
                    disabled={isLoading}
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
