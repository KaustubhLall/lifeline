import {useCallback, useEffect, useRef, useState} from 'react';
import {API_BASE, fetchWithAuth} from '../utils/apiUtils';

export function useConversations(authenticated, onLogout) {
    const [conversations, setConversations] = useState([]);
    const [currentId, setCurrentId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [error, setError] = useState(null);

    // Auto-refresh state for detecting title changes
    const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false);
    const refreshTimeoutRef = useRef(null);
    const lastMessageCountRef = useRef(0);

    // Helper function to check if a conversation has a default title
    const isDefaultTitle = useCallback((title, conversationId) => {
        if (!title) return true;
        return title === 'New Chat' ||
            title.startsWith('Chat ') ||
            title === `Chat ${conversationId}`;
    }, []);

    // Helper function to refresh conversations list
    const refreshConversations = useCallback(async () => {
        if (!authenticated) return;

        try {
            const response = await fetchWithAuth(`${API_BASE}/conversations/`);
            if (!response.ok) throw new Error(`Failed to fetch conversations: ${response.status}`);
            const data = await response.json();

            setConversations(prevConversations => {
                // Check if any titles changed (for logging)
                const titleChanges = data.filter(newConv => {
                    const oldConv = prevConversations.find(old => old.id === newConv.id);
                    return oldConv && oldConv.title !== newConv.title;
                });

                if (titleChanges.length > 0) {
                    console.log('🏷️ Detected title changes:', titleChanges.map(c =>
                        `Conversation ${c.id}: "${c.title}"`
                    ));
                }

                return data;
            });
        } catch (e) {
            console.error('Auto-refresh conversations error:', e);
            if (e.message.includes('401') || e.message.includes('403')) {
                onLogout();
            }
        }
    }, [authenticated, onLogout]);

    // Load user conversations when authenticated
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
                    onLogout();
                } else {
                    setError('Could not load conversations.');
                }
            });
    }, [authenticated, onLogout]);

    // Auto-refresh effect for conversations with default titles
    useEffect(() => {
        if (!autoRefreshEnabled || !authenticated || !currentId) {
            return;
        }

        // Clear any existing timeout
        if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current);
        }

        // Find the current conversation
        const currentConversation = conversations.find(c => c.id === currentId);
        if (!currentConversation) return;

        // Check if current conversation has a default title and recent activity
        const hasDefaultTitle = isDefaultTitle(currentConversation.title, currentConversation.id);
        const hasEnoughMessages = messages.length >= 3; // Likely to trigger auto-titling

        if (hasDefaultTitle && hasEnoughMessages) {
            console.log(`🔄 Scheduling auto-refresh for conversation ${currentId} (default title: "${currentConversation.title}", ${messages.length} messages)`);

            // Schedule refresh after a delay to allow backend processing
            refreshTimeoutRef.current = setTimeout(() => {
                console.log('🔄 Auto-refreshing conversations for title updates...');
                refreshConversations();
            }, 3000); // 3 second delay to allow backend auto-titling to complete
        }

        return () => {
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current);
            }
        };
    }, [autoRefreshEnabled, authenticated, currentId, conversations, messages.length, isDefaultTitle, refreshConversations]);

    // Load messages whenever the active conversation changes
    useEffect(() => {
        if (!authenticated || !currentId) {
            console.log('Skipping message fetch:', {authenticated, currentId});
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

                // Update last message count for change detection
                lastMessageCountRef.current = data.length;
            })
            .catch(e => {
                console.error('Messages error:', e);
                setError('Could not load messages.');
            });
    }, [currentId, authenticated]);

    // Initialize active conversation to first in list
    useEffect(() => {
        if (conversations.length && !currentId) setCurrentId(conversations[0].id);
    }, [conversations, currentId]);

    // Create a new conversation and set it as active
    const handleNewChat = useCallback(async () => {
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
    }, []);

    // Send message optimistically; append bot response on success
    const sendMessage = useCallback(async (content, selectedModel, chatMode, userId, temperature, conversationId = null) => {
        // Use the passed conversationId or fall back to currentId
        const targetConversationId = conversationId || currentId;

        if (!content.trim() || !targetConversationId) {
            console.warn('sendMessage: Missing content or conversation ID', {
                content: content.trim(),
                targetConversationId,
                currentId
            });
            return;
        }

        console.log(`Sending message to conversation ${targetConversationId} (currentId: ${currentId})`);

        const tempId = Date.now();
        const userMessage = {
            id: tempId,
            content,
            sender: userId,
            is_bot: false,
            model: selectedModel,
            mode: chatMode,
            pending: true
        };

        setMessages(m => [...m, userMessage]);

        try {
            const response = await fetchWithAuth(`${API_BASE}/conversations/${targetConversationId}/messages/`, {
                method: 'POST',
                body: JSON.stringify({
                    content: userMessage.content,
                    model: selectedModel,
                    mode: chatMode,
                    temperature: temperature // Pass temperature to the backend
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to send message');
            }

            const data = await response.json();
            const finalUserMessage = data.user_message;
            const botMessage = data.bot_message;

            console.log('Final user message received:', finalUserMessage); // Debug log
            console.log('Bot message received:', botMessage); // Debug log

            // Replace optimistic message with final one from server and add bot message
            setMessages(prevMessages => {
                const updatedMessages = prevMessages.map(msg =>
                    msg.id === tempId ? finalUserMessage : msg
                );
                const newMessages = [...updatedMessages, botMessage];

                // Enable auto-refresh after sending a message to potentially trigger auto-titling
                const currentConversation = conversations.find(c => c.id === targetConversationId);
                if (currentConversation && isDefaultTitle(currentConversation.title, currentConversation.id)) {
                    console.log(`💬 Message sent to conversation with default title, enabling auto-refresh for potential title update`);
                    setAutoRefreshEnabled(true);

                    // Disable auto-refresh after a reasonable time to avoid infinite polling
                    setTimeout(() => {
                        setAutoRefreshEnabled(false);
                        console.log(`⏰ Auto-refresh timeout reached, disabling for conversation ${targetConversationId}`);
                    }, 15000); // 15 seconds should be enough for backend processing
                }

                return newMessages;
            });

        } catch (e) {
            const errorMessage = e.message.includes('budget')
                ? 'API budget exceeded. Please try again later or contact support.'
                : e.message.includes('network')
                    ? 'Network error. Please check your connection.'
                    : 'Failed to get response. Please try again.';

            setError(errorMessage);
            setMessages(m => m.map(msg => msg.id === tempId ? {...msg, pending: false, error: true} : msg));
        }
    }, [currentId, conversations, isDefaultTitle]);

    // Manual refresh function for external use
    const manualRefreshConversations = useCallback(() => {
        console.log('🔄 Manual refresh requested');
        refreshConversations();
    }, [refreshConversations]);

    // Clear any existing error state
    const clearError = useCallback(() => setError(null), []);

    // Reset all conversation data
    const resetConversations = useCallback(() => {
        setConversations([]);
        setCurrentId(null);
        setMessages([]);
        setAutoRefreshEnabled(false);
        if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current);
        }
    }, []);

    return {
        conversations,
        currentId,
        setCurrentId,
        messages,
        error,
        handleNewChat,
        sendMessage,
        clearError,
        resetConversations,
        refreshConversations: manualRefreshConversations,
        autoRefreshEnabled,
        isDefaultTitle: (title, id) => isDefaultTitle(title, id)
    };
}
