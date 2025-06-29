import React, { useState, useEffect, useRef } from 'react';
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

function ChatSidebar({ conversations, currentId, onSelect, onNewChat }) {
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

function ChatWindow({ messages, userId }) {
  const bottomRef = useRef(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  return (
    <div className="flex-grow-1 overflow-auto px-2 py-3" style={{background: '#f8f9fa', minHeight: 0}}>
      {messages.map(msg => (
        <div key={msg.id} className={`d-flex mb-2 ${msg.sender === userId ? 'justify-content-end' : 'justify-content-start'}`}>
          <div className={`p-2 rounded ${msg.sender === userId ? 'bg-primary text-white' : 'bg-light border'}`} style={{maxWidth: '75%'}}>
            {msg.content}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function isSTTSupported() {
  return (
    typeof window !== 'undefined' &&
    ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)
  );
}

function ChatInput({ onSend, onSTT, input, setInput, sttActive, sttSupported }) {
  return (
    <form className="d-flex gap-2 p-2 border-top bg-white" onSubmit={e => {e.preventDefault(); onSend();}}>
      <button
        type="button"
        className={`btn btn-outline-secondary${sttActive ? ' active' : ''}`}
        onClick={onSTT}
        title={sttSupported ? "Speech to Text" : "Speech Recognition not supported in this browser."}
        disabled={!sttSupported || sttActive}
      >
        <i className="bi bi-mic"></i>
      </button>
      <input
        className="form-control"
        type="text"
        placeholder="Type a message..."
        value={input}
        onChange={e => setInput(e.target.value)}
        autoFocus
      />
      <button className="btn btn-primary" type="submit" disabled={!input.trim()}>Send</button>
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
  const [userId, setUserId] = useState(1); // Dummy user id
  const [sttActive, setSttActive] = useState(false);
  const [error, setError] = useState(null);
  const sttSupported = isSTTSupported();

  const handleLogin = (token) => {
    setAuthenticated(true);
    setShowSignup(false); // Reset signup state
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setAuthenticated(false);
    setConversations([]);
    setCurrentId(null);
    setMessages([]);
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

  // Send message
  const handleSend = () => {
    if (!input.trim() || !currentId) return;
    const msg = { content: input, sender: userId, is_bot: false };
    setMessages(m => [...m, { ...msg, id: Date.now() }]); // Optimistic
    setInput('');

    fetchWithAuth(`${API_BASE}/conversations/${currentId}/messages/`, {
      method: 'POST',
      body: JSON.stringify(msg)
    })
      .then(r => {
        if (!r.ok) throw new Error('Failed to send message');
        return r.json();
      })
      .then(botMsg => setMessages(m => [...m, botMsg]))
      .catch(e => {
        setError('Failed to send message.');
        console.error(e);
      });
  };

  // Speech-to-Text
  const handleSTT = () => {
    if (!sttSupported) {
      setError('Speech Recognition not supported in this browser.');
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    setSttActive(true);
    recognition.onresult = event => {
      setInput(input + event.results[0][0].transcript);
      setSttActive(false);
    };
    recognition.onerror = (e) => {
      setSttActive(false);
      setError('Speech recognition error: ' + (e.error || 'Unknown error'));
    };
    recognition.onend = () => setSttActive(false);
    recognition.start();
  };

  // Create new conversation
  const handleNewChat = () => {
    fetchWithAuth(`${API_BASE}/conversations/`, {
      method: 'POST',
      body: JSON.stringify({
        title: `Chat ${conversations.length + 1}`
      })
    })
      .then(r => {
        if (!r.ok) throw new Error('Failed to create conversation');
        return r.json();
      })
      .then(newConv => {
        setConversations(prev => [...prev, newConv]);
        setCurrentId(newConv.id);
        setMessages([]); // Clear messages for new chat
      })
      .catch(e => {
        setError('Could not create new chat.');
        console.error(e);
      });
  };

  if (!authenticated) {
    if (showSignup) {
      return <SignUp onLogin={handleLogin} />;
    }
    return <Login onLogin={handleLogin} onSwitchToSignup={() => setShowSignup(true)} />;
  }

  return (
    <div className="container-fluid p-0" style={{height: '100vh', maxHeight: '100vh'}}>
      {error && (
        <div className="alert alert-danger m-2 p-2" role="alert">
          {error}
          <button type="button" className="btn-close float-end" aria-label="Close" onClick={() => setError(null)}></button>
        </div>
      )}
      <div className="row g-0 flex-nowrap" style={{height: '100vh'}}>
        {/* Sidebar: hidden on xs, visible on sm+ */}
        <nav className="col-12 col-sm-4 col-md-3 col-lg-2 border-end bg-white d-none d-sm-block" style={{minWidth: 0}}>
          <div className="d-flex flex-column" style={{height: '100vh'}}>
            <button
              className="btn btn-link text-danger text-decoration-none py-2 border-bottom"
              onClick={handleLogout}
            >
              Logout
            </button>
            <div className="flex-grow-1" style={{minHeight: 0}}>
              <ChatSidebar
                conversations={conversations}
                currentId={currentId}
                onSelect={setCurrentId}
                onNewChat={handleNewChat}
              />
            </div>
          </div>
        </nav>
        {/* Main chat area */}
        <main className="col-12 col-sm-8 col-md-9 col-lg-10 d-flex flex-column" style={{height: '100vh', minWidth: 0}}>
          {/* On mobile, show sidebar as dropdown and new chat button */}
          <div className="d-block d-sm-none border-bottom bg-white p-2">
            <div className="d-flex gap-2">
              <select
                className="form-select"
                value={currentId || ''}
                onChange={e => setCurrentId(Number(e.target.value))}
              >
                <option value="">Select a chat</option>
                {conversations.map(conv => (
                  <option key={conv.id} value={conv.id}>{conv.title || `Chat #${conv.id}`}</option>
                ))}
              </select>
              <button
                className="btn btn-primary"
                onClick={handleNewChat}
                style={{whiteSpace: 'nowrap'}}
              >
                New +
              </button>
            </div>
          </div>
          {!currentId && conversations.length === 0 ? (
            <div className="flex-grow-1 d-flex align-items-center justify-content-center text-muted">
              <div className="text-center">
                <h4>Welcome to Chat</h4>
                <p>Click "New Chat" to start a conversation</p>
                <button className="btn btn-primary" onClick={handleNewChat}>New Chat</button>
              </div>
            </div>
          ) : (
            <>
              <ChatWindow messages={messages} userId={userId} />
              <ChatInput onSend={handleSend} onSTT={handleSTT} input={input} setInput={setInput} sttActive={sttActive} sttSupported={sttSupported} />
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
