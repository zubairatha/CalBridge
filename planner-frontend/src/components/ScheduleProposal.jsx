import React from 'react';
import { Calendar, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import './ScheduleProposal.css';

const ScheduleProposal = ({ proposal, onCommit, onReject }) => {
  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString([], { 
      weekday: 'short',
      month: 'short', 
      day: 'numeric',
      hour: '2-digit', 
      minute: '2-digit' 
    });
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

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#10b981'; // green
    if (score >= 0.6) return '#f59e0b'; // yellow
    return '#ef4444'; // red
  };

  const getScoreLabel = (score) => {
    if (score >= 0.8) return 'Excellent';
    if (score >= 0.6) return 'Good';
    if (score >= 0.4) return 'Fair';
    return 'Poor';
  };

  return (
    <div className="schedule-proposal">
      <div className="proposal-header">
        <h3>📅 Schedule Proposal</h3>
        <div className="proposal-summary">
          <span className="total-time">
            <Clock size={16} />
            {formatDuration(proposal.total_estimated_minutes)}
          </span>
          <span className="slot-count">
            {proposal.time_slots.length} time slot{proposal.time_slots.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {proposal.conflicts.length > 0 && (
        <div className="conflicts-section">
          <div className="conflicts-header">
            <AlertCircle size={16} />
            <span>Conflicts & Issues</span>
          </div>
          <ul className="conflicts-list">
            {proposal.conflicts.map((conflict, index) => (
              <li key={index} className="conflict-item">
                {conflict}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="timeline-section">
        <h4>Proposed Schedule</h4>
        <div className="timeline">
          {proposal.time_slots.map((slot, index) => {
            const subtask = proposal.subtasks[index];
            return (
              <div key={index} className="timeline-item">
                <div className="timeline-marker">
                  <div className="marker-number">{index + 1}</div>
                </div>
                <div className="timeline-content">
                  <div className="slot-header">
                    <div className="slot-time">
                      <Calendar size={14} />
                      {formatTime(slot.start)}
                    </div>
                    <div 
                      className="slot-score"
                      style={{ color: getScoreColor(slot.score) }}
                    >
                      {getScoreLabel(slot.score)} ({Math.round(slot.score * 100)}%)
                    </div>
                  </div>
                  
                  {subtask && (
                    <div className="subtask-info">
                      <div className="subtask-title">{subtask.title}</div>
                      <div className="subtask-meta">
                        <span className="subtask-duration">
                          <Clock size={12} />
                          {formatDuration(subtask.estimated_minutes)}
                        </span>
                        <span className="subtask-type">{subtask.task_type}</span>
                      </div>
                    </div>
                  )}
                  
                  <div className="slot-reason">
                    {slot.reason}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="proposal-actions">
        <button 
          className="action-button approve"
          onClick={() => onCommit(proposal)}
          disabled={proposal.conflicts.length > 0}
        >
          <CheckCircle size={16} />
          Approve & Schedule
        </button>
        <button 
          className="action-button reject"
          onClick={() => onReject(proposal)}
        >
          <XCircle size={16} />
          Reject
        </button>
      </div>

      {proposal.conflicts.length > 0 && (
        <div className="conflict-warning">
          <AlertCircle size={16} />
          <span>Cannot schedule due to conflicts. Please resolve issues above.</span>
        </div>
      )}
    </div>
  );
};

export default ScheduleProposal;
