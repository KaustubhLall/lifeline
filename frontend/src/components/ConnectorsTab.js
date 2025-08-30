import React, {useEffect, useState} from 'react';
import '../styles/components/MCPConnectors.css';
import {API_BASE, fetchWithAuth} from '../utils/apiUtils';

const ConnectorsTab = () => {
    const [gmailStatus, setGmailStatus] = useState(null);
    const [operations, setOperations] = useState([]);
    const [showTestDialog, setShowTestDialog] = useState(false);
    const [showUploadDialog, setShowUploadDialog] = useState(false);
    const [testResult, setTestResult] = useState(null);
    const [uploadError, setUploadError] = useState('');
    const [uploadSuccess, setUploadSuccess] = useState('');
    const [loading, setLoading] = useState(true);
    const [redirectUri, setRedirectUri] = useState('');

    useEffect(() => {
        fetchGmailStatus();
        handleOAuthCallback();
    }, []);

    useEffect(() => {
        if (showUploadDialog) {
            fetchRedirectUri();
        }
    }, [showUploadDialog]);

    const handleOAuthCallback = () => {
        const urlParams = new URLSearchParams(window.location.search);
        const authSuccess = urlParams.get('auth_success');
        const authError = urlParams.get('auth_error');

        if (authSuccess === 'gmail') {
            setTimeout(() => {
                alert('Gmail authentication successful!');
                fetchGmailStatus();
                window.history.replaceState({}, '', window.location.pathname);
                sessionStorage.removeItem('mcp_auth_tab');
            }, 100);
        } else if (authError) {
            setTimeout(() => {
                const errorMessages = {
                    'access_denied': 'Gmail authentication was cancelled',
                    'missing_code_or_state': 'Authentication failed - missing parameters',
                    'invalid_user': 'Invalid user session',
                    'callback_failed': 'Gmail authentication failed',
                    'server_error': 'Server error during authentication'
                };

                const message = errorMessages[authError] || `Authentication failed: ${authError}`;
                alert(message);
                window.history.replaceState({}, '', window.location.pathname);
            }, 100);
        }
    };

    const fetchGmailStatus = async () => {
        try {
            setLoading(true);
            const response = await fetchWithAuth(`${API_BASE}/mcp/gmail/status/`);
            const data = await response.json();
            console.log('Gmail status response:', data);
            setGmailStatus(data);
            setOperations(data.recent_operations || []);
        } catch (error) {
            console.error('Error fetching Gmail status:', error);
            setGmailStatus({
                authenticated: false,
                status: 'not_configured',
                message: 'Gmail connector not configured',
                recent_operations: []
            });
        } finally {
            setLoading(false);
        }
    };

    const handleGmailAuth = async () => {
        try {
            const response = await fetchWithAuth(`${API_BASE}/mcp/gmail/auth/`);
            const data = await response.json();

            if (data.authenticated) {
                alert('Already authenticated with Gmail!');
                fetchGmailStatus();
            } else if (data.auth_url) {
                sessionStorage.setItem('mcp_auth_tab', 'connectors');
                window.location.href = data.auth_url;
            } else if (data.error && data.error.includes('OAuth configuration file not found')) {
                setShowUploadDialog(true);
            } else if (data.error) {
                alert(`Authentication error: ${data.error}`);
            }
        } catch (error) {
            console.error('Error initiating Gmail auth:', error);

            // Check if this is a 400 error (missing OAuth config) using proper error handling
            if (error.response && error.response.status === 400) {
                try {
                    const errorData = await error.response.json();
                    if (errorData.requires_config || (errorData.error && errorData.error.includes('OAuth configuration file not found'))) {
                        setShowUploadDialog(true);
                        return;
                    }
                } catch (parseError) {
                    console.error('Error parsing 400 response:', parseError);
                }
            }

            alert('Failed to initiate Gmail authentication');
        }
    };

    const handleOAuthUpload = async (file) => {
        try {
            setUploadError('');
            setUploadSuccess('');

            const formData = new FormData();
            formData.append('oauth_config', file);

            // For file uploads, we need to use a different approach since FormData can't use fetchWithAuth
            const token = localStorage.getItem('authToken');
            const response = await fetch(`${API_BASE}/mcp/gmail/upload-config/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Token ${token}`,
                },
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                setUploadSuccess('OAuth configuration uploaded successfully!');
                setTimeout(() => {
                    setShowUploadDialog(false);
                    fetchGmailStatus();
                }, 2000);
            } else {
                setUploadError(data.error || 'Failed to upload configuration');
            }
        } catch (error) {
            console.error('Error uploading OAuth config:', error);
            setUploadError('Failed to upload configuration');
        }
    };

    const handleTestOperation = async (operation, data) => {
        try {
            setTestResult({loading: true});

            const response = await fetchWithAuth(`${API_BASE}/mcp/gmail/operations/`, {
                method: 'POST',
                body: JSON.stringify({
                    operation,
                    data
                })
            });

            const result = await response.json();
            setTestResult(result);
            fetchGmailStatus();
        } catch (error) {
            console.error('Error testing operation:', error);
            setTestResult({error: 'Failed to execute operation'});
        }
    };

    const renderGmailConnector = () => {
        const status = gmailStatus || {
            authenticated: false,
            status: 'not_configured',
            message: 'Gmail connector not configured'
        };

        const statusColor = {
            active: '#4CAF50',
            pending: '#FF9800',
            error: '#F44336',
            not_configured: '#757575'
        }[status.status] || '#757575';

        return (
            <div className="connector-card">
                <div className="connector-header">
                    <h4>Gmail MCP Connector</h4>
                    <span
                        className="status-badge"
                        style={{backgroundColor: statusColor}}
                    >
                        {status.status?.replace('_', ' ').toUpperCase() || 'UNKNOWN'}
                    </span>
                </div>

                <div className="connector-details">
                    <p><strong>Authenticated:</strong> {status.authenticated ? 'Yes' : 'No'}</p>
                    {status.last_authenticated && (
                        <p><strong>Last Auth:</strong> {new Date(status.last_authenticated).toLocaleString()}</p>
                    )}
                    {status.last_used && (
                        <p><strong>Last Used:</strong> {new Date(status.last_used).toLocaleString()}</p>
                    )}
                    {status.message && (
                        <p><strong>Status:</strong> {status.message}</p>
                    )}
                </div>

                <div className="connector-actions">
                    {!status.authenticated && (
                        <button onClick={handleGmailAuth} className="auth-button">
                            Authenticate Gmail
                        </button>
                    )}
                    <button onClick={() => setShowUploadDialog(true)} className="config-button">
                        {status.authenticated ? 'Re-upload Config' : 'Upload OAuth Config'}
                    </button>
                    <button
                        onClick={() => status.authenticated && setShowTestDialog(true)}
                        className="test-button"
                        disabled={!status.authenticated}
                        title={!status.authenticated ? 'Authenticate to test operations' : 'Test Operations'}
                    >
                        Test Operations
                    </button>
                    {status.authenticated && (
                        <button onClick={handleGmailAuth} className="reauth-button">
                            Re-authenticate
                        </button>
                    )}
                </div>
            </div>
        );
    };

    const renderOperationsHistory = () => {
        if (operations.length === 0) return null;

        return (
            <div className="operations-history">
                <h4>Recent Operations</h4>
                <div className="operations-list">
                    {operations.map((op) => (
                        <div key={op.id} className={`operation-item ${op.status}`}>
                            <div className="operation-header">
                                <span className="operation-type">{op.operation_type}</span>
                                <span className="operation-time">
                                    {new Date(op.started_at).toLocaleString()}
                                </span>
                            </div>
                            <div className="operation-details">
                                <span className={`operation-status ${op.status}`}>
                                    {op.status.toUpperCase()}
                                </span>
                                {op.duration_ms && (
                                    <span className="operation-duration">{op.duration_ms}ms</span>
                                )}
                            </div>
                            {op.error_message && (
                                <div className="operation-error">{op.error_message}</div>
                            )}
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    const renderTestDialog = () => {
        if (!showTestDialog) return null;

        const testOperations = [
            {
                name: 'List Labels',
                operation: 'list_labels',
                data: {}
            },
            {
                name: 'Search Recent Emails',
                operation: 'search_emails',
                data: {query: 'in:inbox', max_results: 5}
            },
            {
                name: 'Send Test Email',
                operation: 'send_email',
                data: {
                    to: ['test@example.com'],
                    subject: 'Test from LifeLine MCP',
                    body: 'This is a test email from the LifeLine Gmail MCP connector.'
                }
            }
        ];

        return (
            <div className="test-dialog-overlay">
                <div className="test-dialog">
                    <div className="test-dialog-header">
                        <h4>Test Gmail Operations</h4>
                        <button onClick={() => setShowTestDialog(false)} className="close-button">×</button>
                    </div>

                    <div className="test-dialog-content">
                        <div className="test-operations">
                            {testOperations.map((test, index) => (
                                <div key={index} className="test-operation">
                                    <h5>{test.name}</h5>
                                    <button
                                        onClick={() => handleTestOperation(test.operation, test.data)}
                                        className="test-op-button"
                                    >
                                        Execute
                                    </button>
                                </div>
                            ))}
                        </div>

                        {testResult && (
                            <div className="test-result">
                                <h5>Test Result</h5>
                                {testResult.loading ? (
                                    <div className="loading">Executing...</div>
                                ) : (
                                    <pre>{JSON.stringify(testResult, null, 2)}</pre>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    const renderUploadDialog = () => {
        if (!showUploadDialog) return null;

        return (
            <div className="test-dialog-overlay">
                <div className="test-dialog upload-dialog">
                    <div className="test-dialog-header">
                        <h4>Upload Gmail OAuth Configuration</h4>
                        <button onClick={() => setShowUploadDialog(false)} className="close-button">×</button>
                    </div>

                    <div className="test-dialog-content">
                        <div className="upload-instructions">
                            <h5>Setup Instructions:</h5>
                            <ol>
                                <li>Go to <a href="https://console.cloud.google.com/" target="_blank"
                                             rel="noopener noreferrer">Google Cloud Console</a></li>
                                <li>Create a new project or select an existing one</li>
                                <li>Go to "APIs & Services" → "Library"</li>
                                <li>Search for "Gmail API" and enable it</li>
                                <li>Go to "APIs & Services" → "Credentials"</li>
                                <li>Click "Create Credentials" → "OAuth client ID"</li>
                                <li>Choose "Web application" as application type</li>
                                <li>Add this redirect URI: <code>{redirectUri}</code></li>
                                <li>Download the JSON credentials file</li>
                                <li>Upload the file below</li>
                            </ol>
                        </div>

                        <div className="upload-section">
                            <h5>Upload OAuth Credentials:</h5>
                            <input
                                type="file"
                                accept=".json"
                                onChange={(e) => {
                                    if (e.target.files[0]) {
                                        handleOAuthUpload(e.target.files[0]);
                                    }
                                }}
                                className="file-input"
                            />
                            <p className="upload-note">
                                Select the JSON file you downloaded from Google Cloud Console
                            </p>
                        </div>

                        {uploadError && (
                            <div className="upload-error">
                                {uploadError}
                            </div>
                        )}

                        {uploadSuccess && (
                            <div className="upload-success">
                                {uploadSuccess}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    const fetchRedirectUri = async () => {
        try {
            const response = await fetchWithAuth(`${API_BASE}/mcp/gmail/upload-config/`);
            const data = await response.json();
            setRedirectUri(data.redirect_uri || `${window.location.origin}/api/auth/gmail/callback`);
        } catch (error) {
            console.error('Error fetching redirect URI:', error);
            setRedirectUri(`${window.location.origin}/api/auth/gmail/callback`);
        }
    };

    if (loading) {
        return (
            <div className="connectors-tab">
                <h3>MCP Connectors</h3>
                <div className="loading">Loading MCP connectors...</div>
            </div>
        );
    }

    return (
        <div className="connectors-tab">
            <h3>MCP Connectors</h3>
            <p className="connectors-description">
                Manage your Model Context Protocol integrations for enhanced AI capabilities.
            </p>

            {renderGmailConnector()}
            {renderOperationsHistory()}
            {renderTestDialog()}
            {renderUploadDialog()}
        </div>
    );
};

export default ConnectorsTab;
