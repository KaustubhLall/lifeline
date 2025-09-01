import React, {useEffect, useRef} from 'react';
import '../styles/components/ChatInput.css';

function ChatInput({onSend, onSTT, input, setInput, isSending, isListening, sttSupported}) {
    const textareaRef = useRef(null);
    const formRef = useRef(null);

    const handleSTTClick = async () => {
        console.log('STT button clicked!', {sttSupported, isListening});
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
        const form = formRef.current;
        if (textarea && form) {
            // Reset height to auto to get the correct scrollHeight
            textarea.style.height = 'auto';

            // Calculate new height with min and max constraints
            const scrollHeight = textarea.scrollHeight;
            const minHeight = 48; // Match CSS min-height
            const maxHeight = window.innerHeight * 0.4; // 40% of screen height

            const newHeight = Math.min(Math.max(scrollHeight, minHeight), maxHeight);
            textarea.style.height = `${newHeight}px`;

            // Add expanded class when textarea grows beyond single line
            if (newHeight > minHeight + 10) { // Add some tolerance
                form.classList.add('expanded');
            } else {
                form.classList.remove('expanded');
            }
        }
    };

    // Handle Enter key for submission (Shift+Enter for new line)
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!isSending) {
                onSend();
            }
        }
    };

    // Adjust height when input changes from external sources (like STT)
    useEffect(() => {
        adjustTextareaHeight();
    }, [input]);

    return (
        <form
            ref={formRef}
            className="chat-input-form"
            onSubmit={e => {
                e.preventDefault();
                if (!isSending) {
                    onSend();
                }
            }}
        >
            <textarea
                ref={textareaRef}
                className="message-input"
                placeholder={isSending ? "Generating response..." : "Type a message... (Shift+Enter for new line)"}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                rows={1}
                disabled={isSending}
            />
            <div className="button-stack">
                <button
                    type="button"
                    className={`stt-button ${isListening ? 'active' : ''} ${sttSupported ? '' : 'disabled'}`}
                    onClick={handleSTTClick}
                    title={sttSupported ? (isListening ? "Recording..." : "Click to speak") : "Speech Recognition not supported"}
                    disabled={!sttSupported || isSending}
                >
                    <i className="bi bi-mic-fill"></i>
                </button>
                <button
                    className="send-button"
                    type="submit"
                    disabled={!input.trim() || isSending}
                    aria-label="Send"
                >
                    {isSending ? <div className="send-spinner"></div> : <i className="bi bi-arrow-up"></i>}
                </button>
            </div>
        </form>
    );
}

export default ChatInput;
