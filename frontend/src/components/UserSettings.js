import React, {useEffect, useState} from 'react';
import '../styles/components/UserSettings.css';
import {API_BASE, fetchWithAuth} from '../utils/apiUtils';
import ConnectorsTab from './ConnectorsTab';

function UserSettings({onClose, username}) {
    const [activeTab, setActiveTab] = useState('profile');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // Profile
    const [profileData, setProfileData] = useState({
        username: username || '',
        email: '',
        first_name: '',
        last_name: ''
    });
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);

    // Password change
    const [passwordData, setPasswordData] = useState({
        current_password: '',
        new_password: '',
        confirm_password: ''
    });

    // Memories
    const [memories, setMemories] = useState([]);
    const [memoriesPage, setMemoriesPage] = useState(1);
    const [totalMemoriesPages, setTotalMemoriesPages] = useState(1);
    const [editingMemory, setEditingMemory] = useState(null);
    const [editingContent, setEditingContent] = useState('');

    // Initial load
    useEffect(() => {
        fetchUserProfile();
    }, []);

    useEffect(() => {
        if (activeTab === 'memories') {
            fetchMemories();
        }
    }, [activeTab, memoriesPage]);

    // ---------------- Profile ----------------
    const fetchUserProfile = async () => {
        try {
            setLoading(true);
            const res = await fetchWithAuth(`${API_BASE}/user/profile/`);
            if (!res.ok) throw new Error('Failed to fetch profile');
            const data = await res.json();
            setProfileData({
                username: data.username || '',
                email: data.email || '',
                first_name: data.first_name || '',
                last_name: data.last_name || ''
            });
        } catch (err) {
            setError('Failed to load profile');
        } finally {
            setLoading(false);
        }
    };

    const handleProfileUpdate = async () => {
        if (!confirmPassword) {
            setError('Enter password to confirm');
            return;
        }
        try {
            setLoading(true);
            setError('');
            const res = await fetchWithAuth(`${API_BASE}/user/profile/`, {
                method: 'PATCH',
                body: JSON.stringify({...profileData, password: confirmPassword})
            });
            if (!res.ok) throw new Error('Failed to update profile');
            setSuccess('Profile updated');
            setConfirmPassword('');
            setShowPasswordConfirm(false);
            if (profileData.username !== username) {
                localStorage.setItem('username', profileData.username);
            }
        } catch (err) {
            setError('Failed to update profile');
        } finally {
            setLoading(false);
        }
    };

    // ---------------- Password ----------------
    const handlePasswordChange = async () => {
        if (passwordData.new_password !== passwordData.confirm_password) {
            setError('Passwords do not match');
            return;
        }
        if (passwordData.new_password.length < 8) {
            setError('Password must be at least 8 characters');
            return;
        }
        try {
            setLoading(true);
            setError('');
            const res = await fetchWithAuth(`${API_BASE}/user/change-password/`, {
                method: 'POST',
                body: JSON.stringify({
                    current_password: passwordData.current_password,
                    new_password: passwordData.new_password
                })
            });
            if (!res.ok) throw new Error('Failed to change password');
            setSuccess('Password changed');
            setPasswordData({current_password: '', new_password: '', confirm_password: ''});
        } catch (err) {
            setError('Failed to change password');
        } finally {
            setLoading(false);
        }
    };

    // ---------------- Memories ----------------
    const fetchMemories = async () => {
        try {
            setLoading(true);
            const res = await fetchWithAuth(`${API_BASE}/memories/?page=${memoriesPage}&page_size=10`);
            if (!res.ok) throw new Error('Failed to fetch memories');
            const data = await res.json();
            setMemories(data.memories || []);
            setTotalMemoriesPages(data.pagination?.total_pages || 1);
        } catch (err) {
            setError('Failed to load memories');
        } finally {
            setLoading(false);
        }
    };

    const startEditingMemory = (m) => {
        setEditingMemory(m.id);
        setEditingContent(m.content);
    };

    const cancelEditingMemory = () => {
        setEditingMemory(null);
        setEditingContent('');
    };

    const saveMemoryEdit = async (id) => {
        try {
            const res = await fetchWithAuth(`${API_BASE}/memories/${id}/`, {
                method: 'PATCH',
                body: JSON.stringify({content: editingContent})
            });
            if (!res.ok) throw new Error('Failed to update memory');
            setMemories(memories.map(m => m.id === id ? {...m, content: editingContent} : m));
            setEditingMemory(null);
            setEditingContent('');
            setSuccess('Memory updated');
        } catch (err) {
            setError('Failed to update memory');
        }
    };

    const deleteMemory = async (id) => {
        if (!window.confirm('Delete this memory?')) return;
        try {
            const res = await fetchWithAuth(`${API_BASE}/memories/${id}/`, {method: 'DELETE'});
            if (!res.ok) throw new Error('Failed to delete memory');
            setMemories(memories.filter(m => m.id !== id));
            setSuccess('Memory deleted');
        } catch (err) {
            setError('Failed to delete memory');
        }
    };

    const formatRelativeTime = (dateString) => {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diffH = Math.floor((now - date) / 3600000);
        if (diffH < 1) return 'Just now';
        if (diffH < 24) return `${diffH}h ago`;
        const d = Math.floor(diffH / 24);
        if (d < 7) return `${d}d ago`;
        const w = Math.floor(d / 7);
        if (w < 4) return `${w}w ago`;
        return `${Math.floor(d / 30)}mo ago`;
    };

    const getMemoryTags = (m) => {
        const tags = [];
        if (m.is_auto_extracted) tags.push({type: 'auto-extracted', label: 'Created', timestamp: m.created_at});
        if (m.edited_at) tags.push({type: 'user-edited', label: 'Edited', timestamp: m.edited_at});
        if (m.last_accessed_at) tags.push({type: 'last-accessed', label: 'Accessed', timestamp: m.last_accessed_at});
        return tags;
    };

    // ---------------- UI Sections ----------------
    const ProfileTab = () => (
        <div className="profile-tab">
            <h3>Profile Information</h3>
            <div className="form-group">
                <label>Username</label>
                <input
                    type="text"
                    className="form-control"
                    value={profileData.username}
                    onChange={e => setProfileData({...profileData, username: e.target.value})}
                />
            </div>
            <div className="form-group">
                <label>Email</label>
                <input
                    type="email"
                    className="form-control"
                    value={profileData.email}
                    onChange={e => setProfileData({...profileData, email: e.target.value})}
                />
            </div>
            <div className="form-group">
                <label>First Name</label>
                <input
                    type="text"
                    className="form-control"
                    value={profileData.first_name}
                    onChange={e => setProfileData({...profileData, first_name: e.target.value})}
                />
            </div>
            <div className="form-group">
                <label>Last Name</label>
                <input
                    type="text"
                    className="form-control"
                    value={profileData.last_name}
                    onChange={e => setProfileData({...profileData, last_name: e.target.value})}
                />
            </div>
            {!showPasswordConfirm ? (
                <button className="btn btn-primary" onClick={() => setShowPasswordConfirm(true)}>
                    Update Profile
                </button>
            ) : (
                <div className="password-confirm">
                    <div className="form-group">
                        <label>Confirm Password</label>
                        <input
                            type="password"
                            className="form-control"
                            value={confirmPassword}
                            onChange={e => setConfirmPassword(e.target.value)}
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
                            disabled={loading}
                            onClick={handleProfileUpdate}
                        >
                            {loading ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );

    const PasswordTab = () => (
        <div className="password-tab">
            <h3>Change Password</h3>
            <div className="form-group">
                <label>Current Password</label>
                <input
                    type="password"
                    className="form-control"
                    value={passwordData.current_password}
                    onChange={e => setPasswordData({...passwordData, current_password: e.target.value})}
                />
            </div>
            <div className="form-group">
                <label>New Password</label>
                <input
                    type="password"
                    className="form-control"
                    value={passwordData.new_password}
                    onChange={e => setPasswordData({...passwordData, new_password: e.target.value})}
                />
            </div>
            <div className="form-group">
                <label>Confirm New Password</label>
                <input
                    type="password"
                    className="form-control"
                    value={passwordData.confirm_password}
                    onChange={e => setPasswordData({...passwordData, confirm_password: e.target.value})}
                />
            </div>
            <button
                className="btn btn-primary"
                disabled={loading || !passwordData.current_password}
                onClick={handlePasswordChange}
            >
                {loading ? 'Changing...' : 'Change Password'}
            </button>
        </div>
    );

    const MemoriesTab = () => (
        <div className="memories-tab">
            <h3>Your Memories & Notes</h3>
            {loading && memories.length === 0 ? (
                <div className="loading">Loading memories...</div>
            ) : (
                <>
                    <div className="memories-list">
                        {memories.map(memory => (
                            <div key={memory.id} className="memory-card">
                                <div className="memory-tags">
                                    {getMemoryTags(memory).map((tag, i) => (
                                        <span key={i} className={`memory-tag ${tag.type}`}>
                                            {tag.label}
                                            {tag.timestamp && (
                                                <span className="tag-timestamp">
                                                    {' '}({formatRelativeTime(tag.timestamp)})
                                                </span>
                                            )}
                                        </span>
                                    ))}
                                </div>
                                {editingMemory === memory.id ? (
                                    <div className="memory-edit">
                                        <textarea
                                            className="form-control memory-textarea"
                                            rows={4}
                                            value={editingContent}
                                            onChange={e => setEditingContent(e.target.value)}
                                        />
                                        <div className="button-group">
                                            <button className="btn btn-secondary" onClick={cancelEditingMemory}>
                                                Cancel
                                            </button>
                                            <button className="btn btn-primary"
                                                    onClick={() => saveMemoryEdit(memory.id)}>
                                                Save
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="memory-content">{memory.content}</div>
                                )}
                                <div className="memory-meta">
                                    <span className="memory-type">{memory.memory_type || 'personal'}</span>
                                    <div className="memory-meta-right">
                                        <span className="memory-access">Accessed {memory.access_count || 0} times</span>
                                        <div className="memory-actions">
                                            {editingMemory !== memory.id && (
                                                <button
                                                    className="edit-btn"
                                                    onClick={() => startEditingMemory(memory)}
                                                    title="Edit"
                                                >
                                                    <i className="bi bi-pencil"/>
                                                </button>
                                            )}
                                            <button
                                                className="delete-btn"
                                                onClick={() => deleteMemory(memory.id)}
                                                title="Delete"
                                            >
                                                <i className="bi bi-trash"/>
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
                                disabled={memoriesPage === 1}
                                onClick={() => setMemoriesPage(p => Math.max(1, p - 1))}
                            >
                                Previous
                            </button>
                            <span className="page-info">Page {memoriesPage} of {totalMemoriesPages}</span>
                            <button
                                className="btn btn-secondary"
                                disabled={memoriesPage === totalMemoriesPages}
                                onClick={() => setMemoriesPage(p => Math.min(totalMemoriesPages, p + 1))}
                            >
                                Next
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    );

    return (
        <div className="user-settings-modal" onClick={(e) => e.stopPropagation()}>
            <div className="user-settings-header">
                <h2>User Settings</h2>
                <button onClick={onClose} className="close-btn">×</button>
            </div>
            <div className="user-settings-body">
                <div className="user-settings-tabs">
                    <button
                        className={`tab-button ${activeTab === 'profile' ? 'active' : ''}`}
                        onClick={() => setActiveTab('profile')}
                    >
                        Profile
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'password' ? 'active' : ''}`}
                        onClick={() => setActiveTab('password')}
                    >
                        Password
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'memories' ? 'active' : ''}`}
                        onClick={() => setActiveTab('memories')}
                    >
                        Memories
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'connectors' ? 'active' : ''}`}
                        onClick={() => setActiveTab('connectors')}
                    >
                        Connectors
                    </button>
                </div>
                <div className="user-settings-content">
                    {error && <div className="error-toast">{error}</div>}
                    {success && <div className="success-toast">{success}</div>}
                    {activeTab === 'profile' && <ProfileTab/>}
                    {activeTab === 'password' && <PasswordTab/>}
                    {activeTab === 'memories' && <MemoriesTab/>}
                    {activeTab === 'connectors' && <ConnectorsTab/>}
                </div>
            </div>
        </div>
    );
}

export default UserSettings;
