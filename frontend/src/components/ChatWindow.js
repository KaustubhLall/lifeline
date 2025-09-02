import React, {useState, useEffect, useRef} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {Prism as SyntaxHighlighter} from 'react-syntax-highlighter';
import {tomorrow} from 'react-syntax-highlighter/dist/esm/styles/prism';
import MessageMetadata from './MessageMetadata';
import '../styles/components/ChatWindow.css';

function ChatWindow({messages, username, onQuickAction, onOpenSettings}) {
    const bottomRef = useRef(null);
    const [visibleMetadataId, setVisibleMetadataId] = useState(null);
    const [renderTrigger, setRenderTrigger] = useState(0);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({behavior: 'smooth'});
    }, [messages]);

    // Force re-render when new messages arrive - especially with metadata
    useEffect(() => {
        // Trigger re-render after a short delay to ensure metadata is processed
        const timer = setTimeout(() => {
            setRenderTrigger(prev => prev + 1);
        }, 100);
        
        return () => clearTimeout(timer);
    }, [messages]);

    const toggleMetadata = (messageId) => {
        setVisibleMetadataId(prevId => (prevId === messageId ? null : messageId));
    };

    const handleCopyMessage = (content, e) => {
        navigator.clipboard.writeText(content).then(() => {
            const originalIcon = e.currentTarget.innerHTML;
            e.currentTarget.innerHTML = `<i class="bi bi-check-lg"></i>`;
            setTimeout(() => {
                e.currentTarget.innerHTML = originalIcon;
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy message: ', err);
        });
    };

    const formatTime = (timestamp) => {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    };

    const QuickActions = () => (
        <div className="quick-actions-container">
            <div className="quick-actions-grid">
                <button className="quick-action-btn" onClick={() => onQuickAction('Summarize my last 25 emails')}>
                    <i className="bi bi-envelope-paper"></i>
                    <span>Summarize my last 25 emails</span>
                </button>
                <button className="quick-action-btn" onClick={() => onQuickAction('What do you know about me?')}>
                    <i className="bi bi-person-badge"></i>
                    <span>What do you know about me?</span>
                </button>
                <button className="quick-action-btn" onClick={() => onQuickAction('Help me journal')}>
                    <i className="bi bi-journal-bookmark"></i>
                    <span>Help me journal</span>
                </button>
            </div>
        </div>
    );

    const MarkdownRenderer = ({content}) => {
        return (
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({node, inline, className, children, ...props}) {
                        const match = /language-(\w+)/.exec(className || '');
                        const codeText = String(children).replace(/\n$/, '');

                        const handleCopyCode = (e) => {
                            navigator.clipboard.writeText(codeText).then(() => {
                                const button = e.currentTarget;
                                button.innerHTML = '<i class="bi bi-check-lg"></i> Copied';
                                setTimeout(() => {
                                    button.innerHTML = '<i class="bi bi-clipboard"></i> Copy';
                                }, 2000);
                            }).catch(err => {
                                console.error('Failed to copy code: ', err);
                            });
                        };

                        return !inline && match ? (
                            <div className="code-block-container">
                                <div className="code-block-header">
                                    <span className="language-name">{match[1]}</span>
                                    <button className="copy-code-btn" onClick={handleCopyCode}>
                                        <i className="bi bi-clipboard"></i> Copy
                                    </button>
                                </div>
                                <SyntaxHighlighter
                                    style={tomorrow}
                                    language={match[1]}
                                    PreTag="div"
                                    {...props}
                                >
                                    {codeText}
                                </SyntaxHighlighter>
                            </div>
                        ) : (
                            <code className={className} {...props}>
                                {children}
                            </code>
                        );
                    },
                    // Style other markdown elements
                    h1: ({children}) => <h1 className="markdown-h1">{children}</h1>,
                    h2: ({children}) => <h2 className="markdown-h2">{children}</h2>,
                    h3: ({children}) => <h3 className="markdown-h3">{children}</h3>,
                    p: ({children}) => <p className="markdown-p">{children}</p>,
                    ul: ({children}) => <ul className="markdown-ul">{children}</ul>,
                    ol: ({children}) => <ol className="markdown-ol">{children}</ol>,
                    li: ({children}) => <li className="markdown-li">{children}</li>,
                    blockquote: ({children}) => <blockquote className="markdown-blockquote">{children}</blockquote>,
                    strong: ({children}) => <strong className="markdown-strong">{children}</strong>,
                    em: ({children}) => <em className="markdown-em">{children}</em>,
                    // Table components with wrapper and copy functionality
                    table: ({children}) => {
                        const copyTableToClipboard = (e) => {
                            const table = e.target.closest('.table-container').querySelector('table');
                            const rows = Array.from(table.querySelectorAll('tr'));
                            const csvContent = rows.map(row => {
                                const cells = Array.from(row.querySelectorAll('th, td'));
                                return cells.map(cell => cell.textContent.trim()).join('\t');
                            }).join('\n');
                            
                            navigator.clipboard.writeText(csvContent).then(() => {
                                e.target.textContent = 'Copied!';
                                setTimeout(() => {
                                    e.target.textContent = 'Copy';
                                }, 2000);
                            }).catch(() => {
                                e.target.textContent = 'Failed';
                                setTimeout(() => {
                                    e.target.textContent = 'Copy';
                                }, 2000);
                            });
                        };

                        return (
                            <div className="table-container">
                                <div className="table-actions">
                                    <button className="table-copy-btn" onClick={copyTableToClipboard}>
                                        Copy
                                    </button>
                                </div>
                                <table>{children}</table>
                            </div>
                        );
                    },
                    thead: ({children}) => <thead>{children}</thead>,
                    tbody: ({children}) => <tbody>{children}</tbody>,
                    tr: ({children}) => <tr>{children}</tr>,
                    th: ({children}) => <th>{children}</th>,
                    td: ({children}) => <td>{children}</td>,
                }}
            >
                {content}
            </ReactMarkdown>
        );
    };

    return (
        <div className="chat-window">
            {messages.length === 0 ? (
                <QuickActions />
            ) : (
                messages.map((msg, index) => (
                    <div key={`${msg.id}-${msg.metadata ? Object.keys(msg.metadata).length : 0}-${renderTrigger}`} className="message-container">
                        <div className={`message-header ${!msg.is_bot ? 'user' : 'bot'}`}>
                            <div className="message-header-left">
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
                            </div>
                            <div className="message-header-right">
                                <span className="message-timestamp">{formatTime(msg.created_at)}</span>
                                {process.env.NODE_ENV === 'development' && msg.is_bot && (
                                    <span className="message-meta-count" title="Number of metadata fields">
                                        {msg.metadata ? `metadata: ${Object.keys(msg.metadata).length}` : 'no metadata'}
                                    </span>
                                )}
                                {msg.is_bot && (
                                    <div className="message-actions">
                                        <button className="message-action-btn" onClick={(e) => handleCopyMessage(msg.content, e)} title="Copy message">
                                            <i className="bi bi-clipboard"></i>
                                        </button>
                                        <button className="message-action-btn" onClick={() => toggleMetadata(msg.id)} title="View details">
                                            <i className={`bi ${visibleMetadataId === msg.id ? 'bi-chevron-up' : 'bi-info-circle'}`}></i>
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                        {visibleMetadataId === msg.id && (
                            <MessageMetadata metadata={msg.metadata || {}} onOpenSettings={onOpenSettings} />
                        )}
                        <div className={`message-content ${!msg.is_bot ? 'user-content' : 'bot-content'}`}>
                            <div
                                className={`message ${!msg.is_bot ? 'user' : 'bot'} ${msg.pending ? 'pending' : ''} ${msg.error ? 'error' : ''}`}>
                                {msg.is_bot ? (
                                    <MarkdownRenderer content={msg.content} />
                                ) : (
                                    msg.content
                                )}
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
                ))
            )}
            <div ref={bottomRef}/>
        </div>
    );
}

export default ChatWindow;
