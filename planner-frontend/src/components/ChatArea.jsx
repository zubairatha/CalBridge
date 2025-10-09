import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Calendar, Clock, CheckCircle } from 'lucide-react';
import MessageBubble from './MessageBubble';
import TaskProposal from './TaskProposal';
import ScheduleProposal from './ScheduleProposal';
import './ChatArea.css';

const ChatArea = ({ sessionId, onTaskCreated }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (sessionId) {
      loadSession();
    }
  }, [sessionId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSession = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/chat/sessions/${sessionId}`);
      if (response.ok) {
        const data = await response.json();
        setSession(data);
        setMessages(data.messages || []);
      }
    } catch (error) {
      console.error('Failed to load session:', error);
    }
  };

  const extractSchedulingInfo = (message) => {
    const lowerMessage = message.toLowerCase();
    
    // Parse date and time patterns
    let deadline = null;
    let calendar_target = null;
    
    // Check for "tomorrow" + time
    if (lowerMessage.includes('tomorrow')) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      
      // Extract time patterns
      const timeMatch = lowerMessage.match(/(\d{1,2}):?(\d{2})?\s*(am|pm)?/i);
      if (timeMatch) {
        let hours = parseInt(timeMatch[1]);
        const minutes = timeMatch[2] ? parseInt(timeMatch[2]) : 0;
        const ampm = timeMatch[3] ? timeMatch[3].toLowerCase() : '';
        
        // Convert to 24-hour format
        if (ampm === 'pm' && hours !== 12) {
          hours += 12;
        } else if (ampm === 'am' && hours === 12) {
          hours = 0;
        }
        
        tomorrow.setHours(hours, minutes, 0, 0);
        deadline = tomorrow.toISOString();
      }
    }
    
    // Check for specific dates + time
    const dateTimeMatch = lowerMessage.match(/(\d{1,2})\/(\d{1,2})\/(\d{2,4})\s+at\s+(\d{1,2}):?(\d{2})?\s*(am|pm)?/i);
    if (dateTimeMatch) {
      const month = parseInt(dateTimeMatch[1]);
      const day = parseInt(dateTimeMatch[2]);
      let year = parseInt(dateTimeMatch[3]);
      let hours = parseInt(dateTimeMatch[4]);
      const minutes = dateTimeMatch[5] ? parseInt(dateTimeMatch[5]) : 0;
      const ampm = dateTimeMatch[6] ? dateTimeMatch[6].toLowerCase() : '';
      
      // Handle 2-digit years
      if (year < 100) {
        year += 2000;
      }
      
      // Convert to 24-hour format
      if (ampm === 'pm' && hours !== 12) {
        hours += 12;
      } else if (ampm === 'am' && hours === 12) {
        hours = 0;
      }
      
      const date = new Date(year, month - 1, day, hours, minutes, 0, 0);
      deadline = date.toISOString();
    }
    
    // Determine calendar target based on content
    if (lowerMessage.includes('work') || lowerMessage.includes('meeting') || lowerMessage.includes('call')) {
      calendar_target = 'Work';
    } else if (lowerMessage.includes('home') || lowerMessage.includes('personal')) {
      calendar_target = 'Home';
    }
    
    return { deadline, calendar_target };
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || loading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      created_at: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setLoading(true);

    try {
      // Send user message to backend
      await fetch(`http://127.0.0.1:8000/api/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          role: 'user',
          content: userMessage.content
        })
      });

      // Extract scheduling information from the message
      const schedulingInfo = extractSchedulingInfo(userMessage.content);
      
      // Process the message and create task
      const taskResponse = await fetch('http://127.0.0.1:8000/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: userMessage.content,
          description: userMessage.content,
          deadline: schedulingInfo.deadline,
          calendar_target: schedulingInfo.calendar_target
        })
      });

      if (taskResponse.ok) {
        const task = await taskResponse.json();
        
        // Create AI response message
        const aiMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `I've analyzed your request: "${userMessage.content}"`,
          task_id: task.id,
          created_at: new Date().toISOString()
        };

        setMessages(prev => [...prev, aiMessage]);
        
        // Send AI message to backend
        await fetch(`http://127.0.0.1:8000/api/chat/sessions/${sessionId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            role: 'assistant',
            content: aiMessage.content,
            task_id: task.id
          })
        });

        onTaskCreated(task.id);
      } else {
        throw new Error('Failed to create task');
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        created_at: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleScheduleTask = async (taskId) => {
    try {
      // Generate schedule proposal
      const proposalResponse = await fetch(`http://127.0.0.1:8000/api/tasks/${taskId}/schedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (proposalResponse.ok) {
        const proposal = await proposalResponse.json();
        
        // Add schedule proposal message
        const scheduleMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Here\'s a proposed schedule for your task:',
          schedule_proposal: proposal,
          created_at: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, scheduleMessage]);
      }
    } catch (error) {
      console.error('Failed to generate schedule:', error);
    }
  };

  const handleCommitSchedule = async (taskId, proposal) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/tasks/${taskId}/commit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          proposal: proposal,
          approved: true
        })
      });

      if (response.ok) {
        const successMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: 'Great! I\'ve scheduled your task in your calendar. You can view it in the Calendar app or click the Calendar button above.',
          created_at: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, successMessage]);
      }
    } catch (error) {
      console.error('Failed to commit schedule:', error);
    }
  };

  const handleRejectSchedule = (proposal) => {
    const rejectMessage = {
      id: Date.now().toString(),
      role: 'assistant',
      content: 'Schedule proposal rejected. Would you like me to generate a different schedule or would you prefer to schedule this manually?',
      created_at: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, rejectMessage]);
  };

  return (
    <div className="chat-area">
      {/* Messages */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <Bot size={48} className="welcome-icon" />
            <h2>Welcome to Smart Planner</h2>
            <p>Tell me what you need to get done, and I'll help you break it down and schedule it!</p>
            <div className="example-prompts">
              <p>Try saying:</p>
              <ul>
                <li>"Finish project proposal by next Friday"</li>
                <li>"Call with dad for 30 minutes"</li>
                <li>"Plan vacation to Europe"</li>
              </ul>
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages.map((message) => (
              <div key={message.id} className="message-wrapper">
                <MessageBubble message={message} />
                {message.task_id && (
                  <TaskProposal 
                    taskId={message.task_id}
                    onSchedule={() => handleScheduleTask(message.task_id)}
                  />
                )}
                {message.schedule_proposal && (
                  <ScheduleProposal 
                    proposal={message.schedule_proposal}
                    onCommit={(proposal) => handleCommitSchedule(proposal.task_id, proposal)}
                    onReject={handleRejectSchedule}
                  />
                )}
              </div>
            ))}
            {loading && (
              <div className="message-wrapper">
                <div className="message assistant">
                  <div className="message-avatar">
                    <Bot size={20} />
                  </div>
                  <div className="message-content">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="input-container">
        <div className="input-wrapper">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="What do you need to get done?"
            className="message-input"
            rows={1}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim() || loading}
            className="send-button"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatArea;
