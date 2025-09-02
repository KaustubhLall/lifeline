import React from 'react';
import '../styles/components/MessageMetadata.css';
import { formatDuration } from '../utils/formatUtils';

function MessageMetadata({metadata, onOpenSettings}) {
    const fmt = (n) => (typeof n === 'number' ? n.toLocaleString() : n);
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
        total_tokens,
        agent_tokens,
        tool_tokens,
        tools_token_breakdown,
        steps_total_duration_ms,
        tools_total_duration_ms
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
                                <span className="metadata-label">Latency (wall-clock)</span>
                                <span className="metadata-value">{formatDuration(latency_ms)}</span>
                            </div>
                        )}
                        {token_usage && mode !== 'agent' && (
                            <div className="metadata-item">
                                <span className="metadata-label">Tokens (total)</span>
                                <span className="metadata-value">
                                {fmt(token_usage.total_tokens)}
                                    {token_usage.prompt_tokens && token_usage.completion_tokens && (
                                        <span
                                            className="token-breakdown"> ({fmt(token_usage.prompt_tokens)}+{fmt(token_usage.completion_tokens)})</span>
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
                                <span className="metadata-label">Total Tokens (all)</span>
                                <span className="metadata-value">
                                    {fmt(agent_tokens || 0)}+{fmt(tool_tokens || 0)}/{fmt(total_tokens)}
                                </span>
                            </div>
                        )}
                        {mode === 'agent' && agent_tokens !== undefined && agent_tokens > 0 && (
                            <div className="metadata-item">
                                <span className="metadata-label">Agent Tokens</span>
                                <span className="metadata-value">{fmt(agent_tokens)}</span>
                            </div>
                        )}
                        {mode === 'agent' && tool_tokens !== undefined && tool_tokens > 0 && (
                            <div className="metadata-item">
                                <span className="metadata-label">Tool Tokens</span>
                                <span className="metadata-value">{fmt(tool_tokens)}</span>
                            </div>
                        )}
                        {mode === 'agent' && steps_total_duration_ms !== undefined && (
                            <div className="metadata-item">
                                <span className="metadata-label">Steps Runtime (sum)</span>
                                <span className="metadata-value">{formatDuration(steps_total_duration_ms)}</span>
                            </div>
                        )}
                        {mode === 'agent' && tools_total_duration_ms !== undefined && (
                            <div className="metadata-item">
                                <span className="metadata-label">Tools Runtime (sum)</span>
                                <span className="metadata-value">{formatDuration(tools_total_duration_ms)}</span>
                            </div>
                        )}
                        {mode === 'agent' && (agent_tokens || tool_tokens) && (
                            <div className="metadata-item" style={{gridColumn: '1 / -1'}}>
                                <span className="metadata-hint">Agent + Tool = Total</span>
                            </div>
                        )}
                        {mode === 'agent' && total_tokens > 0 && (agent_tokens || 0) + (tool_tokens || 0) !== total_tokens && (
                            <div className="metadata-item" style={{gridColumn: '1 / -1'}}>
                                <span className="metadata-warning">Mismatch: {fmt((agent_tokens || 0) + (tool_tokens || 0))} ≠ {fmt(total_tokens)}</span>
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
                                        ({tools_token_breakdown && tools_token_breakdown.length > 0 ? tools_token_breakdown.length : (tool_calls ? tool_calls.length : 0)})</h4>
                                    {((tools_token_breakdown && tools_token_breakdown.length > 0) || (tool_calls && tool_calls.length > 0)) ? (
                                        <ul className="agent-list">
                                            {(
                                                (tools_token_breakdown && tools_token_breakdown.length > 0)
                                                    ? tools_token_breakdown.map((t, index) => ({
                                                        key: index,
                                                        name: t.tool_name || 'tool',
                                                        // Sum duration across API calls when provided by backend
                                                        latency_ms: t.duration_ms_total || 0,
                                                        api_calls: t.api_calls || 0,
                                                        tokensTotal: t.tokens || 0,
                                                        metrics: null,
                                                    }))
                                                    : tool_calls.map((tool, index) => ({
                                                        key: index,
                                                        name: tool.tool_name,
                                                        latency_ms: tool.latency_ms || tool.duration_ms || 0,
                                                        api_calls: (tool.metrics && tool.metrics.api_calls) ? tool.metrics.api_calls : 1,
                                                        tokensTotal: (tool.tokens && tool.tokens.total) ? tool.tokens.total : 0,
                                                        metrics: tool.metrics || null,
                                                        concurrency: (tool.metrics && tool.metrics.concurrency) || null,
                                                    }))
                                            ).map((item) => (
                                                <li key={item.key} className="agent-item">
                                                    <div className="agent-item-main">
                                                        <span className="tool-name">{item.name}{item.api_calls > 1 ? ` (${fmt(item.api_calls)} ${item.concurrency || 'async'} calls)` : ''}</span>
                                                        <span className="tool-latency">{formatDuration(item.latency_ms)}</span>
                                                    </div>
                                                    {(item.tokensTotal > 0 || (item.metrics && (item.metrics.model || item.metrics.usage || item.metrics.input_count || item.metrics.extracted_count))) && (
                                                        <div className="agent-item-details">
                                                            {item.tokensTotal > 0 && (
                                                                <span className="step-detail">{fmt(item.tokensTotal)} tokens</span>
                                                            )}
                                                            {item.concurrency && (
                                                                <span className="step-detail">{item.concurrency}</span>
                                                            )}
                                                            {item.metrics?.model && (
                                                                <span className="step-detail">{item.metrics.model}</span>
                                                            )}
                                                            {item.metrics?.input_count !== undefined && (
                                                                <span className="step-detail">{fmt(item.metrics.input_count)} inputs</span>
                                                            )}
                                                            {item.metrics?.extracted_count !== undefined && (
                                                                <span className="step-detail">{fmt(item.metrics.extracted_count)} extracted</span>
                                                            )}
                                                        </div>
                                                    )}
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
                                                        <span className="step-duration">{formatDuration(step.duration_ms)}</span>
                                                    </div>
                                                    {(step.tokens?.total > 0 || step.tool_calls_count > 0 || step.message_type || step.tool_name) && (
                                                        <div className="agent-item-details">
                                                            {step.tokens && step.tokens.total > 0 && (
                                                                <span
                                                                    className="step-detail">{fmt(step.tokens.total)} tokens</span>
                                                            )}
                                                            {step.tool_calls_count > 0 && (
                                                                <span
                                                                    className="step-detail">{step.tool_calls_count} calls</span>
                                                            )}
                                                            {step.message_type && (
                                                                <span
                                                                    className="step-detail">{step.message_type.replace('Message', '')}</span>
                                                            )}
                                                            {step.tool_name && (
                                                                <span className="step-detail">{`Tool: ${step.tool_name}${step.tool_calls_count_by_name > 1 ? ` (${fmt(step.tool_calls_count_by_name)} ${step.concurrency_type || 'async'} calls)` : ''}`}</span>
                                                            )}
                                                            {step.concurrency_type && (
                                                                <span className="step-detail">{`Concurrency: ${step.concurrency_type}${step.tool_calls_in_step ? ` (${fmt(step.tool_calls_in_step)} calls)` : ''}`}</span>
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
