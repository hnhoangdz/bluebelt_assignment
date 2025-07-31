import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Send, Plus, LogOut, User, Bot, Trash2, MessageSquare, Settings } from 'lucide-react';
import UserProfile from '../components/UserProfile';
import './ChatbotPage.css';

// Simplified error suppression - only suppress console errors, don't override chrome.runtime
(() => {
  const originalError = console.error;
  console.error = (...args) => {
    const message = args.join(' ');
    if (message.includes('Could not establish connection') || 
        message.includes('Receiving end does not exist') ||
        message.includes('Extension context invalidated') ||
        message.includes('runtime.lastError')) {
      return; // Suppress extension errors
    }
    originalError.apply(console, args);
  };
})();

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  created_at: string;
  sessionId: string;
}

const ChatbotPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [sessions, setSessions] = useState<any[]>([]); // Changed to any[] as SessionInfo is removed
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [currentSession, setCurrentSession] = useState<any | null>(null); // Changed to any
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [userStats, setUserStats] = useState<any | null>(null); // Changed to any
  const [showProfile, setShowProfile] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Simplified focus function - remove complex error handling that might interfere
  const focusInput = () => {
    try {
      if (inputRef.current && !inputRef.current.disabled) {
        inputRef.current.focus();
      }
    } catch (error) {
      // Silently handle any focus errors
    }
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Simplified error handling - don't prevent default or stop propagation
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      if (event.message?.includes('Could not establish connection') || 
          event.message?.includes('Receiving end does not exist') ||
          event.message?.includes('Extension context invalidated')) {
        // Just log suppression, don't prevent default
        console.log('Suppressed extension error:', event.message);
      }
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      if (event.reason?.message?.includes('Could not establish connection') ||
          event.reason?.message?.includes('Receiving end does not exist') ||
          event.reason?.message?.includes('Extension context invalidated')) {
        // Just log suppression, don't prevent default
        console.log('Suppressed extension rejection:', event.reason?.message);
      }
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);

  // Load sessions and conversations on component mount
  useEffect(() => {
    loadSessionsAndConversations();
    loadUserStats();
  }, []);

  // Disable automatic session creation to prevent interference with conversation history
  // Users can manually create new sessions by clicking "New Chat" button

  const loadSessionsAndConversations = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      };

      // Load sessions
      const sessionsResponse = await fetch('/api/chat/sessions', { headers });
      if (!sessionsResponse.ok) {
        if (sessionsResponse.status === 401) {
          // Token expired, redirect to login
          localStorage.removeItem('token');
          window.location.reload();
          return;
        }
        throw new Error(`Failed to load sessions: ${sessionsResponse.status}`);
      }
      const sessionsData = await sessionsResponse.json();
      setSessions(sessionsData);

      // Load conversations for each session
      const conversationsData: Conversation[] = [];
      for (const session of sessionsData) {
        try {
          const history = await fetch(`/api/chat/history/${session.id}`, { headers }).then(res => res.json());
          
          // Always create a conversation entry, even if empty
          const messages: Message[] = [];
          let title = 'New Chat';
          
          if (history.conversations.length > 0) {
            // Convert conversation items to messages
            history.conversations.forEach((conv: any) => { // Changed to any
              messages.push({
                id: `${conv.id}-user`,
                role: 'user',
                content: conv.message,
                timestamp: conv.timestamp
              });
              messages.push({
                id: `${conv.id}-assistant`,
                role: 'assistant',
                content: conv.response,
                timestamp: conv.timestamp
              });
            });

            title = history.conversations[0]?.message.slice(0, 50) + '...' || 'New Chat';
          }

          conversationsData.push({
            id: session.id,
            title,
            messages,
            created_at: session.created_at,
            sessionId: session.id
          });
        } catch (error) {
          console.error(`Failed to load conversations for session ${session.id}:`, error);
          // Even if loading fails, add an empty conversation for the session
          conversationsData.push({
            id: session.id,
            title: 'New Chat',
            messages: [],
            created_at: session.created_at,
            sessionId: session.id
          });
        }
      }

      // Sort conversations: ones with messages first, then by creation time (newest first)
      conversationsData.sort((a, b) => {
        // Prioritize conversations with messages
        if (a.messages.length > 0 && b.messages.length === 0) return -1;
        if (a.messages.length === 0 && b.messages.length > 0) return 1;
        
        // Then sort by creation time (newest first)
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });

      setConversations(conversationsData);

      // Auto-select the first conversation with messages after loading
      if (!currentSession && conversationsData.length > 0) {
        const firstConversationWithMessages = conversationsData.find(conv => conv.messages.length > 0);
        if (firstConversationWithMessages) {
          console.log('Auto-selecting conversation with messages:', firstConversationWithMessages.title);
          selectConversation(firstConversationWithMessages);
        } else if (conversationsData.length > 0) {
          // Select the first conversation even if it has no messages
          console.log('Auto-selecting first conversation:', conversationsData[0].title);
          selectConversation(conversationsData[0]);
        }
      }
    } catch (error) {
      console.error('Failed to load sessions and conversations:', error);
    } finally {
      // Data loading completed
    }
  };

  const loadUserStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      };
      const stats = await fetch('/api/user/stats', { headers }).then(res => res.json());
      setUserStats(stats);
    } catch (error) {
      console.error('Failed to load user stats:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      };

      // Create new session
      const newSession = await fetch('/api/chat/session', { method: 'POST', headers }).then(res => res.json());
      setCurrentSession(newSession);
      // apiService.setSessionId(newSession.id); // Removed

      const newConversation: Conversation = {
        id: newSession.id,
        title: 'New Chat',
        messages: [],
        created_at: newSession.created_at,
        sessionId: newSession.id
      };

      setConversations([newConversation, ...conversations]);
      setCurrentConversation(newConversation);
      setMessages([]);

      // Focus input after creating new conversation
      setTimeout(focusInput, 100);
    } catch (error) {
      console.error('Failed to create new conversation:', error);
    }
  };

  const selectConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation);
    setCurrentSession(sessions.find(s => s.id === conversation.sessionId) || null);
    setMessages(conversation.messages);
    // apiService.setSessionId(conversation.sessionId); // Removed
    
    // Focus input after selecting conversation
    setTimeout(focusInput, 100);
  };

  const deleteConversation = async (conversationId: string) => {
    try {
      const token = localStorage.getItem('token');
      const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      };
      await fetch(`/api/chat/session/${conversationId}`, { method: 'DELETE', headers });
      setConversations(conversations.filter(c => c.id !== conversationId));
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setCurrentSession(null);
        setMessages([]);
        // apiService.clearSessionId(); // Removed
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || loading || !currentSession || !user) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputMessage('');
    setLoading(true);

    // Restore focus to input after clearing message
    setTimeout(focusInput, 0);

    try {
      const token = localStorage.getItem('token');
      const chatData = {
        user_id: user!.id,
        session_id: currentSession!.id,
        query: inputMessage
      };

      // Add timeout to prevent hanging requests
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

      const fetchResponse = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify(chatData),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!fetchResponse.ok) {
        throw {
          status: fetchResponse.status,
          message: `HTTP error! status: ${fetchResponse.status}`
        };
      }

      const response: any = await fetchResponse.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      };

      const finalMessages = [...updatedMessages, assistantMessage];
      setMessages(finalMessages);

      // Update conversation
      if (currentConversation) {
        const updatedConversation = {
          ...currentConversation,
          messages: finalMessages,
          title: finalMessages.length === 2 ? inputMessage.slice(0, 50) + '...' : currentConversation.title
        };
        setCurrentConversation(updatedConversation);
        setConversations(conversations.map(c => 
          c.id === currentConversation.id ? updatedConversation : c
        ));
      }

      // Reload user stats after sending message
      loadUserStats();

      // Restore focus to input after successful message
      setTimeout(focusInput, 100);
    } catch (error: any) {
      console.error('Failed to send message:', error);
      
      // Check if it's a timeout/abort error
      if (error.name === 'AbortError') {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Request timed out. Please try again.',
          timestamp: new Date().toISOString()
        };
        setMessages([...updatedMessages, errorMessage]);
      }
      // Check if it's an authentication error
      else if (error.status === 401 || (error.response && error.response.status === 401)) {
        // Token expired, try to refresh or logout
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Your session has expired. Please refresh the page and log in again.',
          timestamp: new Date().toISOString()
        };
        setMessages([...updatedMessages, errorMessage]);
        
        // Clear token and redirect to login after a delay
        setTimeout(() => {
          localStorage.removeItem('token');
          window.location.reload();
        }, 3000);
      } else {
        // Add generic error message
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date().toISOString()
        };
        setMessages([...updatedMessages, errorMessage]);
      }
    } finally {
      setLoading(false);
      
      // Always restore focus to input when loading completes
      setTimeout(focusInput, 150);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleLogout = () => {
    logout();
  };

  return (
    <div className="chatbot-container">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <button className="new-chat-btn" onClick={createNewConversation}>
            <Plus size={20} />
            New Chat
          </button>
        </div>

        <div className="conversations-list">
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`conversation-item ${currentConversation?.id === conversation.id ? 'active' : ''}`}
              onClick={() => selectConversation(conversation)}
            >
              <MessageSquare size={16} />
              <span className="conversation-title">{conversation.title}</span>
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conversation.id);
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="user-info">
            <User size={16} />
            <span>{user?.username}</span>
          </div>
          {userStats && (
            <div className="user-stats">
              <div className="stat-item">
                <span className="stat-label">Chats:</span>
                <span className="stat-value">{userStats.total_conversations}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Tokens:</span>
                <span className="stat-value">{userStats.total_tokens}</span>
              </div>
            </div>
          )}
          <div className="user-actions">
            <button className="profile-btn" onClick={() => setShowProfile(true)}>
              <Settings size={16} />
              Profile
            </button>
            <button className="logout-btn" onClick={handleLogout}>
              <LogOut size={16} />
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        <div className="chat-header">
          <button
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <MessageSquare size={20} />
          </button>
          <h1>Dextrends AI Chat</h1>
          {currentSession && (
            <div className="session-info">
              <span className="session-id">Session: {currentSession.id.slice(0, 8)}...</span>
            </div>
          )}
        </div>

        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="empty-state">
              <Bot size={48} />
              <h2>Welcome to Dextrends AI</h2>
              <p>Start a conversation by typing a message below</p>
              {userStats && (
                <div className="welcome-stats">
                  <p>You've had {userStats.total_conversations} conversations using {userStats.total_tokens} tokens</p>
                </div>
              )}
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`message ${message.role === 'user' ? 'user' : 'assistant'}`}
              >
                <div className="message-avatar">
                  {message.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                </div>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                  <div className="message-timestamp">
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="message assistant">
              <div className="message-avatar">
                <Bot size={20} />
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <div className="dot"></div>
                  <div className="dot"></div>
                  <div className="dot"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              onClick={focusInput}
              onFocus={(e) => {
                // Ensure proper focus behavior
                e.target.focus();
              }}
              placeholder={
                loading ? "AI is thinking..." 
                : !currentSession ? "Select or create a conversation to start chatting"
                : !user ? "Please log in to chat"
                : "Type your message here..."
              }
              disabled={loading || !currentSession || !user}
              rows={3}
              style={{
                minHeight: '80px',
                maxHeight: '200px',
                resize: 'none',
                cursor: 'text'
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                // Simple auto-resize without complex cursor management
                target.style.height = 'auto';
                target.style.height = Math.min(Math.max(target.scrollHeight, 80), 200) + 'px';
              }}
            />
            <button
              className="send-btn"
              onClick={sendMessage}
              disabled={!inputMessage.trim() || loading || !currentSession || !user}
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* User Profile Modal */}
      {showProfile && user && (
        <UserProfile user={user} onClose={() => setShowProfile(false)} />
      )}
    </div>
  );
};

export default ChatbotPage; 