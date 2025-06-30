import React from 'react';
import '../styles/components/Header.css';

function Header({
    onToggleSidebar,
    selectedModel,
    setSelectedModel,
    chatMode,
    setChatMode,
    showMobileMenu,
    setShowMobileMenu,
    onLogout,
    models,
    chatModes
}) {
    return (
        <div className="app-header">
            {/* Left Section */}
            <div className="header-left">
                <button
                    className="menu-button"
                    onClick={onToggleSidebar}
                    aria-label="Open conversations"
                >
                    <i className="bi bi-chat-dots"></i>
                    <span className="menu-button-text">Conversations</span>
                </button>
            </div>

            {/* Center Section (Desktop Only) */}
            <div className="header-center">
                <h5 className="app-title">AI Assistant</h5>
                <div className="model-controls">
                    <div className="control-group">
                        <label className="control-label" htmlFor="modelSelect">
                            Model
                        </label>
                        <select
                            id="modelSelect"
                            className="model-selector"
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                        >
                            {models.map(model => (
                                <option key={model.value} value={model.value}>{model.label}</option>
                            ))}
                        </select>
                    </div>
                    <div className="control-group">
                        <label className="control-label" htmlFor="modeSelect">
                            Mode
                        </label>
                        <select
                            id="modeSelect"
                            className="mode-selector"
                            value={chatMode}
                            onChange={(e) => setChatMode(e.target.value)}
                        >
                            {chatModes.map(mode => (
                                <option key={mode.value} value={mode.value}>{mode.label}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Right Section */}
            <div className="header-right">
                {/* Mobile Controls Dropdown */}
                <div className="mobile-controls">
                    <div className="mobile-dropdown">
                        <button
                            className="settings-button"
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowMobileMenu(!showMobileMenu);
                            }}
                            aria-label="Settings"
                        >
                            <i className="bi bi-gear"></i>
                        </button>
                        <div className={`mobile-dropdown-content ${showMobileMenu ? 'show' : ''}`}>
                            <div className="mobile-form-group">
                                <label htmlFor="mobileModelSelect" className="mobile-label">Model</label>
                                <select
                                    id="mobileModelSelect"
                                    className="mobile-selector"
                                    value={selectedModel}
                                    onChange={(e) => setSelectedModel(e.target.value)}
                                >
                                    {models.map(model => (
                                        <option key={model.value} value={model.value}>{model.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="mobile-form-group">
                                <label htmlFor="mobileModeSelect" className="mobile-label">Mode</label>
                                <select
                                    id="mobileModeSelect"
                                    className="mobile-selector"
                                    value={chatMode}
                                    onChange={(e) => setChatMode(e.target.value)}
                                >
                                    {chatModes.map(mode => (
                                        <option key={mode.value} value={mode.value}>{mode.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="mobile-actions">
                                <button
                                    className="mobile-action-btn close-btn"
                                    onClick={() => setShowMobileMenu(false)}
                                    aria-label="Close menu"
                                >
                                    <i className="bi bi-x"></i>
                                    <span>Close</span>
                                </button>
                                <button
                                    className="mobile-action-btn logout-btn"
                                    onClick={() => {
                                        setShowMobileMenu(false);
                                        onLogout();
                                    }}
                                    aria-label="Logout"
                                >
                                    <i className="bi bi-box-arrow-right"></i>
                                    <span>Logout</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Desktop Logout */}
                <button
                    className="desktop-logout-btn"
                    onClick={onLogout}
                    aria-label="Logout"
                >
                    <i className="bi bi-box-arrow-right"></i>
                    <span className="logout-text">Logout</span>
                </button>
            </div>
        </div>
    );
}

export default Header;
