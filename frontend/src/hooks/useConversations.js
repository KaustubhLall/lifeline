import {useCallback, useEffect, useState} from 'react';
import {API_BASE, fetchWithAuth} from '../utils/apiUtils';

export function useConversations(authenticated, onLogout) {
    const [conversations, setConversations] = useState([]);
    const [currentId, setCurrentId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [error, setError] = useState(null);

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
    const sendMessage = useCallback(async (content, selectedModel, chatMode, userId, temperature) => {
        if (!content.trim() || !currentId) return;

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
            const response = await fetchWithAuth(`${API_BASE}/conversations/${currentId}/messages/`, {
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
                return [...updatedMessages, botMessage];
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
    }, [currentId]);

    // Clear any existing error state
    const clearError = useCallback(() => setError(null), []);

    // Reset all conversation data
    const resetConversations = useCallback(() => {
        setConversations([]);
        setCurrentId(null);
        setMessages([]);
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
        resetConversations
    };
}
