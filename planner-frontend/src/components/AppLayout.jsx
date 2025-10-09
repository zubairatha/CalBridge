import React from 'react';
import { Calendar, RefreshCw, Settings, MessageSquare } from 'lucide-react';
import Sidebar from './Sidebar';
import './AppLayout.css';

const AppLayout = ({ 
  children, 
  onCalendarClick, 
  onSyncClick, 
  onSettingsClick,
  onSessionSwitch
}) => {
  return (
    <div className="app-layout">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <MessageSquare className="logo-icon" />
          <h1>Smart Planner</h1>
        </div>
        <div className="header-right">
          <button 
            className="header-button"
            onClick={onCalendarClick}
            title="Open Calendar"
          >
            <Calendar size={20} />
          </button>
          <button 
            className="header-button"
            onClick={onSyncClick}
            title="Sync with Calendar"
          >
            <RefreshCw size={20} />
          </button>
          <button 
            className="header-button"
            onClick={onSettingsClick}
            title="Settings"
          >
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="app-main">
        {/* Sidebar */}
        <aside className="app-sidebar">
          <Sidebar onSessionSwitch={onSessionSwitch} />
        </aside>

        {/* Chat Area */}
        <main className="app-content">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
