import React, { useState } from 'react';

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
    console.log('Starting signup process...');

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords don't match");
      setIsLoading(false);
      return;
    }

    try {
      console.log('Making registration request...');
      const response = await fetch('/api/register/', {
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
      const contentType = response.headers.get("content-type");
      console.log('Response content type:', contentType);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Registration failed. Server response:', errorText);
        throw new Error('Registration failed');
      }

      const data = await response.json();
      console.log('Registration successful, attempting login...');

      // Login automatically after successful registration
      const loginResponse = await fetch('/api/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: formData.username,
          password: formData.password,
        }),
      });

      console.log('Login response status:', loginResponse.status);

      if (!loginResponse.ok) {
        throw new Error('Login after registration failed');
      }

      const loginData = await loginResponse.json();
      localStorage.setItem('authToken', loginData.token);
      console.log('Auto-login successful');
      onLogin(loginData.token);
    } catch (err) {
      console.error('Signup/Login error:', err);
      setError(err.message || 'Registration failed. Please try again.');
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
