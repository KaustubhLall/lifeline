import React, {useEffect, useState} from 'react';
import '../styles/components/UserSettings.css';
import {API_BASE, fetchWithAuth} from '../utils/apiUtils';

function UserSettings({onClose, username, userId}) {
    const [activeTab, setActiveTab] = useState('profile');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Profile form state
    const [profileData, setProfileData] = useState({
        username: username || '',
        email: '',
        first_name: '',
        last_name: ''
    });

    // Password form state
    const [passwordData, setPasswordData] = useState({
        current_password: '',
        new_password: '',
        confirm_password: ''
    });

    // Password confirmation for profile changes
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);

    // Memories and notes data
    const [memories, setMemories] = useState([]);
    const [memoriesPage, setMemoriesPage] = useState(1);
    const [totalMemoriesPages, setTotalMemoriesPages] = useState(1);

    // Editing state for memories
    const [editingMemory, setEditingMemory] = useState(null);
    const [editingContent, setEditingContent] = useState('');

    useEffect(() => {
        fetchUserProfile();
    }, []);

    useEffect(() => {
        if (activeTab === 'memories') {
            fetchMemories();
        }
    }, [activeTab, memoriesPage]);

    const fetchUserProfile = async () => {
        try {
            setLoading(true);
            const response = await fetchWithAuth(`${API_BASE}/user/profile/`);
            const data = await response.json();
            setProfileData({
                username: data.username || '',
                email: data.email || '',
                first_name: data.first_name || '',
                last_name: data.last_name || ''
            });
        } catch (error) {
            setError('Failed to load profile data');
        } finally {
            setLoading(false);
        }
    };

    const fetchMemories = async () => {
        try {
            setLoading(true);
            const response = await fetchWithAuth(`${API_BASE}/memories/?page=${memoriesPage}&page_size=10`);
            const data = await response.json();
            setMemories(data.memories || []);
            setTotalMemoriesPages(data.pagination?.total_pages || 1);
        } catch (error) {
            setError('Failed to load memories');
        } finally {
            setLoading(false);
        }
    };

    const handleProfileUpdate = async () => {
        if (!confirmPassword) {
            setError('Please enter your password to confirm changes');
            return;
        }

        try {
            setLoading(true);
            setError('');

            const response = await fetchWithAuth(`${API_BASE}/user/profile/`, {
                method: 'PATCH',
                body: JSON.stringify({
                    ...profileData,
                    password: confirmPassword
                })
            });

            if (response.ok) {
                setSuccess('Profile updated successfully');
                setConfirmPassword('');
                setShowPasswordConfirm(false);
                // Update localStorage if username changed
                if (profileData.username !== username) {
                    localStorage.setItem('username', profileData.username);
                }
            }
        } catch (error) {
            setError('Failed to update profile');
        } finally {
            setLoading(false);
        }
    };

    const handlePasswordChange = async () => {
        if (passwordData.new_password !== passwordData.confirm_password) {
            setError('New passwords do not match');
            return;
        }

        if (passwordData.new_password.length < 8) {
            setError('Password must be at least 8 characters long');
            return;
        }

        try {
            setLoading(true);
            setError('');

            const response = await fetchWithAuth(`${API_BASE}/user/change-password/`, {
                method: 'POST',
                body: JSON.stringify({
                    current_password: passwordData.current_password,
                    new_password: passwordData.new_password
                })
            });

            if (response.ok) {
                setSuccess('Password changed successfully');
                setPasswordData({
                    current_password: '',
                    new_password: '',
                    confirm_password: ''
                });
            }
        } catch (error) {
            setError('Failed to change password');
        } finally {
            setLoading(false);
        }
    };

    const startEditingMemory = (memory) => {
        setEditingMemory(memory.id);
        setEditingContent(memory.content);
    };

    const cancelEditingMemory = () => {
        setEditingMemory(null);
        setEditingContent('');
    };

    const saveMemoryEdit = async (memoryId) => {
        try {
            const response = await fetchWithAuth(`${API_BASE}/memories/${memoryId}/`, {
                method: 'PATCH',
                body: JSON.stringify({
                    content: editingContent
                })
            });

            if (response.ok) {
                setMemories(memories.map(m =>
                    m.id === memoryId
                        ? {...m, content: editingContent}
                        : m
                ));
                setEditingMemory(null);
                setEditingContent('');
                setSuccess('Memory updated successfully');
            }
        } catch (error) {
            setError('Failed to update memory');
        }
    };

    const deleteMemory = async (memoryId) => {
        if (!window.confirm('Are you sure you want to delete this memory?')) {
            return;
        }

        try {
            await fetchWithAuth(`${API_BASE}/memories/${memoryId}/`, {
                method: 'DELETE'
            });
            setMemories(memories.filter(m => m.id !== memoryId));
            setSuccess('Memory deleted successfully');
        } catch (error) {
            setError('Failed to delete memory');
        }
    };

    const formatDate = (dateString) => {
        if (!dateString) return '';
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const formatRelativeTime = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diffInHours = Math.floor((now - date) / (1000 * 60 * 60));

        if (diffInHours < 1) return 'Just now';
        if (diffInHours < 24) return `${diffInHours}h ago`;
        const diffInDays = Math.floor(diffInHours / 24);
        if (diffInDays < 7) return `${diffInDays}d ago`;
        const diffInWeeks = Math.floor(diffInDays / 7);
        if (diffInWeeks < 4) return `${diffInWeeks}w ago`;
        const diffInMonths = Math.floor(diffInDays / 30);
        return `${diffInMonths}mo ago`;
    };

    const getMemoryTags = (memory) => {
        const tags = [];

        if (memory.is_auto_extracted) {
            tags.push({
                type: 'auto-extracted',
                label: 'Created',
                timestamp: memory.created_at
            });
        }

        if (memory.edited_at) {
            tags.push({
                type: 'user-edited',
                label: 'Edited',
                timestamp: memory.edited_at
            });
        }

        if (memory.last_accessed_at) {
            tags.push({
                type: 'last-accessed',
                label: 'Accessed',
                timestamp: memory.last_accessed_at
            });
        }

        return tags;
    };

    return (
        <div className="settings-overlay">
            <div className="settings-modal">
                <div className="settings-header">
                    <h2>User Settings</h2>
                    <button className="close-btn" onClick={onClose}>
                        <i className="bi bi-x"></i>
                    </button>
                </div>

                {error && (
                    <div className="alert alert-danger">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="alert alert-success">
                        {success}
                    </div>
                )}

                <div className="settings-tabs">
                    <button
                        className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`}
                        onClick={() => setActiveTab('profile')}
                    >
                        <i className="bi bi-person"></i>
                        Profile
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'password' ? 'active' : ''}`}
                        onClick={() => setActiveTab('password')}
                    >
                        <i className="bi bi-lock"></i>
                        Password
                    </button>
                    <button
                        className={`tab-btn ${activeTab === 'memories' ? 'active' : ''}`}
                        onClick={() => setActiveTab('memories')}
                    >
                        <i className="bi bi-journal-text"></i>
                        Memories
                    </button>
                </div>

                <div className="settings-content">
                    {activeTab === 'profile' && (
                        <div className="profile-tab">
                            <h3>Profile Information</h3>
                            <div className="form-group">
                                <label>Username</label>
                                <input
                                    type="text"
                                    value={profileData.username}
                                    onChange={(e) => setProfileData({...profileData, username: e.target.value})}
                                    className="form-control"
                                />
                            </div>
                            <div className="form-group">
                                <label>Email</label>
                                <input
                                    type="email"
                                    value={profileData.email}
                                    onChange={(e) => setProfileData({...profileData, email: e.target.value})}
                                    className="form-control"
                                />
                            </div>
                            <div className="form-group">
                                <label>First Name</label>
                                <input
                                    type="text"
                                    value={profileData.first_name}
                                    onChange={(e) => setProfileData({...profileData, first_name: e.target.value})}
                                    className="form-control"
                                />
                            </div>
                            <div className="form-group">
                                <label>Last Name</label>
                                <input
                                    type="text"
                                    value={profileData.last_name}
                                    onChange={(e) => setProfileData({...profileData, last_name: e.target.value})}
                                    className="form-control"
                                />
                            </div>

                            {!showPasswordConfirm ? (
                                <button
                                    className="btn btn-primary"
                                    onClick={() => setShowPasswordConfirm(true)}
                                >
                                    Update Profile
                                </button>
                            ) : (
                                <div className="password-confirm">
                                    <div className="form-group">
                                        <label>Confirm Password to Save Changes</label>
                                        <input
                                            type="password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            className="form-control"
                                            placeholder="Enter your current password"
                                        />
                                    </div>
                                    <div className="button-group">
                                        <button
                                            className="btn btn-secondary"
                                            onClick={() => {
                                                setShowPasswordConfirm(false);
                                                setConfirmPassword('');
                                            }}
                                        >
                                            Cancel
                                        </button>
                                        <button
                                            className="btn btn-primary"
                                            onClick={handleProfileUpdate}
                                            disabled={loading}
                                        >
                                            {loading ? 'Saving...' : 'Save Changes'}
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'password' && (
                        <div className="password-tab">
                            <h3>Change Password</h3>
                            <div className="form-group">
                                <label>Current Password</label>
                                <input
                                    type="password"
                                    value={passwordData.current_password}
                                    onChange={(e) => setPasswordData({
                                        ...passwordData,
                                        current_password: e.target.value
                                    })}
                                    className="form-control"
                                />
                            </div>
                            <div className="form-group">
                                <label>New Password</label>
                                <input
                                    type="password"
                                    value={passwordData.new_password}
                                    onChange={(e) => setPasswordData({...passwordData, new_password: e.target.value})}
                                    className="form-control"
                                />
                                <small className="form-text">Password must be at least 8 characters long</small>
                            </div>
                            <div className="form-group">
                                <label>Confirm New Password</label>
                                <input
                                    type="password"
                                    value={passwordData.confirm_password}
                                    onChange={(e) => setPasswordData({
                                        ...passwordData,
                                        confirm_password: e.target.value
                                    })}
                                    className="form-control"
                                />
                            </div>
                            <button
                                className="btn btn-primary"
                                onClick={handlePasswordChange}
                                disabled={loading || !passwordData.current_password || !passwordData.new_password}
                            >
                                {loading ? 'Changing...' : 'Change Password'}
                            </button>
                        </div>
                    )}

                    {activeTab === 'memories' && (
                        <div className="memories-tab">
                            <h3>Your Memories & Notes</h3>
                            {loading && memories.length === 0 ? (
                                <div className="loading">Loading memories...</div>
                            ) : (
                                <>
                                    <div className="memories-list">
                                        {memories.map((memory) => (
                                            <div key={memory.id} className="memory-card">
                                                <div className="memory-tags">
                                                    {getMemoryTags(memory).map((tag, index) => (
                                                        <span key={index} className={`memory-tag ${tag.type}`}>
                                                            {tag.label}
                                                            {tag.timestamp && (
                                                                <span className="tag-timestamp">
                                                                    ({formatRelativeTime(tag.timestamp)})
                                                                </span>
                                                            )}
                                                        </span>
                                                    ))}
                                                </div>

                                                {editingMemory === memory.id ? (
                                                    <div className="memory-edit">
                                                        <textarea
                                                            className="form-control memory-textarea"
                                                            value={editingContent}
                                                            onChange={(e) => setEditingContent(e.target.value)}
                                                            rows={4}
                                                        />
                                                        <div className="button-group">
                                                            <button
                                                                className="btn btn-secondary"
                                                                onClick={cancelEditingMemory}
                                                            >
                                                                Cancel
                                                            </button>
                                                            <button
                                                                className="btn btn-primary"
                                                                onClick={() => saveMemoryEdit(memory.id)}
                                                            >
                                                                Save
                                                            </button>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="memory-content">
                                                        {memory.content}
                                                    </div>
                                                )}

                                                <div className="memory-meta">
                                                    <span className="memory-type">
                                                        {memory.memory_type || 'personal'}
                                                    </span>
                                                    <div className="memory-meta-right">
                                                        <span className="memory-access">
                                                            Accessed {memory.access_count || 0} times
                                                        </span>
                                                        <div className="memory-actions">
                                                            {editingMemory !== memory.id && (
                                                                <button
                                                                    className="edit-btn"
                                                                    onClick={() => startEditingMemory(memory)}
                                                                    title="Edit memory"
                                                                >
                                                                    <i className="bi bi-pencil"></i>
                                                                </button>
                                                            )}
                                                            <button
                                                                className="delete-btn"
                                                                onClick={() => deleteMemory(memory.id)}
                                                                title="Delete memory"
                                                            >
                                                                <i className="bi bi-trash"></i>
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {totalMemoriesPages > 1 && (
                                        <div className="pagination">
                                            <button
                                                className="btn btn-secondary"
                                                onClick={() => setMemoriesPage(prev => Math.max(1, prev - 1))}
                                                disabled={memoriesPage === 1}
                                            >
                                                Previous
                                            </button>
                                            <span className="page-info">
                                                Page {memoriesPage} of {totalMemoriesPages}
                                            </span>
                                            <button
                                                className="btn btn-secondary"
                                                onClick={() => setMemoriesPage(prev => Math.min(totalMemoriesPages, prev + 1))}
                                                disabled={memoriesPage === totalMemoriesPages}
                                            >
                                                Next
                                            </button>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default UserSettings;
