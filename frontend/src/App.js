import React, {useEffect, useRef, useState} from 'react';
import './App.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import Login from './Login';
import SignUp from './SignUp';
import config from './config';

// API endpoints
const API_BASE = `${config.API_URL}/api`;

// Helper function to add auth headers
const fetchWithAuth = async (url, options = {}) => {
    const token = localStorage.getItem('authToken');
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'Authorization': `Token ${token}`,
                'Content-Type': 'application/json',
            },
        });

        console.log(`API ${options.method || 'GET'} ${url}:`, {
            status: response.status,
            statusText: response.statusText
        });

        if (!response.ok) {
            const errorData = await response.text();
            console.error('Response error:', errorData);
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
};

function ChatSidebar({conversations, currentId, onSelect, onNewChat}) {
    return (
        <div className="list-group list-group-flush overflow-auto" style={{height: '100vh'}}>
            <button
                className="list-group-item list-group-item-action text-center fw-bold bg-primary text-white"
                onClick={onNewChat}
            >
                New Chat +
            </button>
            {conversations.length === 0 ? (
                <div className="list-group-item text-center text-muted">
                    No conversations yet
                </div>
            ) : (
                conversations.map(conv => (
                    <button
                        key={conv.id}
                        className={`list-group-item list-group-item-action${conv.id === currentId ? ' active' : ''}`}
                        onClick={() => onSelect(conv.id)}
                    >
                        {conv.title || `Chat #${conv.id}`}
                    </button>
                ))
            )}
        </div>
    );
}

