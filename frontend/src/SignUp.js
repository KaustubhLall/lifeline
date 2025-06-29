import React, { useState } from 'react';
import config from './config';

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

    console.log('=== SIGNUP DEBUG START ===');
    console.log('Config API URL:', config.API_URL);
    console.log('Window location:', window.location.href);

    try {
      const registerUrl = `${config.API_URL}/api/register/`;
      console.log('Registration URL:', registerUrl);

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

      console.log('Registration response status:', response.status);
      console.log('Registration response ok:', response.ok);

      if (!response.ok) {
        const responseText = await response.text();
        console.log('Error response text:', responseText);
        let errorData;
        try {
          errorData = responseText ? JSON.parse(responseText) : { detail: 'Registration failed' };
        } catch {
          errorData = { detail: `Registration failed: ${response.status}` };
        }
        console.error('Registration failed:', errorData);
        throw new Error(errorData.detail || 'Registration failed');
      }

      const data = await response.json();
      console.log('Registration successful:', data);
      console.log('=== SIGNUP SUCCESS ===');

      // Call onLogin with the registration data directly
      onLogin(data);

    } catch (err) {
      console.error('=== SIGNUP ERROR ===');
      console.error('Error details:', err);

      let errorMessage = 'Registration failed. Please try again.';

      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError') || err.name === 'TypeError') {
        errorMessage = `Network error: Cannot connect to server at ${config.API_URL}. Please check if the backend server is running.`;
      } else {
        errorMessage = err.message || 'Registration failed. Please try again.';
      }

      setError(errorMessage);
    } finally {
      setIsLoading(false);
      console.log('=== SIGNUP DEBUG END ===');
    }
  };

  return (
    <div className="container">
      <div className="row justify-content-center align-items-center min-vh-100">
        <div className="col-12 col-sm-8 col-md-6 col-lg-4">
          <div className="card">
            <div className="card-body">
              <h2 className="card-title text-center mb-4">Sign Up</h2>
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
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    disabled={isLoading}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="email" className="form-label">Email</label>
                  <input
                    type="email"
                    className="form-control"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
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
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    disabled={isLoading}
                    required
                  />
                </div>
                <div className="mb-3">
                  <label htmlFor="confirmPassword" className="form-label">Confirm Password</label>
                  <input
                    type="password"
                    className="form-control"
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    disabled={isLoading}
                    required
                  />
                </div>
                <button
                  type="submit"
                  className="btn btn-primary w-100 mb-3"
                  disabled={isLoading}
                >
                  {isLoading ? 'Creating Account...' : 'Sign Up'}
                </button>
                <div className="text-center">
                  <a href="/login" onClick={(e) => {e.preventDefault(); window.history.back();}}>
                    Already have an account? Login
                  </a>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SignUp;
