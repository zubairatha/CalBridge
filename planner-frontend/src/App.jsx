import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import ChatArea from './components/ChatArea';
import CalendarModal from './components/CalendarModal';
import PersonaSettings from './components/PersonaSettings';
import './App.css';

function App() {
  const [showCalendar, setShowCalendar] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Create or get default chat session
    const createDefaultSession = async () => {
      try {
        console.log('Creating default session...');
        const response = await fetch('http://127.0.0.1:8000/api/chat/sessions');
        console.log('Response status:', response.status);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const sessions = await response.json();
        console.log('Sessions:', sessions);
        
        if (sessions.length === 0) {
          // Create new session
          console.log('Creating new session...');
          const newSessionResponse = await fetch('http://127.0.0.1:8000/api/chat/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: 'New Chat' })
          });
          
          if (!newSessionResponse.ok) {
            throw new Error(`HTTP error! status: ${newSessionResponse.status}`);
          }
          
          const newSession = await newSessionResponse.json();
          console.log('New session created:', newSession);
          setCurrentSessionId(newSession.id);
        } else {
          setCurrentSessionId(sessions[0].id);
        }
      } catch (error) {
        console.error('Failed to initialize chat session:', error);
        setError(error.message);
      } finally {
        setLoading(false);
      }
    };

    createDefaultSession();
  }, []);

  const handleSessionSwitch = (sessionId) => {
    setCurrentSessionId(sessionId);
  };

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '18px'
      }}>
        Loading Smart Planner...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column',
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '18px',
        padding: '20px'
      }}>
        <h2>Error Loading App</h2>
        <p style={{ color: 'red' }}>{error}</p>
        <p>Make sure the backend is running on http://127.0.0.1:8000</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <Router>
      <div className="App">
        <AppLayout
          onCalendarClick={() => setShowCalendar(true)}
          onSettingsClick={() => setShowSettings(true)}
          onSyncClick={async () => {
            // TODO: Implement sync functionality
            console.log('Sync clicked');
          }}
          onSessionSwitch={handleSessionSwitch}
        >
          <Routes>
            <Route 
              path="/" 
              element={
                <ChatArea 
                  sessionId={currentSessionId}
                  onTaskCreated={(taskId) => {
                    console.log('Task created:', taskId);
                  }}
                />
              } 
            />
            <Route 
              path="/chat/:sessionId" 
              element={
                <ChatArea 
                  sessionId={currentSessionId}
                  onTaskCreated={(taskId) => {
                    console.log('Task created:', taskId);
                  }}
                />
              } 
            />
          </Routes>
        </AppLayout>

        {showCalendar && (
          <CalendarModal
            onClose={() => setShowCalendar(false)}
          />
        )}

        {showSettings && (
          <PersonaSettings
            onClose={() => setShowSettings(false)}
          />
        )}
      </div>
    </Router>
  );
}

export default App;