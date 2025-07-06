import React from 'react';
import '../styles/components/ChatSidebar.css';

function ChatSidebar({conversations, currentId, onSelect, onNewChat, onClose}) {
    return (
        <div className="chat-sidebar">
            <div className="sidebar-header">
                <h3 className="sidebar-title">Conversations</h3>
                <button
                    className="sidebar-close-btn"
                    onClick={onClose}
                    aria-label="Close sidebar"
                >
                    <i className="bi bi-x"></i>
                </button>
            </div>
            <button
                className="new-chat-button"
                onClick={onNewChat}
            >
                ✨ New Chat
            </button>
            {conversations.length === 0 ? (
                <div className="empty-conversations">
                    No conversations yet
                </div>
            ) : (
                conversations.map(conv => (
                    <button
                        key={conv.id}
                        className={`conversation-item ${conv.id === currentId ? 'active' : ''}`}
                        onClick={() => onSelect(conv.id)}
                    >
                        <div className="conversation-title">
                            {conv.title || `Chat #${conv.id}`}
                        </div>
                        <div className="conversation-id">
                            [ID: {conv.id}]
                        </div>
                    </button>
                ))
            )}
        </div>
    );
}

export default ChatSidebar;