function ChatWindow({messages, userId, username}) {
    const bottomRef = useRef(null);
    useEffect(() => {
        bottomRef.current?.scrollIntoView({behavior: 'smooth'});
    }, [messages]);

    const formatTime = (timestamp) => {
        if (!timestamp) return '';
        return new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    };

    return (
        <div className="flex-grow-1 overflow-auto px-3 py-4 chat-window" style={{minHeight: 0}}>
            {messages.map(msg => (
                <div key={msg.id} className="message-container">
                    <div className={`message-header ${!msg.is_bot ? 'user' : 'bot'}`}>
                        <div className="d-flex align-items-center gap-2">
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
                    <div className={`d-flex ${!msg.is_bot ? 'justify-content-end' : 'justify-content-start'}`}>
                        <div
                            className={`message ${!msg.is_bot ? 'user' : 'bot'} ${msg.pending ? 'pending' : ''} ${msg.error ? 'error' : ''}`}>
                            {msg.content}
                            {msg.pending && (
                                <div className="spinner-border spinner-border-sm ms-2" role="status">
                                    <span className="visually-hidden">Loading...</span>
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

function isSTTSupported() {
    return (
        typeof window !== 'undefined' &&
        ('mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices) &&
        typeof MediaRecorder !== 'undefined'
    );
}

function ChatInput({onSend, onSTT, input, setInput, sttActive, sttSupported}) {
    return (
        <form
            className="d-flex align-items-center gap-2 p-2 border-top bg-transparent chat-input-container"
            onSubmit={e => {
                e.preventDefault();
                onSend();
            }}
            style={{position: 'sticky', bottom: 0}}
        >
            <button
                type="button"
                className={`btn stt-button ${sttActive ? 'active' : ''} ${sttSupported ? '' : 'disabled'}`}
                onClick={onSTT}
                title={sttSupported ? (sttActive ? "Recording..." : "Click to speak") : "Speech Recognition not supported"}
                disabled={!sttSupported}
            >
                <img src="/mic.png" alt="Voice"/>
            </button>
            <input
                className="form-control"
                type="text"
                placeholder="Type a message..."
                value={input}
                onChange={e => setInput(e.target.value)}
                style={{fontSize: '1rem'}}
            />
            <button
                className="btn btn-primary send-button"
                type="submit"
                disabled={!input.trim()}
                aria-label="Send"
            >
                <i className="bi bi-arrow-right"></i>
            </button>
        </form>
    );
}

function App() {
    const [authenticated, setAuthenticated] = useState(!!localStorage.getItem('authToken'));
    const [showSignup, setShowSignup] = useState(false);
    const [conversations, setConversations] = useState([]);
    const [currentId, setCurrentId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [userId, setUserId] = useState(localStorage.getItem('userId'));
    const [username, setUsername] = useState(localStorage.getItem('username'));
    const [sttActive, setSttActive] = useState(false);
    const [error, setError] = useState(null);
    const [showSidebar, setShowSidebar] = useState(false);
    const [showMobileMenu, setShowMobileMenu] = useState(false);
    const [selectedModel, setSelectedModel] = useState('gpt-4.1-nano');
    const [chatMode, setChatMode] = useState('conversational');
    const sttSupported = isSTTSupported();
    const recognitionRef = useRef(null);
    const mediaStreamRef = useRef(null); // Keep stream active
    const isRecordingRef = useRef(false);

    const models = [
        {value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano'},
        {value: 'gpt-4o', label: 'GPT-4O'},
        {value: 'gpt-4o-mini', label: 'GPT-4O Mini'},
        {value: 'gpt-4.1', label: 'GPT-4.1'}
    ];

    const chatModes = [
        {value: 'conversational', label: 'Conversational'},
        {value: 'coaching', label: 'Coaching'}
    ];

    const handleLogin = (userData) => {
        // Store auth data first
        localStorage.setItem('authToken', userData.token);
        localStorage.setItem('userId', userData.user_id);
        localStorage.setItem('username', userData.username);

        // Update state
        setUserId(userData.user_id);
        setUsername(userData.username);
        setShowSignup(false);

        // Set authenticated last to ensure everything is ready
        setTimeout(() => {
            setAuthenticated(true);
        }, 100);
    };

    const handleLogout = () => {
        localStorage.removeItem('authToken');
        localStorage.removeItem('userId');
        localStorage.removeItem('username');
        setUserId(null);
        setUsername(null);
        setAuthenticated(false);
        setConversations([]);
        setCurrentId(null);
        setMessages([]);
        setShowSidebar(false);
        setShowMobileMenu(false);
    };

    // Close mobile menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (showMobileMenu && !event.target.closest('.mobile-dropdown')) {
                setShowMobileMenu(false);
            }
            if (showSidebar && !event.target.closest('.sidebar') && !event.target.closest('.menu-button')) {
                setShowSidebar(false);
            }
        };

        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [showMobileMenu, showSidebar]);

    const handleNewChat = async () => {
        try {
            const response = await fetchWithAuth(`${API_BASE}/conversations/`, {
                method: 'POST',
                body: JSON.stringify({
                    title: 'New Chat'
                })
            });

            if (!response.ok) throw new Error('Failed to create new chat');
            const newConversation = await response.json();
            setConversations(prev => [...prev, newConversation]);
            setCurrentId(newConversation.id);
            setMessages([]);
        } catch (e) {
            setError('Failed to create new conversation');
            console.error(e);
        }
    };

    // Fetch conversations
    useEffect(() => {
        if (!authenticated) return;

        fetchWithAuth(`${API_BASE}/conversations/`)
            .then(r => {
                if (!r.ok) throw new Error('Failed to fetch conversations');
                return r.json();
            })
            .then(setConversations)
            .catch(e => {
                if (e.message.includes('401') || e.message.includes('403')) {
                    handleLogout();
                } else {
                    setError('Could not load conversations.');
                    console.error(e);
                }
            });
    }, [authenticated]);

    // Fetch messages for current conversation
    useEffect(() => {
        if (!authenticated || !currentId) return;

        fetchWithAuth(`${API_BASE}/conversations/${currentId}/messages/`)
            .then(r => {
                if (!r.ok) throw new Error('Failed to fetch messages');
                return r.json();
            })
            .then(setMessages)
            .catch(e => {
                setError('Could not load messages.');
                console.error(e);
            });
    }, [currentId, authenticated]);

    // Select first conversation by default
    useEffect(() => {
        if (conversations.length && !currentId) setCurrentId(conversations[0].id);
    }, [conversations, currentId]);

    // Error handler component
    const ErrorToast = ({message, onClose}) => (
        <div className="toast show position-fixed top-0 end-0 m-3" role="alert" style={{zIndex: 1050}}>
            <div className="toast-header bg-danger text-white">
                <strong className="me-auto">Error</strong>
                <button type="button" className="btn-close btn-close-white" onClick={onClose}></button>
            </div>
            <div className="toast-body">{message}</div>
        </div>
    );

    // Send message with improved error handling
    const handleSend = async () => {
        if (!input.trim() || !currentId) return;

        const tempId = Date.now();
        const userMessage = {
            id: tempId,
            content: input,
            sender: userId,
            is_bot: false,
            model: selectedModel,
            mode: chatMode,
            pending: true
        };

        setMessages(m => [...m, userMessage]);
        setInput('');

        try {
            const response = await fetchWithAuth(`${API_BASE}/conversations/${currentId}/messages/`, {
                method: 'POST',
                body: JSON.stringify({
                    content: userMessage.content,
                    model: selectedModel,
                    mode: chatMode
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to send message');
            }

            const botMsg = await response.json();
            setMessages(m => m.map(msg => msg.id === tempId ? {...msg, pending: false} : msg));
            setMessages(m => [...m, botMsg]);
        } catch (e) {
            const errorMessage = e.message.includes('budget')
                ? 'API budget exceeded. Please try again later or contact support.'
                : e.message.includes('network')
                    ? 'Network error. Please check your connection.'
                    : 'Failed to get response. Please try again.';

            setError(errorMessage);
            // Remove pending state from user message
            setMessages(m => m.map(msg => msg.id === tempId ? {...msg, pending: false, error: true} : msg));
        }
    };

    // Pre-warm microphone on component mount for instant recording
    useEffect(() => {
        if (authenticated && sttSupported) {
            const initializeMicrophone = async () => {
                try {
                    // Pre-request microphone access and keep stream ready
                    const stream = await navigator.mediaDevices.getUserMedia({
                        audio: {
                            sampleRate: 48000,
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true,
                            latency: 0.01,
                            volume: 1.0
                        }
                    });
                    mediaStreamRef.current = stream;
                    console.log('Microphone pre-warmed and ready for instant recording');
                } catch (error) {
                    console.log('Microphone pre-warm failed (user may not have granted permission yet):', error);
                }
            };

            initializeMicrophone();
        }

        // Cleanup on unmount
        return () => {
            if (mediaStreamRef.current) {
                mediaStreamRef.current.getTracks().forEach(track => track.stop());
            }
        };
    }, [authenticated, sttSupported]);

    // Instant Recording Speech-to-Text with pre-warmed microphone
    const handleSTT = async () => {
        if (!sttSupported) {
            setError('Speech Recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
            return;
        }

        if (sttActive) {
            // Stop recording
            if (recognitionRef.current && recognitionRef.current.state === 'recording') {
                recognitionRef.current.stop();
            }
            setSttActive(false);
            isRecordingRef.current = false;
            return;
        }

        try {
            let stream = mediaStreamRef.current;

            // If no pre-warmed stream, create one now
            if (!stream || !stream.active) {
                stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        sampleRate: 48000,
                        channelCount: 1,
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true,
                        latency: 0.01,
                        volume: 1.0
                    }
                });
                mediaStreamRef.current = stream;
            }

            // Create MediaRecorder with proper format preferences
            let mediaRecorder;
            let mimeType = '';

            // Try formats in order of preference for Whisper API
            const formats = [
                'audio/webm;codecs=opus',
                'audio/mp4',
                'audio/webm',
                'audio/ogg;codecs=opus'
            ];

            for (const format of formats) {
                if (MediaRecorder.isTypeSupported(format)) {
                    mimeType = format;
                    break;
                }
            }

            if (!mimeType) {
                mediaRecorder = new MediaRecorder(stream);
                mimeType = mediaRecorder.mimeType;
            } else {
                mediaRecorder = new MediaRecorder(stream, {
                    mimeType,
                    audioBitsPerSecond: 128000
                });
            }
            
            const audioChunks = [];
            let recordingStartTime = Date.now();
            console.log('Starting INSTANT recording with pre-warmed mic, MIME type:', mimeType);

            // Set recording state BEFORE starting
            setSttActive(true);
            isRecordingRef.current = true;
            recognitionRef.current = mediaRecorder;

            // Start recording INSTANTLY with pre-warmed microphone
            mediaRecorder.start(10); // Ultra-frequent collection (10ms) for maximum responsiveness

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && isRecordingRef.current) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const totalDuration = Date.now() - recordingStartTime;

                try {
                    // Check minimum recording duration
                    if (totalDuration < 300 || audioChunks.length === 0) {
                        setError('Recording too short. Please hold the button longer and speak clearly.');
                        setSttActive(false);
                        return;
                    }

                    // Create blob with the detected MIME type
                    const audioBlob = new Blob(audioChunks, { type: mimeType });

                    console.log('Audio blob created:', {
                        size: audioBlob.size,
                        type: audioBlob.type,
                        duration: totalDuration,
                        chunks: audioChunks.length
                    });

                    // Check blob size
                    if (audioBlob.size < 1500) {
                        setError('Recording failed or too short. Please try again and speak louder.');
                        setSttActive(false);
                        return;
                    }

                    // Convert to base64 for API transmission
                    const reader = new FileReader();
                    reader.onload = async () => {
                        try {
                            const base64Audio = reader.result.split(',')[1];
                            
                            // DEBUG: Save audio file for inspection
                            const debugAudioUrl = URL.createObjectURL(audioBlob);
                            const debugLink = document.createElement('a');
                            debugLink.href = debugAudioUrl;
                            debugLink.download = `debug_audio_${Date.now()}.webm`;
                            debugLink.style.display = 'none';
                            document.body.appendChild(debugLink);
                            debugLink.click();
                            document.body.removeChild(debugLink);
                            console.log('Debug: Audio file saved for inspection');

                            const response = await fetchWithAuth(`${API_BASE}/transcribe/`, {
                                method: 'POST',
                                body: JSON.stringify({
                                    audio: base64Audio,
                                    model: 'gpt-4o-mini-transcribe',
                                    format: mimeType
                                })
                            });

                            if (!response.ok) {
                                const errorData = await response.json();
                                throw new Error(errorData.detail || 'Failed to transcribe audio');
                            }

                            const data = await response.json();

                            // Add transcribed text to input field
                            if (data.text && data.text.trim()) {
                                const transcribedText = data.text.trim();
                                console.log('Transcription successful:', transcribedText);
                                setInput(prev => (prev + ' ' + transcribedText).trim());
                            } else {
                                setError('No speech detected. Please try speaking more clearly.');
                            }

                        } catch (error) {
                            console.error('Transcription error:', error);
                            setError(error.message || 'Failed to transcribe audio. Please try again.');
                        }
                    };

                    reader.onerror = () => {
                        setError('Failed to process audio data. Please try again.');
                    };

                    reader.readAsDataURL(audioBlob);

                } catch (error) {
                    console.error('Audio processing error:', error);
                    setError('Failed to process audio. Please try again.');
                } finally {
                    setSttActive(false);
                    isRecordingRef.current = false;
                    // Keep the stream alive for next recording
                }
            };

            mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                setError('Audio recording failed. Please try again.');
                setSttActive(false);
                isRecordingRef.current = false;
            };

            // Immediate start confirmation
            mediaRecorder.onstart = () => {
                console.log('Recording started INSTANTLY with pre-warmed microphone');
            };

        } catch (error) {
            setSttActive(false);
            isRecordingRef.current = false;
            console.error('Microphone access error:', error);

            if (error.name === 'NotAllowedError') {
                setError('Microphone access denied. Please allow microphone access and reload the page.');
            } else if (error.name === 'NotFoundError') {
                setError('No microphone found. Please connect a microphone and try again.');
            } else if (error.name === 'NotSupportedError') {
                setError('Audio recording not supported in this browser. Please use Chrome, Edge, or Safari.');
            } else {
                setError('Failed to start audio recording. Please check your microphone and try again.');
            }
        }
    };

    if (!authenticated) {
        if (showSignup) {
            return <SignUp onLogin={handleLogin}/>;
        }
        return <Login onLogin={handleLogin} onSwitchToSignup={() => setShowSignup(true)}/>;
    }

    return (
        <div className="container-fluid p-0 vh-100 d-flex flex-column">
            {error && <ErrorToast message={error} onClose={() => setError(null)}/>}

            {/* Fixed Header for Mobile */}
            <div className="header fixed-top">
                <button
                    className="menu-button d-flex align-items-center gap-2"
                    onClick={() => setShowSidebar(!showSidebar)}
                    aria-label="Open conversations"
                >
                    <i className="bi bi-chat-dots"></i>
                    <span className="d-none d-md-inline">Conversations</span>
                </button>

                <h5 className="mb-0 d-none d-md-block text-center flex-grow-1">AI Assistant</h5>

                {/* Desktop Controls */}
                <div className="header-controls flex-grow-1 d-none d-md-flex justify-content-center">
                    <div className="d-flex align-items-center gap-3">
                        <div className="d-flex align-items-center gap-2">
                            <label className="fw-semibold text-nowrap model-mode-label" htmlFor="modelSelect">
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

                        <div className="d-flex align-items-center gap-2">
                            <label className="fw-semibold text-nowrap model-mode-label" htmlFor="modeSelect">
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

                {/* Mobile Controls Dropdown */}
                <div className="mobile-header-controls d-md-none">
                    <div className="mobile-dropdown">
                        <button
                            className="btn btn-outline-light settings-button"
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowMobileMenu(!showMobileMenu);
                            }}
                            aria-label="Settings"
                        >
                            <i className="bi bi-gear"></i>
                        </button>
                        <div className={`mobile-dropdown-content ${showMobileMenu ? 'show' : ''}`}>
                            <div className="form-group">
                                <label htmlFor="mobileModelSelect" className="mobile-dropdown-label">Model</label>
                                <select
                                    id="mobileModelSelect"
                                    className="model-selector w-100"
                                    value={selectedModel}
                                    onChange={(e) => setSelectedModel(e.target.value)}
                                >
                                    {models.map(model => (
                                        <option key={model.value} value={model.value}>{model.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label htmlFor="mobileModeSelect" className="mobile-dropdown-label">Mode</label>
                                <select
                                    id="mobileModeSelect"
                                    className="mode-selector w-100"
                                    value={chatMode}
                                    onChange={(e) => setChatMode(e.target.value)}
                                >
                                    {chatModes.map(mode => (
                                        <option key={mode.value} value={mode.value}>{mode.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="d-flex gap-2">
                                <button
                                    className="btn btn-outline-light flex-grow-1"
                                    onClick={() => {
                                        setShowMobileMenu(false);
                                        setShowSidebar(false);
                                    }}
                                    aria-label="Close menu"
                                >
                                    <i className="bi bi-x"></i>
                                    <span className="ms-1">Close</span>
                                </button>
                                <button
                                    className="btn btn-outline-danger flex-grow-1"
                                    onClick={() => {
                                        setShowMobileMenu(false);
                                        handleLogout();
                                    }}
                                    aria-label="Logout"
                                >
                                    <i className="bi bi-box-arrow-right"></i>
                                    <span className="ms-1">Logout</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <button
                    className="btn btn-outline-light d-none d-md-flex align-items-center gap-2"
                    onClick={handleLogout}
                    aria-label="Logout"
                >
                    <i className="bi bi-box-arrow-right"></i>
                    <span className="d-none d-lg-inline">Logout</span>
                </button>
            </div>

            {/* Main content with top padding for fixed header */}
            <div className="flex-grow-1 d-flex overflow-hidden position-relative" style={{paddingTop: '70px'}}>
                {/* Enhanced Sidebar with overlay for mobile */}
                <div
                    className={`d-md-none position-fixed top-0 start-0 w-100 h-100 bg-dark ${showSidebar ? 'd-block' : 'd-none'}`}
                    style={{opacity: 0.5, zIndex: 1040}}
                    onClick={() => setShowSidebar(false)}
                />

                <div
                    className={`sidebar ${showSidebar ? 'show' : ''}`}
                    style={{
                        width: '280px',
                        position: 'fixed',
                        top: 0,
                        bottom: 0,
                        left: 0,
                        zIndex: 1045,
                        transform: showSidebar ? 'translateX(0)' : 'translateX(-100%)',
                        transition: 'transform 0.3s ease-in-out',
                        overflowY: 'auto',
                        paddingTop: '70px'
                    }}
                >
                    <ChatSidebar
                        conversations={conversations}
                        currentId={currentId}
                        onSelect={(id) => {
                            setCurrentId(id);
                            setShowSidebar(false);
                        }}
                        onNewChat={() => {
                            handleNewChat();
                            setShowSidebar(false);
                        }}
                    />
                </div>

                {/* Chat area with improved layout */}
                <div className="flex-grow-1 d-flex flex-column">
                    <ChatWindow messages={messages} userId={userId} username={username}/>
                    <ChatInput
                        onSend={handleSend}
                        onSTT={handleSTT}
                        input={input}
                        setInput={setInput}
                        sttActive={sttActive}
                        sttSupported={sttSupported}
                    />
                </div>
            </div>
        </div>
    );
}

export default App;
