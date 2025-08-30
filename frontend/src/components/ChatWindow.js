import React, {useEffect, useRef} from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {Prism as SyntaxHighlighter} from 'react-syntax-highlighter';
import {tomorrow} from 'react-syntax-highlighter/dist/esm/styles/prism';
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

    const MarkdownRenderer = ({content}) => {
        return (
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({node, inline, className, children, ...props}) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                            <SyntaxHighlighter
                                style={tomorrow}
                                language={match[1]}
                                PreTag="div"
                                {...props}
                            >
                                {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
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
            ))}
            <div ref={bottomRef}/>
        </div>
    );
}

export default ChatWindow;
