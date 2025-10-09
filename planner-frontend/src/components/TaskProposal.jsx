import React, { useState, useEffect } from 'react';
import { Calendar, Clock, Edit3, CheckCircle, XCircle, Play } from 'lucide-react';
import './TaskProposal.css';

const TaskProposal = ({ taskId, onSchedule }) => {
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editedSubtasks, setEditedSubtasks] = useState([]);

  useEffect(() => {
    loadTask();
  }, [taskId]);

  const loadTask = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/tasks/${taskId}`);
      if (response.ok) {
        const data = await response.json();
        setTask(data);
        setEditedSubtasks(data.subtasks || []);
      }
    } catch (error) {
      console.error('Failed to load task:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEditSubtask = (index, field, value) => {
    const updated = [...editedSubtasks];
    updated[index] = { ...updated[index], [field]: value };
    setEditedSubtasks(updated);
  };

  const handleSaveEdits = async () => {
    // TODO: Implement saving edited subtasks
    setEditing(false);
  };

  const handleCancelEdits = () => {
    setEditedSubtasks(task.subtasks || []);
    setEditing(false);
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

  const getTaskTypeLabel = (type) => {
    const labels = {
      'deep_work': 'Deep Work',
      'meeting': 'Meeting',
      'quick_task': 'Quick Task',
      'research': 'Research'
    };
    return labels[type] || type;
  };

  if (loading) {
    return (
      <div className="task-proposal">
        <div className="loading">Loading task details...</div>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="task-proposal">
        <div className="error">Failed to load task details</div>
      </div>
    );
  }

  return (
    <div className="task-proposal">
      <div className="task-header">
        <div className="task-title">
          <h3>{task.title}</h3>
          <div className="task-meta">
            <span className="task-type" style={{ color: getTaskTypeColor(task.task_type) }}>
              {getTaskTypeLabel(task.task_type)}
            </span>
            {task.deadline && (
              <span className="deadline">
                <Clock size={14} />
                Due: {new Date(task.deadline).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <div className="task-actions">
          {editing ? (
            <>
              <button 
                className="action-button save"
                onClick={handleSaveEdits}
              >
                <CheckCircle size={16} />
                Save
              </button>
              <button 
                className="action-button cancel"
                onClick={handleCancelEdits}
              >
                <XCircle size={16} />
                Cancel
              </button>
            </>
          ) : (
            <>
              <button 
                className="action-button edit"
                onClick={() => setEditing(true)}
              >
                <Edit3 size={16} />
                Edit
              </button>
              <button 
                className="action-button schedule"
                onClick={() => onSchedule(taskId)}
              >
                <Calendar size={16} />
                Schedule This
              </button>
            </>
          )}
        </div>
      </div>

      {task.description && (
        <div className="task-description">
          {task.description}
        </div>
      )}

      {task.needs_subtasks && editedSubtasks.length > 0 ? (
        <div className="subtasks-section">
          <h4>Subtasks ({editedSubtasks.length})</h4>
          <div className="subtasks-list">
            {editedSubtasks.map((subtask, index) => (
              <div key={subtask.id} className="subtask-item">
                <div className="subtask-order">
                  {subtask.order_index}
                </div>
                <div className="subtask-content">
                  {editing ? (
                    <input
                      type="text"
                      value={subtask.title}
                      onChange={(e) => handleEditSubtask(index, 'title', e.target.value)}
                      className="subtask-title-input"
                    />
                  ) : (
                    <div className="subtask-title">{subtask.title}</div>
                  )}
                  <div className="subtask-meta">
                    <span 
                      className="subtask-type"
                      style={{ color: getTaskTypeColor(subtask.task_type) }}
                    >
                      {getTaskTypeLabel(subtask.task_type)}
                    </span>
                    {editing ? (
                      <input
                        type="number"
                        value={subtask.estimated_minutes}
                        onChange={(e) => handleEditSubtask(index, 'estimated_minutes', parseInt(e.target.value))}
                        className="duration-input"
                        min="5"
                        step="5"
                      />
                    ) : (
                      <span className="subtask-duration">
                        <Clock size={12} />
                        {formatDuration(subtask.estimated_minutes)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="simple-task">
          <div className="simple-task-info">
            <Play size={16} />
            <span>Simple task - {formatDuration(task.estimated_minutes || 30)}</span>
          </div>
        </div>
      )}

      <div className="task-summary">
        <div className="total-duration">
          <Clock size={16} />
          <span>
            Total: {formatDuration(
              task.needs_subtasks 
                ? editedSubtasks.reduce((sum, st) => sum + st.estimated_minutes, 0)
                : (task.estimated_minutes || 30)
            )}
          </span>
        </div>
        {task.calendar_target && (
          <div className="calendar-target">
            <Calendar size={16} />
            <span>{task.calendar_target} Calendar</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskProposal;
