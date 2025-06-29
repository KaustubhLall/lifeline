import React, {useEffect, useRef, useState} from 'react';
import '../styles/App.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import Login from '../components/Login';
import SignUp from '../components/SignUp';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import { fetchWithAuth, API_BASE } from '../utils/apiUtils';
import { isSTTSupported } from '../utils/speechUtils';

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
    const mediaStreamRef = useRef(null);
    const isRecordingRef = useRef(false);

    const models = [
        {value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano'},
        {value: 'gpt-4o', label: 'GPT-4o'},
        {value: 'gpt-4o-mini', label: 'GPT-4o Mini'},
        {value: 'gpt-4.1', label: 'GPT-4.1'}
    ];

    const chatModes = [
        {value: 'conversational', label: 'Conversational'},
        {value: 'coaching', label: 'Coaching'}
    ];

    const handleLogin = (userData) => {
        // Store auth data first
        localStorage.setItem('authToken', userData.token);
        localStorage.setItem('userId', userData.user_id.toString());
        localStorage.setItem('username', userData.username);

        // Update state
        setUserId(userData.user_id.toString());
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

            if (!response.ok) {
                const errorData = await response.text();
                console.error('Failed to create new chat:', errorData);
                setError('Failed to create new conversation');
                return;
            }
            const newConversation = await response.json();
            setConversations(prev => [...prev, newConversation]);
            setCurrentId(newConversation.id);
            setMessages([]);
        } catch (error) {
            setError('Failed to create new conversation');
            console.error('Error creating new chat:', error);
        }
    };

    // Fetch conversations
    useEffect(() => {
        if (!authenticated) return;

        console.log('Fetching conversations...');
        fetchWithAuth(`${API_BASE}/conversations/`)
            .then(r => {
                console.log('Conversations response:', r.status, r.ok);
                if (!r.ok) throw new Error(`Failed to fetch conversations: ${r.status}`);
                return r.json();
            })
            .then(data => {
                console.log('Conversations loaded:', data);
                setConversations(data);
            })
            .catch(e => {
                console.error('Conversations error:', e);
                if (e.message.includes('401') || e.message.includes('403')) {
                    console.log('Authentication failed, logging out...');
                    handleLogout();
                } else {
                    setError('Could not load conversations.');
                    console.error(e);
                }
            });
    }, [authenticated]);

    // Fetch messages for current conversation
    useEffect(() => {
        if (!authenticated || !currentId) {
            console.log('Skipping message fetch:', { authenticated, currentId });
            return;
        }

        console.log('Fetching messages for conversation:', currentId);
        fetchWithAuth(`${API_BASE}/conversations/${currentId}/messages/`)
            .then(r => {
                console.log('Messages response:', r.status, r.ok);
                if (!r.ok) throw new Error(`Failed to fetch messages: ${r.status}`);
                return r.json();
            })
            .then(data => {
                console.log('Messages loaded:', data);
                setMessages(data);
            })
            .catch(e => {
                console.error('Messages error:', e);
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

    // Mobile-friendly microphone initialization
    useEffect(() => {
        if (authenticated && sttSupported) {
            // Don't pre-warm on mobile to avoid permission issues
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

            if (!isMobile) {
                const initializeMicrophone = async () => {
                    try {
                        // Only pre-warm on desktop with basic constraints
                        const mediaStream = await navigator.mediaDevices.getUserMedia({
                            audio: {
                                echoCancellation: true,
                                noiseSuppression: true,
                                autoGainControl: true
                            }
                        });
                        mediaStreamRef.current = mediaStream;
                        console.log('Desktop microphone pre-warmed successfully');
                    } catch (error) {
                        console.log('Desktop microphone pre-warm failed (user may not have granted permission yet):', error);
                    }
                };
                // Explicitly handle the promise
                initializeMicrophone().catch(error => {
                    console.error('Failed to initialize microphone:', error);
                });
            } else {
                console.log('Mobile device detected - skipping microphone pre-warming to avoid permission issues');
            }
        }

        // Cleanup on unmount
        return () => {
            if (mediaStreamRef.current) {
                mediaStreamRef.current.getTracks().forEach(track => track.stop());
                mediaStreamRef.current = null;
            }
        };
    }, [authenticated, sttSupported]);

    // Mobile-optimized Speech-to-Text with better error handling
    const handleSTT = async () => {
        if (!sttSupported) {
            const isMobileSafari = /iPhone|iPad|iPod/.test(navigator.userAgent) && /Safari/.test(navigator.userAgent);
            const isLocalNetworkIP = window.location.hostname.startsWith('192.168.') ||
                                    window.location.hostname.startsWith('10.') ||
                                    window.location.hostname.startsWith('172.');
            const isHTTPS = window.location.protocol === 'https:';
            const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

            if (isMobileSafari && isLocalNetworkIP && !isHTTPS) {
                setError('🔒 Mobile Safari requires HTTPS for microphone access on local networks. Please:\n\n• Use HTTPS (set HTTPS=true when starting the dev server)\n• Or access via ngrok for a secure tunnel\n• Or test on desktop for development');
            } else if (!isHTTPS && !isLocalhost) {
                setError('Speech Recognition requires HTTPS. Please access the site via HTTPS or use localhost.');
            } else {
                setError('Speech Recognition not supported in this browser. Please use Chrome, Edge, or Safari.');
            }
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
            const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            let currentStream = mediaStreamRef.current;

            // Mobile-friendly audio constraints
            const audioConstraints = isMobile ? {
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                }
            } : {
                audio: {
                    sampleRate: 48000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    latency: 0.01,
                    volume: 1.0
                }
            };

            // Always request fresh stream on mobile, use cached on desktop
            if (!currentStream || !currentStream.active || isMobile) {
                console.log(`Requesting microphone access (${isMobile ? 'mobile' : 'desktop'} mode)`);
                currentStream = await navigator.mediaDevices.getUserMedia(audioConstraints);
                mediaStreamRef.current = currentStream;
            }

            // Mobile-compatible MediaRecorder setup
            let mediaRecorder;
            let mimeType = '';

            // Different format preferences for mobile vs desktop
            const formats = isMobile ? [
                'audio/webm',
                'audio/mp4',
                'audio/ogg',
                'audio/wav'
            ] : [
                'audio/webm;codecs=opus',
                'audio/mp4',
                'audio/webm',
                'audio/ogg;codecs=opus'
            ];

            for (const format of formats) {
                if (MediaRecorder.isTypeSupported(format)) {
                    mimeType = format;
                    console.log(`Selected audio format: ${format} (${isMobile ? 'mobile' : 'desktop'} mode)`);
                    break;
                }
            }

            if (!mimeType) {
                mediaRecorder = new MediaRecorder(currentStream);
                mimeType = mediaRecorder.mimeType;
                console.log(`Using browser default format: ${mimeType}`);
            } else {
                const recorderOptions = isMobile ?
                    { mimeType } : // Mobile: basic options only
                    { mimeType, audioBitsPerSecond: 128000 }; // Desktop: can handle bitrate setting

                mediaRecorder = new MediaRecorder(currentStream, recorderOptions);
            }
            
            const audioChunks = [];
            let recordingStartTime = Date.now();
            console.log(`Starting recording (${isMobile ? 'mobile' : 'desktop'} optimized), MIME type: ${mimeType}`);

            // Set recording state BEFORE starting
            setSttActive(true);
            isRecordingRef.current = true;
            recognitionRef.current = mediaRecorder;

            // Mobile-friendly data collection interval
            const dataInterval = isMobile ? 100 : 10; // Less frequent on mobile to reduce processing load
            mediaRecorder.start(dataInterval);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && isRecordingRef.current) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const totalDuration = Date.now() - recordingStartTime;

                try {
                    // More lenient minimum duration for mobile
                    const minDuration = isMobile ? 500 : 300;
                    if (totalDuration < minDuration || audioChunks.length === 0) {
                        setError(`Recording too short. Please hold the button for at least ${minDuration/1000} seconds and speak clearly.`);
                        setSttActive(false);
                        return;
                    }

                    // Create blob with the detected MIME type
                    const audioBlob = new Blob(audioChunks, { type: mimeType });

                    console.log('Audio blob created:', {
                        size: audioBlob.size,
                        type: audioBlob.type,
                        duration: totalDuration,
                        chunks: audioChunks.length,
                        platform: isMobile ? 'mobile' : 'desktop'
                    });

                    // More lenient minimum size for mobile recordings
                    const minSize = isMobile ? 1000 : 1500;
                    if (audioBlob.size < minSize) {
                        setError('Recording failed or too short. Please try again and speak louder.');
                        setSttActive(false);
                        return;
                    }

                    // Convert to base64 for API transmission
                    const reader = new FileReader();
                    reader.onload = async () => {
                        try {
                            const base64Audio = reader.result.split(',')[1];
                            
                            // Skip debug file download on mobile to avoid issues
                            if (!isMobile) {
                                const debugAudioUrl = URL.createObjectURL(audioBlob);
                                const debugLink = document.createElement('a');
                                debugLink.href = debugAudioUrl;
                                debugLink.download = `debug_audio_${Date.now()}.webm`;
                                debugLink.style.display = 'none';
                                document.body.appendChild(debugLink);
                                debugLink.click();
                                document.body.removeChild(debugLink);
                                console.log('Debug: Audio file saved for inspection');
                            }

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

                    // On mobile, close the stream after recording to free resources
                    if (isMobile && mediaStreamRef.current) {
                        mediaStreamRef.current.getTracks().forEach(track => track.stop());
                        mediaStreamRef.current = null;
                    }
                }
            };

            mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                setError('Audio recording failed. Please try again.');
                setSttActive(false);
                isRecordingRef.current = false;
            };

            mediaRecorder.onstart = () => {
                console.log('Recording started successfully');
            };

        } catch (error) {
            setSttActive(false);
            isRecordingRef.current = false;
            console.error('Microphone access error:', error);

            if (error.name === 'NotAllowedError') {
                setError('Microphone access denied. Please allow microphone access in your browser settings and reload the page.');
            } else if (error.name === 'NotFoundError') {
                setError('No microphone found. Please connect a microphone and try again.');
            } else if (error.name === 'NotSupportedError') {
                setError('Audio recording not supported in this browser. Please use Chrome, Edge, or Safari.');
            } else if (error.name === 'NotReadableError') {
                setError('Microphone is being used by another application. Please close other apps using the microphone.');
            } else {
                setError(`Failed to start audio recording: ${error.message}. Please check your microphone and try again.`);
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

            {/* Fixed Header */}
            <div className="header fixed-top">
                {/* Left Section */}
                <div className="header-left">
                    <button
                        className="menu-button d-flex align-items-center gap-2"
                        onClick={() => setShowSidebar(!showSidebar)}
                        aria-label="Open conversations"
                    >
                        <i className="bi bi-chat-dots"></i>
                        <span className="d-none d-md-inline">Conversations</span>
                    </button>
                </div>

                {/* Center Section (Desktop Only) */}
                <div className="header-center d-none d-md-flex align-items-center gap-3">
                    <h5 className="mb-0 text-white">AI Assistant</h5>
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

                {/* Right Section */}
                <div className="header-right d-flex align-items-center gap-2">
                    {/* Mobile Controls Dropdown */}
                    <div className="mobile-header-controls d-md-none">
                        <div className="mobile-dropdown">
                            <button
                                className="btn settings-button"
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

                    {/* Desktop Logout */}
                    <button
                        className="btn btn-outline-light d-none d-md-flex align-items-center gap-2"
                        onClick={handleLogout}
                        aria-label="Logout"
                    >
                        <i className="bi bi-box-arrow-right"></i>
                        <span className="d-none d-lg-inline">Logout</span>
                    </button>
                </div>
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
                        top: '70px', // Start directly below the header
                        bottom: 0,
                        left: 0,
                        zIndex: 1045,
                        transform: showSidebar ? 'translateX(0)' : 'translateX(-100%)',
                        transition: 'transform 0.3s ease-in-out',
                        overflowY: 'auto'
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
                    <ChatWindow messages={messages} username={username}/>
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
