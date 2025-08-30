import React, {useEffect, useState} from 'react';
import '../styles/components/MCPConnectors.css';

const MCPConnectors = () => {
    const [connectors, setConnectors] = useState([]);
    const [loading, setLoading] = useState(true);
    const [gmailStatus, setGmailStatus] = useState(null);
    const [operations, setOperations] = useState([]);
    const [showTestDialog, setShowTestDialog] = useState(false);
    const [showUploadDialog, setShowUploadDialog] = useState(false);
    const [testResult, setTestResult] = useState(null);
    const [uploadError, setUploadError] = useState('');
    const [uploadSuccess, setUploadSuccess] = useState('');

    useEffect(() => {
        fetchGmailStatus();

        // Handle OAuth callback parameters
        const urlParams = new URLSearchParams(window.location.search);
        const authSuccess = urlParams.get('auth_success');
        const authError = urlParams.get('auth_error');

        if (authSuccess === 'gmail') {
            // Show success message and refresh status
            setTimeout(() => {
                alert('Gmail authentication successful!');
                fetchGmailStatus();

                // Clean URL
                window.history.replaceState({}, '', window.location.pathname);

                // Restore previous state if available
                const returnTab = sessionStorage.getItem('mcp_auth_tab');
                if (returnTab === 'connectors') {
                    // User is already on the right tab, just refresh
                    sessionStorage.removeItem('mcp_auth_tab');
                    sessionStorage.removeItem('mcp_auth_return');
                }
            }, 100);
        } else if (authError) {
            // Show error message
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

                // Clean URL
                window.history.replaceState({}, '', window.location.pathname);
            }, 100);
        }
    }, []);

    const fetchGmailStatus = async () => {
        try {
            setLoading(true);
            const response = await fetch('/api/mcp/gmail/status/', {
                credentials: 'include',
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Gmail status response:', data);
            setGmailStatus(data);
            setOperations(data.recent_operations || []);
        } catch (error) {
            console.error('Error fetching Gmail status:', error);
            // Set a default status to show the interface even when there's an error
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

    const handleOAuthUpload = async (file) => {
        try {
            setUploadError('');
            setUploadSuccess('');

            const formData = new FormData();
            formData.append('oauth_config', file);

            const response = await fetch('/api/mcp/gmail/upload-config/', {
                method: 'POST',
                credentials: 'include',
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

    const handleGmailAuth = async () => {
        try {
            const response = await fetch('/api/mcp/gmail/auth/', {
                credentials: 'include',
            });
            const data = await response.json();

            if (data.authenticated) {
                alert('Already authenticated with Gmail!');
                fetchGmailStatus();
            } else if (data.auth_url) {
                // Store current page state before redirect
                sessionStorage.setItem('mcp_auth_return', window.location.pathname);
                sessionStorage.setItem('mcp_auth_tab', 'connectors');

                // Direct redirect instead of popup
                window.location.href = data.auth_url;
            } else if (data.error && data.error.includes('OAuth configuration file not found')) {
                // Show upload dialog if OAuth config is missing
                setShowUploadDialog(true);
            }
        } catch (error) {
            console.error('Error initiating Gmail auth:', error);
            alert('Failed to initiate Gmail authentication');
        }
    };

    const handleTestOperation = async (operation, data) => {
        try {
            setTestResult({loading: true});

            const response = await fetch('/api/mcp/gmail/operations/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({
                    operation,
                    data
                })
            });

            const result = await response.json();
            setTestResult(result);

            // Refresh operations list
            fetchGmailStatus();
        } catch (error) {
            console.error('Error testing operation:', error);
            setTestResult({error: 'Failed to execute operation'});
        }
    };

    const renderUploadDialog = () => {
        if (!showUploadDialog) return null;

        return (
            <div className="test-dialog-overlay">
                <div className="test-dialog upload-dialog">
                    <div className="test-dialog-header">
                        <h3>Upload Gmail OAuth Configuration</h3>
                        <button onClick={() => setShowUploadDialog(false)} className="close-button">×</button>
                    </div>

                    <div className="test-dialog-content">
                        <div className="upload-instructions">
                            <h4>Setup Instructions:</h4>
                            <ol>
                                <li>Go to <a href="https://console.cloud.google.com/" target="_blank"
                                             rel="noopener noreferrer">Google Cloud Console</a></li>
                                <li>Create a new project or select an existing one</li>
                                <li>Go to "APIs & Services" → "Library"</li>
                                <li>Search for "Gmail API" and enable it</li>
                                <li>Go to "APIs & Services" → "Credentials"</li>
                                <li>Click "Create Credentials" → "OAuth client ID"</li>
                                <li>Choose "Web application" as application type</li>
                                <li>Add this redirect URI: <code>{window.location.origin}/api/auth/gmail/callback</code>
                                </li>
                                <li>Download the JSON credentials file</li>
                                <li>Upload the file below</li>
                            </ol>
                        </div>

                        <div className="upload-section">
                            <h4>Upload OAuth Credentials:</h4>
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

    const renderGmailStatus = () => {
        // Always render the Gmail connector card, even if status is null
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
                    <h3>Gmail MCP Connector</h3>
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
                    {!status.authenticated ? (
                        <div className="auth-actions">
                            <button onClick={handleGmailAuth} className="auth-button">
                                Authenticate Gmail
                            </button>
                            <button onClick={() => setShowUploadDialog(true)} className="config-button">
                                Upload OAuth Config
                            </button>
                        </div>
                    ) : (
                        <>
                            <button onClick={() => setShowTestDialog(true)} className="test-button">
                                Test Operations
                            </button>
                            <button onClick={handleGmailAuth} className="reauth-button">
                                Re-authenticate
                            </button>
                        </>
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
                        <h3>Test Gmail Operations</h3>
                        <button onClick={() => setShowTestDialog(false)} className="close-button">×</button>
                    </div>

                    <div className="test-dialog-content">
                        <div className="test-operations">
                            {testOperations.map((test, index) => (
                                <div key={index} className="test-operation">
                                    <h4>{test.name}</h4>
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
                                <h4>Test Result</h4>
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

    if (loading) {
        return (
            <div className="mcp-connectors">
                <div className="mcp-header">
                    <h2>MCP Connectors</h2>
                    <p>Manage your Model Context Protocol integrations</p>
                </div>
                <div className="loading">Loading MCP connectors...</div>
            </div>
        );
    }

    return (
        <div className="mcp-connectors">
            <div className="mcp-header">
                <h2>MCP Connectors</h2>
                <p>Manage your Model Context Protocol integrations</p>
            </div>

            {renderGmailStatus()}
            {renderOperationsHistory()}
            {renderTestDialog()}
            {renderUploadDialog()}
        </div>
    );
};

export default MCPConnectors;