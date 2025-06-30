import React, { useRef, useEffect } from 'react';
import '../styles/components/ChatInput.css';

function ChatInput({onSend, onSTT, input, setInput, sttActive, sttSupported}) {
    const textareaRef = useRef(null);

    const handleSTTClick = async () => {
        console.log('STT button clicked!', { sttSupported, sttActive });
        if (onSTT) {
            try {
                await onSTT();
            } catch (error) {
                console.error('STT error:', error);
            }
        } else {
            console.error('onSTT function not provided!');
        }
    };

    // Auto-resize textarea based on content
    const handleInputChange = (e) => {
        setInput(e.target.value);
        adjustTextareaHeight();
    };

    const adjustTextareaHeight = () => {
        const textarea = textareaRef.current;
        if (textarea) {
            // Reset height to auto to get the correct scrollHeight
            textarea.style.height = 'auto';

            // Calculate new height with min and max constraints
            const scrollHeight = textarea.scrollHeight;
            const minHeight = 48; // Match CSS min-height
            const maxHeight = window.innerHeight * 0.4; // 40% of screen height

            const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
            textarea.style.height = `${newHeight}px`;
        }
    };

    // Handle Enter key for submission (Shift+Enter for new line)
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            onSend();
        }
    };

    // Adjust height when input changes from external sources (like STT)
    useEffect(() => {
        adjustTextareaHeight();
    }, [input]);

    return (
        <form
            className="chat-input-form"
            onSubmit={e => {
                e.preventDefault();
                onSend();
            }}
        >
            <textarea
                ref={textareaRef}
                className="message-input"
                placeholder="Type a message... (Shift+Enter for new line)"
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                rows={1}
            />
            <div className="button-stack">
                <button
                    type="button"
                    className={`stt-button ${sttActive ? 'active' : ''} ${sttSupported ? '' : 'disabled'}`}
                    onClick={handleSTTClick}
                    title={sttSupported ? (sttActive ? "Recording..." : "Click to speak") : "Speech Recognition not supported"}
                    disabled={!sttSupported}
                >
                    🎤
                </button>
                <button
                    className="send-button"
                    type="submit"
                    disabled={!input.trim()}
                    aria-label="Send"
                >
                    🚀
                </button>
            </div>
        </form>
    );
}

export default ChatInput;
