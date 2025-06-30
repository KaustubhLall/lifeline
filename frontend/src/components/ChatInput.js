import React from 'react';
import '../styles/components/ChatInput.css';

function ChatInput({onSend, onSTT, input, setInput, sttActive, sttSupported}) {
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

    return (
        <form
            className="chat-input-form"
            onSubmit={e => {
                e.preventDefault();
                onSend();
            }}
        >
            <button
                type="button"
                className={`stt-button ${sttActive ? 'active' : ''} ${sttSupported ? '' : 'disabled'}`}
                onClick={handleSTTClick}
                title={sttSupported ? (sttActive ? "Recording..." : "Click to speak") : "Speech Recognition not supported"}
                disabled={!sttSupported}
            >
                🎤
            </button>
            <input
                className="message-input"
                type="text"
                placeholder="Type a message..."
                value={input}
                onChange={e => setInput(e.target.value)}
            />
            <button
                className="send-button"
                type="submit"
                disabled={!input.trim()}
                aria-label="Send"
            >
                🚀
            </button>
        </form>
    );
}

export default ChatInput;
