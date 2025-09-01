import React from 'react';
import '../styles/components/MessageMetadata.css';

function MessageMetadata({metadata, onOpenSettings}) {
    // Always render, but show "No metadata available" if empty
    const hasMetadata = metadata && Object.keys(metadata).length > 0;

    const {
        latency_ms,
        token_usage,
        history_messages_included,
        prompt_length,
        mode,
        model,
        tool_calls,
        used_memories,
        relevant_memories,
        conversation_memories,
        response_length,
        step_details,
        total_steps,
        total_tokens
    } = metadata;

    // Ensure used_memories is an array
    const memories = Array.isArray(used_memories) ? used_memories : [];

    return (
        <div className="message-metadata-container">
            {!hasMetadata ? (
                <div className="metadata-empty">
                    <p>No metadata available for this message.</p>
                </div>
            ) : (
                <>
                    <div className="metadata-grid">
                        {latency_ms !== undefined && (
                            <div className="metadata-item">
                                <span className="metadata-label">Latency</span>
                                <span className="metadata-value">{latency_ms} ms</span>
                            </div>
                        )}
                        {token_usage && (
                            <div className="metadata-item">
                                <span className="metadata-label">Tokens</span>
                                <span className="metadata-value">
                                {token_usage.total_tokens}
                                    {token_usage.prompt_tokens && token_usage.completion_tokens && (
                                        <span
                                            className="token-breakdown"> ({token_usage.prompt_tokens}+{token_usage.completion_tokens})</span>
                                    )}
                            </span>
                            </div>
                        )}
                        {model && (
                            <div className="metadata-item">
                                <span className="metadata-label">Model</span>
                                <span className="metadata-value">{model}</span>
                            </div>
                        )}
                        {mode && (
                            <div className="metadata-item">
                                <span className="metadata-label">Mode</span>
                                <span className="metadata-value">{mode}</span>
                            </div>
                        )}
                        {history_messages_included !== undefined && (
                            <div className="metadata-item">
                                <span className="metadata-label">History</span>
                                <span className="metadata-value">{history_messages_included} messages</span>
                            </div>
                        )}
                        {memories.length > 0 && (
                            <div className="metadata-item">
                                <span className="metadata-label">Memories</span>
                                <span className="metadata-value">{memories.length} used</span>
                            </div>
                        )}
                        {mode === 'agent' && total_steps !== undefined && (
                            <div className="metadata-item">
                                <span className="metadata-label">Steps</span>
                                <span className="metadata-value">{total_steps} executed</span>
                            </div>
                        )}
                        {mode === 'agent' && total_tokens !== undefined && total_tokens > 0 && (
                            <div className="metadata-item">
                                <span className="metadata-label">Agent Tokens</span>
                                <span className="metadata-value">{total_tokens}</span>
                            </div>
                        )}
                    </div>

                    <div className="memory-details">
                        <div className="memory-header">
                            <h4 className="memory-title">🧠 Used Memories ({memories.length})</h4>
                            <button onClick={() => onOpenSettings('Memories')} className="manage-memories-btn">
                                Manage Memories
                            </button>
                        </div>
                        {memories.length > 0 ? (
                            <ul className="memory-list">
                                {memories.map((memory, index) => (
                                    <li key={index} className="memory-item">
                                        <p className="memory-content">{memory.content}</p>
                                        {memory.score !== undefined && (
                                            <span className="memory-score">Score: {memory.score.toFixed(3)}</span>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="memory-empty">No memories were used for this response.</p>
                        )}
                    </div>

                    {mode === 'agent' && (
                        <div className="agent-details">
                            <div className="agent-horizontal-layout">
                                {/* Tools Used Section - Left Side */}
                                <div className="agent-section agent-section-left">
                                    <h4 className="agent-section-header">🔧 Tools
                                        ({tool_calls ? tool_calls.length : 0})</h4>
                                    {tool_calls && tool_calls.length > 0 ? (
                                        <ul className="agent-list">
                                            {tool_calls.map((tool, index) => (
                                                <li key={index} className="agent-item">
                                                    <div className="agent-item-main">
                                                        <span className="tool-name">{tool.tool_name}</span>
                                                        <span className="tool-latency">{tool.latency_ms}ms</span>
                                                    </div>
                                                </li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <p className="agent-empty">No tools used</p>
                                    )}
                                </div>

                                {/* Steps Taken Section - Right Side */}
                                <div className="agent-section agent-section-right">
                                    <h4 className="agent-section-header">⚡ Steps
                                        ({step_details ? step_details.length : 0})</h4>
                                    {step_details && step_details.length > 0 ? (
                                        <ul className="agent-list">
                                            {step_details.map((step, index) => (
                                                <li key={index} className="agent-item">
                                                    <div className="agent-item-main">
                                                        <span className="step-node">{step.node}</span>
                                                        <span className="step-duration">{step.duration_ms}ms</span>
                                                    </div>
                                                    {(step.tokens?.total > 0 || step.tool_calls_count > 0 || step.message_type) && (
                                                        <div className="agent-item-details">
                                                            {step.tokens && step.tokens.total > 0 && (
                                                                <span
                                                                    className="step-detail">{step.tokens.total} tokens</span>
                                                            )}
                                                            {step.tool_calls_count > 0 && (
                                                                <span
                                                                    className="step-detail">{step.tool_calls_count} calls</span>
                                                            )}
                                                            {step.message_type && (
                                                                <span
                                                                    className="step-detail">{step.message_type.replace('Message', '')}</span>
                                                            )}
                                                        </div>
                                                    )}
                                                </li>
                                            ))}
                                        </ul>
                                    ) : (
                                        <p className="agent-empty">No steps captured</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

export default MessageMetadata;
