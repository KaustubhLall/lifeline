import React, {useState, useEffect} from 'react';
import '../styles/App.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import Login from '../components/Login';
import SignUp from '../components/SignUp';
import Header from '../components/Header';
import ErrorToast from '../components/ErrorToast';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import UserSettings from '../components/UserSettings';
import {useAuth} from '../hooks/useAuth';
import {useConversations} from '../hooks/useConversations';
import {useSpeechToText} from '../hooks/useSpeechToText';
import {useMobileLayout} from '../hooks/useMobileLayout';

function App() {
    const [showSignup, setShowSignup] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [input, setInput] = useState('');
    const [selectedModel, setSelectedModel] = useState('gpt-5-mini-2025-08-07');
    const [chatMode, setChatMode] = useState(localStorage.getItem('chatMode') || 'agent');
    const [temperature, setTemperature] = useState(0.2);

    // Persist chat mode selection
    useEffect(() => {
        localStorage.setItem('chatMode', chatMode);
    }, [chatMode]);

    // Authentication and user info
    const {authenticated, userId, username, handleLogin, handleLogout} = useAuth();

    // Responsive layout controls
    const {
        showSidebar,
        showMobileMenu,
        toggleSidebar,
        closeSidebar,
        toggleMobileMenu,
        resetLayout
    } = useMobileLayout();

    // Conversation and messaging logic
    const {
        conversations,
        currentId,
        setCurrentId,
        messages,
        error: conversationError,
        handleNewChat,
        sendMessage,
        clearError: clearConversationError,
        resetConversations
    } = useConversations(authenticated, handleLogout);

    // Speech-to-text functionality
    const {
        sttActive,
        sttSupported,
        error: sttError,
        handleSTT: originalHandleSTT,
        clearError: clearSTTError
    } = useSpeechToText(authenticated);

    // Available AI models and chat modes
    const models = [
        {value: 'gpt-5-mini-2025-08-07', label: 'GPT-5 Mini (2025-08-07)'},
        {value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano'},
        {value: 'gpt-4o', label: 'GPT-4o'},
        {value: 'gpt-4o-mini', label: 'GPT-4o Mini'},
        {value: 'gpt-4.1', label: 'GPT-4.1'}
    ];

    const chatModes = [
        {value: 'conversational', label: 'Conversational'},
        {value: 'coaching', label: 'Coaching'},
        {value: 'agent', label: 'Agent'}
    ];

    // Consolidate errors from hooks
    const error = conversationError || sttError;
    const clearError = () => {
        clearConversationError();
        clearSTTError();
    };

    // Logout and reset state
    const handleLogoutWithCleanup = () => {
        handleLogout();
        resetConversations();
        resetLayout();
        setShowSettings(false);
    };

    // Open/close settings modal
    const handleOpenSettings = () => {
        setShowSettings(true);
    };

    const handleCloseSettings = () => {
        setShowSettings(false);
    };

    // Append speech transcription to input
    const handleSTTWithInput = async () => {
        console.log('handleSTTWithInput called in App.js');
        try {
            const transcribedText = await originalHandleSTT();
            console.log('Transcribed text:', transcribedText);
            if (transcribedText) {
                setInput(prev => (prev + ' ' + transcribedText).trim());
            }
        } catch (error) {
            console.error('Error in handleSTTWithInput:', error);
        }
    };

    // Send message to the server
    const handleSend = async () => {
        if (!input.trim() || !currentId) {
            console.warn('handleSend: Missing input or conversation ID', {input: input.trim(), currentId});
            return;
        }

        console.log(`App.js: Sending message to conversation ${currentId}`);
        await sendMessage(input, selectedModel, chatMode, userId, temperature, currentId);
        setInput('');
    };

    // Select a conversation and close sidebar
    const handleConversationSelect = (id) => {
        setCurrentId(id);
        closeSidebar();
    };

    // Start a new conversation and close sidebar
    const handleNewChatWithCleanup = () => {
        handleNewChat();
        closeSidebar();
    };

    if (!authenticated) {
        // Show login or signup based on state
        if (showSignup) {
            return <SignUp onLogin={handleLogin}/>;
        }
        return <Login onLogin={handleLogin} onSwitchToSignup={() => setShowSignup(true)}/>;
    }

    return (
        <div className="app-container">
            {/* Display error messages */}
            {error && <ErrorToast message={error} onClose={clearError}/>}

            {/* User Settings Modal */}
            {showSettings && (
                <div className="settings-overlay" onClick={handleCloseSettings}>
                    <UserSettings
                        onClose={handleCloseSettings}
                        username={username}
                        userId={userId}
                    />
                </div>
            )}

            {/* Application header with controls */}
            <Header
                onToggleSidebar={toggleSidebar}
                selectedModel={selectedModel}
                setSelectedModel={setSelectedModel}
                chatMode={chatMode}
                setChatMode={setChatMode}
                showMobileMenu={showMobileMenu}
                setShowMobileMenu={toggleMobileMenu}
                onLogout={handleLogoutWithCleanup}
                onOpenSettings={handleOpenSettings}
                models={models}
                chatModes={chatModes}
            />

            <div className="main-content">
                {/* Mobile overlay */}
                <div
                    className={`mobile-overlay ${showSidebar ? 'show' : ''}`}
                    onClick={closeSidebar}
                />

                {/* Sidebar */}
                <div className={`sidebar-container ${showSidebar ? 'show' : ''}`}>
                    <ChatSidebar
                        conversations={conversations}
                        currentId={currentId}
                        onSelect={handleConversationSelect}
                        onNewChat={handleNewChatWithCleanup}
                        onClose={closeSidebar}
                    />
                </div>

                {/* Chat area */}
                <div className="chat-area">
                    <ChatWindow messages={messages} username={username}/>
                    <ChatInput
                        onSend={handleSend}
                        onSTT={handleSTTWithInput}
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
