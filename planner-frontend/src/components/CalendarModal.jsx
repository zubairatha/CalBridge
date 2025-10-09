import React, { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Plus, CheckCircle, Clock } from 'lucide-react';
import './CalendarModal.css';

const CalendarModal = ({ onClose }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('week'); // 'week' or 'month'

  useEffect(() => {
    loadTasks();
  }, [currentDate]);

  const loadTasks = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/tasks');
      if (response.ok) {
        const data = await response.json();
        setTasks(data);
      }
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const navigateDate = (direction) => {
    const newDate = new Date(currentDate);
    if (view === 'week') {
      newDate.setDate(newDate.getDate() + (direction * 7));
    } else {
      newDate.setMonth(newDate.getMonth() + direction);
    }
    setCurrentDate(newDate);
  };

  const getWeekDates = () => {
    const start = new Date(currentDate);
    const day = start.getDay();
    start.setDate(start.getDate() - day);
    
    const dates = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(start);
      date.setDate(start.getDate() + i);
      dates.push(date);
    }
    return dates;
  };

  const getMonthDates = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());
    
    const dates = [];
    const endDate = new Date(lastDay);
    endDate.setDate(endDate.getDate() + (6 - lastDay.getDay()));
    
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
      dates.push(new Date(d));
    }
    return dates;
  };

  const getTasksForDate = (date) => {
    return tasks.filter(task => {
      if (!task.subtasks || task.subtasks.length === 0) {
        return false; // Only show scheduled tasks
      }
      
      return task.subtasks.some(subtask => {
        if (!subtask.scheduled_start) return false;
        const taskDate = new Date(subtask.scheduled_start);
        return taskDate.toDateString() === date.toDateString();
      });
    });
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDuration = (minutes) => {
    if (minutes < 60) {
      return `${minutes}m`;
    } else {
      const hours = Math.floor(minutes / 60);
      const mins = minutes % 60;
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    }
  };

  const getTaskTypeColor = (type) => {
    const colors = {
      'deep_work': '#3b82f6',
      'meeting': '#10b981',
      'quick_task': '#f59e0b',
      'research': '#8b5cf6'
    };
    return colors[type] || '#64748b';
  };

  if (loading) {
    return (
      <div className="modal-overlay">
        <div className="modal-content">
          <div className="loading">Loading calendar...</div>
        </div>
      </div>
    );
  }

  const dates = view === 'week' ? getWeekDates() : getMonthDates();

  return (
    <div className="modal-overlay">
      <div className="modal-content calendar-modal">
        <div className="modal-header">
          <div className="header-left">
            <h2>Calendar</h2>
            <div className="view-toggle">
              <button 
                className={`toggle-button ${view === 'week' ? 'active' : ''}`}
                onClick={() => setView('week')}
              >
                Week
              </button>
              <button 
                className={`toggle-button ${view === 'month' ? 'active' : ''}`}
                onClick={() => setView('month')}
              >
                Month
              </button>
            </div>
          </div>
          
          <div className="header-center">
            <button 
              className="nav-button"
              onClick={() => navigateDate(-1)}
            >
              <ChevronLeft size={20} />
            </button>
            <h3>
              {view === 'week' 
                ? `${dates[0].toLocaleDateString([], { month: 'short', day: 'numeric' })} - ${dates[6].toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}`
                : currentDate.toLocaleDateString([], { month: 'long', year: 'numeric' })
              }
            </h3>
            <button 
              className="nav-button"
              onClick={() => navigateDate(1)}
            >
              <ChevronRight size={20} />
            </button>
          </div>
          
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="calendar-body">
          {view === 'week' ? (
            <div className="week-view">
              <div className="week-header">
                {dates.map((date, index) => (
                  <div key={index} className="day-header">
                    <div className="day-name">
                      {date.toLocaleDateString([], { weekday: 'short' })}
                    </div>
                    <div className={`day-number ${date.toDateString() === new Date().toDateString() ? 'today' : ''}`}>
                      {date.getDate()}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="week-grid">
                {dates.map((date, index) => {
                  const dayTasks = getTasksForDate(date);
                  return (
                    <div key={index} className="day-column">
                      <div className="day-content">
                        {dayTasks.map((task) => (
                          <div key={task.id} className="task-card">
                            <div className="task-title">{task.title}</div>
                            {task.subtasks.map((subtask) => (
                              subtask.scheduled_start && new Date(subtask.scheduled_start).toDateString() === date.toDateString() && (
                                <div 
                                  key={subtask.id} 
                                  className="subtask-item"
                                  style={{ borderLeftColor: getTaskTypeColor(subtask.task_type) }}
                                >
                                  <div className="subtask-time">
                                    {formatTime(subtask.scheduled_start)}
                                  </div>
                                  <div className="subtask-title">{subtask.title}</div>
                                  <div className="subtask-duration">
                                    {formatDuration(subtask.estimated_minutes)}
                                  </div>
                                </div>
                              )
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="month-view">
              <div className="month-header">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                  <div key={day} className="month-day-header">{day}</div>
                ))}
              </div>
              
              <div className="month-grid">
                {dates.map((date, index) => {
                  const dayTasks = getTasksForDate(date);
                  const isCurrentMonth = date.getMonth() === currentDate.getMonth();
                  const isToday = date.toDateString() === new Date().toDateString();
                  
                  return (
                    <div 
                      key={index} 
                      className={`month-day ${!isCurrentMonth ? 'other-month' : ''} ${isToday ? 'today' : ''}`}
                    >
                      <div className="day-number">{date.getDate()}</div>
                      <div className="day-tasks">
                        {dayTasks.slice(0, 3).map((task) => (
                          <div 
                            key={task.id} 
                            className="month-task"
                            style={{ backgroundColor: getTaskTypeColor(task.task_type) }}
                          >
                            {task.title}
                          </div>
                        ))}
                        {dayTasks.length > 3 && (
                          <div className="more-tasks">+{dayTasks.length - 3} more</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        <div className="calendar-footer">
          <div className="legend">
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#3b82f6' }}></div>
              <span>Deep Work</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#10b981' }}></div>
              <span>Meeting</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#f59e0b' }}></div>
              <span>Quick Task</span>
            </div>
            <div className="legend-item">
              <div className="legend-color" style={{ backgroundColor: '#8b5cf6' }}></div>
              <span>Research</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarModal;
