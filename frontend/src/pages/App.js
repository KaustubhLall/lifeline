import React, { useState, useEffect } from 'react';
import '../styles/App.css';
import 'bootstrap/dist/css/bootstrap.min.css';
import Login from '../components/Login';
import SignUp from '../components/SignUp';
import Header from '../components/Header';
import ErrorToast from '../components/ErrorToast';
import ChatSidebar from '../components/ChatSidebar';
import ChatWindow from '../components/ChatWindow';
import ChatInput from '../components/ChatInput';
import { useAuth } from '../hooks/useAuth';
import { useConversations } from '../hooks/useConversations';
import { useSpeechToText } from '../hooks/useSpeechToText';
import { useMobileLayout } from '../hooks/useMobileLayout';

function App() {
    const [showSignup, setShowSignup] = useState(false);
    const [input, setInput] = useState('');
    const [selectedModel, setSelectedModel] = useState('gpt-4.1-nano');
    const [chatMode, setChatMode] = useState('conversational');

    // Custom hooks
    const { authenticated, userId, username, handleLogin, handleLogout } = useAuth();
    const {
        showSidebar,
        showMobileMenu,
        toggleSidebar,
        closeSidebar,
        toggleMobileMenu,
        resetLayout
    } = useMobileLayout();

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

    const {
        sttActive,
        sttSupported,
        error: sttError,
        handleSTT: originalHandleSTT,
        clearError: clearSTTError
    } = useSpeechToText(authenticated);

    // Constants
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

    // Combined error handling
    const error = conversationError || sttError;
    const clearError = () => {
        clearConversationError();
        clearSTTError();
    };

    // Enhanced logout handler
    const handleLogoutWithCleanup = () => {
        handleLogout();
        resetConversations();
        resetLayout();
    };

    // Enhanced STT handler that adds transcribed text to input
    const handleSTTWithInput = async () => {
        const transcribedText = await originalHandleSTT();
        if (transcribedText) {
            setInput(prev => (prev + ' ' + transcribedText).trim());
        }
    };

    // Send message handler
    const handleSend = async () => {
        if (!input.trim() || !currentId) return;

        await sendMessage(input, selectedModel, chatMode, userId);
        setInput('');
    };

    // Handle conversation selection
    const handleConversationSelect = (id) => {
        setCurrentId(id);
        closeSidebar();
    };

    // Handle new chat
    const handleNewChatWithCleanup = () => {
        handleNewChat();
        closeSidebar();
    };

    if (!authenticated) {
        if (showSignup) {
            return <SignUp onLogin={handleLogin}/>;
        }
        return <Login onLogin={handleLogin} onSwitchToSignup={() => setShowSignup(true)}/>;
    }

    return (
        <div className="app-container">
            {error && <ErrorToast message={error} onClose={clearError}/>}

            <Header
                onToggleSidebar={toggleSidebar}
                selectedModel={selectedModel}
                setSelectedModel={setSelectedModel}
                chatMode={chatMode}
                setChatMode={setChatMode}
                showMobileMenu={showMobileMenu}
                setShowMobileMenu={toggleMobileMenu}
                onLogout={handleLogoutWithCleanup}
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
