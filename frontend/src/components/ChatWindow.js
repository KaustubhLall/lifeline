import React, {useEffect, useRef} from 'react';
import '../styles/components/ChatWindow.css';

function ChatWindow({messages, username}) {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({behavior: 'smooth'});
    }, [messages]);

    const formatTime = (timestamp) => {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    };

    return (
        <div className="chat-window">
            {messages.map(msg => (
                <div key={msg.id} className="message-container">
                    <div className={`message-header ${!msg.is_bot ? 'user' : 'bot'}`}>
                        <div className="message-sender">
                            {!msg.is_bot ? (
                                <>
                                    <span>{username || 'User'}</span>
                                    <i className="bi bi-person-circle"></i>
                                </>
                            ) : (
                                <>
                                    <i className="bi bi-robot"></i>
                                    <span>AI Assistant</span>
                                </>
                            )}
                        </div>
                        <span className="message-timestamp">{formatTime(msg.created_at)}</span>
                    </div>
                    <div className={`message-content ${!msg.is_bot ? 'user-content' : 'bot-content'}`}>
                        <div
                            className={`message ${!msg.is_bot ? 'user' : 'bot'} ${msg.pending ? 'pending' : ''} ${msg.error ? 'error' : ''}`}>
                            {msg.content}
                            {msg.pending && (
                                <div className="message-spinner">
                                    <div className="spinner-border spinner-border-sm ms-2" role="status">
                                        <span className="visually-hidden">Loading...</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            ))}
            <div ref={bottomRef}/>
        </div>
    );
}

export default ChatWindow;
