import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare, Calendar, Clock, Trash2 } from 'lucide-react';
import './Sidebar.css';

const Sidebar = ({ onSessionSwitch }) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/sessions');
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error('Failed to load chat sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const createNewSession = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Chat' })
      });
      
      if (response.ok) {
        const newSession = await response.json();
        setSessions(prev => [newSession, ...prev]);
        // Switch to the new session
        onSessionSwitch(newSession.id);
      }
    } catch (error) {
      console.error('Failed to create new session:', error);
    }
  };

  const deleteSession = async (sessionId, event) => {
    event.stopPropagation(); // Prevent triggering the session click
    
    if (!confirm('Are you sure you want to delete this chat? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/chat/sessions/${sessionId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        setSessions(prev => prev.filter(session => session.id !== sessionId));
      } else {
        throw new Error('Failed to delete session');
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
      alert('Failed to delete chat. Please try again.');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 24) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffInHours < 168) { // 7 days
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  if (loading) {
    return (
      <div className="sidebar">
        <div className="sidebar-header">
          <h2>Chats</h2>
        </div>
        <div className="sidebar-content">
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Chats</h2>
        <button 
          className="new-chat-button"
          onClick={createNewSession}
          title="New Chat"
        >
          <Plus size={16} />
        </button>
      </div>
      
      <div className="sidebar-content">
        {sessions.length === 0 ? (
          <div className="empty-state">
            <MessageSquare size={48} className="empty-icon" />
            <p>No chats yet</p>
            <button 
              className="create-first-chat"
              onClick={createNewSession}
            >
              Start your first chat
            </button>
          </div>
        ) : (
          <div className="session-list">
            {sessions.map((session) => (
              <div 
                key={session.id} 
                className="session-item"
                onClick={() => {
                  onSessionSwitch(session.id);
                }}
              >
                <div className="session-icon">
                  <MessageSquare size={16} />
                </div>
                <div className="session-content">
                  <div className="session-title">
                    {session.title || 'Untitled Chat'}
                  </div>
                  <div className="session-meta">
                    <Clock size={12} />
                    <span>{formatDate(session.last_message_at)}</span>
                  </div>
                </div>
                <button 
                  className="delete-session-button"
                  onClick={(e) => deleteSession(session.id, e)}
                  title="Delete chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;
