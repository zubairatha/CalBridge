import React, { useState, useEffect } from 'react';
import { X, Upload, Save, Download, User, Clock, Calendar } from 'lucide-react';
import './PersonaSettings.css';

const PersonaSettings = ({ onClose }) => {
  const [constraints, setConstraints] = useState({
    work_hours: {
      monday: ['09:00', '17:00'],
      tuesday: ['09:00', '17:00'],
      wednesday: ['09:00', '17:00'],
      thursday: ['09:00', '17:00'],
      friday: ['09:00', '17:00'],
      saturday: null,
      sunday: null
    },
    recurring_blocks: [],
    preferences: {
      deep_work_hours: ['09:00', '12:00'],
      meeting_hours: ['14:00', '17:00'],
      min_block_minutes: 30,
      buffer_minutes: 15
    }
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploadText, setUploadText] = useState('');
  const [activeTab, setActiveTab] = useState('work-hours');

  useEffect(() => {
    loadConstraints();
  }, []);

  const loadConstraints = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/persona');
      if (response.ok) {
        const data = await response.json();
        setConstraints(data);
      }
    } catch (error) {
      console.error('Failed to load constraints:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveConstraints = async () => {
    setSaving(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/persona', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(constraints)
      });
      
      if (response.ok) {
        alert('Settings saved successfully!');
      } else {
        throw new Error('Failed to save settings');
      }
    } catch (error) {
      console.error('Failed to save constraints:', error);
      alert('Failed to save settings. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleWorkHoursChange = (day, field, value) => {
    setConstraints(prev => ({
      ...prev,
      work_hours: {
        ...prev.work_hours,
        [day]: prev.work_hours[day] ? 
          [...prev.work_hours[day].slice(0, field), value, ...prev.work_hours[day].slice(field + 1)] :
          [value]
      }
    }));
  };

  const toggleWorkDay = (day) => {
    setConstraints(prev => ({
      ...prev,
      work_hours: {
        ...prev.work_hours,
        [day]: prev.work_hours[day] ? null : ['09:00', '17:00']
      }
    }));
  };

  const addRecurringBlock = () => {
    setConstraints(prev => ({
      ...prev,
      recurring_blocks: [
        ...prev.recurring_blocks,
        {
          title: '',
          days: [],
          time: ['09:00', '17:00']
        }
      ]
    }));
  };

  const updateRecurringBlock = (index, field, value) => {
    setConstraints(prev => ({
      ...prev,
      recurring_blocks: prev.recurring_blocks.map((block, i) => 
        i === index ? { ...block, [field]: value } : block
      )
    }));
  };

  const removeRecurringBlock = (index) => {
    setConstraints(prev => ({
      ...prev,
      recurring_blocks: prev.recurring_blocks.filter((_, i) => i !== index)
    }));
  };

  const handleTextUpload = async () => {
    if (!uploadText.trim()) return;
    
    try {
      // TODO: Implement text parsing
      alert('Text parsing not yet implemented. Please use the form below.');
    } catch (error) {
      console.error('Failed to parse text:', error);
      alert('Failed to parse text. Please try again.');
    }
  };

  const exportSettings = () => {
    const dataStr = JSON.stringify(constraints, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'persona-constraints.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  const importSettings = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target.result);
        setConstraints(imported);
        alert('Settings imported successfully!');
      } catch (error) {
        alert('Invalid JSON file. Please check the format.');
      }
    };
    reader.readAsText(file);
  };

  if (loading) {
    return (
      <div className="modal-overlay">
        <div className="modal-content">
          <div className="loading">Loading settings...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Persona Settings</h2>
          <button className="close-button" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div className="tabs">
            <button 
              className={`tab ${activeTab === 'work-hours' ? 'active' : ''}`}
              onClick={() => setActiveTab('work-hours')}
            >
              <Clock size={16} />
              Work Hours
            </button>
            <button 
              className={`tab ${activeTab === 'blocks' ? 'active' : ''}`}
              onClick={() => setActiveTab('blocks')}
            >
              <Calendar size={16} />
              Recurring Blocks
            </button>
            <button 
              className={`tab ${activeTab === 'preferences' ? 'active' : ''}`}
              onClick={() => setActiveTab('preferences')}
            >
              <User size={16} />
              Preferences
            </button>
            <button 
              className={`tab ${activeTab === 'import' ? 'active' : ''}`}
              onClick={() => setActiveTab('import')}
            >
              <Upload size={16} />
              Import/Export
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'work-hours' && (
              <div className="work-hours-section">
                <h3>Work Hours</h3>
                <p>Set your available work hours for each day of the week.</p>
                
                <div className="work-hours-grid">
                  {Object.entries(constraints.work_hours).map(([day, hours]) => (
                    <div key={day} className="work-day">
                      <div className="day-header">
                        <label className="day-checkbox">
                          <input
                            type="checkbox"
                            checked={hours !== null}
                            onChange={() => toggleWorkDay(day)}
                          />
                          <span className="day-name">{day.charAt(0).toUpperCase() + day.slice(1)}</span>
                        </label>
                      </div>
                      
                      {hours && (
                        <div className="time-inputs">
                          <input
                            type="time"
                            value={hours[0]}
                            onChange={(e) => handleWorkHoursChange(day, 0, e.target.value)}
                            className="time-input"
                          />
                          <span>to</span>
                          <input
                            type="time"
                            value={hours[1]}
                            onChange={(e) => handleWorkHoursChange(day, 1, e.target.value)}
                            className="time-input"
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'blocks' && (
              <div className="blocks-section">
                <div className="section-header">
                  <h3>Recurring Blocks</h3>
                  <button className="add-button" onClick={addRecurringBlock}>
                    Add Block
                  </button>
                </div>
                <p>Define recurring time blocks (gym, lunch, etc.) that should be avoided.</p>
                
                <div className="blocks-list">
                  {constraints.recurring_blocks.map((block, index) => (
                    <div key={index} className="block-item">
                      <div className="block-header">
                        <input
                          type="text"
                          value={block.title}
                          onChange={(e) => updateRecurringBlock(index, 'title', e.target.value)}
                          placeholder="Block title (e.g., Gym, Lunch)"
                          className="block-title-input"
                        />
                        <button 
                          className="remove-button"
                          onClick={() => removeRecurringBlock(index)}
                        >
                          Remove
                        </button>
                      </div>
                      
                      <div className="block-days">
                        {['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'].map(day => (
                          <label key={day} className="day-checkbox">
                            <input
                              type="checkbox"
                              checked={block.days.includes(day)}
                              onChange={(e) => {
                                const newDays = e.target.checked 
                                  ? [...block.days, day]
                                  : block.days.filter(d => d !== day);
                                updateRecurringBlock(index, 'days', newDays);
                              }}
                            />
                            <span>{day.charAt(0).toUpperCase() + day.slice(1, 3)}</span>
                          </label>
                        ))}
                      </div>
                      
                      <div className="block-time">
                        <input
                          type="time"
                          value={block.time[0]}
                          onChange={(e) => updateRecurringBlock(index, 'time', [e.target.value, block.time[1]])}
                          className="time-input"
                        />
                        <span>to</span>
                        <input
                          type="time"
                          value={block.time[1]}
                          onChange={(e) => updateRecurringBlock(index, 'time', [block.time[0], e.target.value])}
                          className="time-input"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'preferences' && (
              <div className="preferences-section">
                <h3>Preferences</h3>
                <p>Set your preferred times for different types of work.</p>
                
                <div className="preference-group">
                  <label>Deep Work Hours</label>
                  <div className="time-range">
                    <input
                      type="time"
                      value={constraints.preferences.deep_work_hours[0]}
                      onChange={(e) => setConstraints(prev => ({
                        ...prev,
                        preferences: {
                          ...prev.preferences,
                          deep_work_hours: [e.target.value, prev.preferences.deep_work_hours[1]]
                        }
                      }))}
                      className="time-input"
                    />
                    <span>to</span>
                    <input
                      type="time"
                      value={constraints.preferences.deep_work_hours[1]}
                      onChange={(e) => setConstraints(prev => ({
                        ...prev,
                        preferences: {
                          ...prev.preferences,
                          deep_work_hours: [prev.preferences.deep_work_hours[0], e.target.value]
                        }
                      }))}
                      className="time-input"
                    />
                  </div>
                </div>

                <div className="preference-group">
                  <label>Meeting Hours</label>
                  <div className="time-range">
                    <input
                      type="time"
                      value={constraints.preferences.meeting_hours[0]}
                      onChange={(e) => setConstraints(prev => ({
                        ...prev,
                        preferences: {
                          ...prev.preferences,
                          meeting_hours: [e.target.value, prev.preferences.meeting_hours[1]]
                        }
                      }))}
                      className="time-input"
                    />
                    <span>to</span>
                    <input
                      type="time"
                      value={constraints.preferences.meeting_hours[1]}
                      onChange={(e) => setConstraints(prev => ({
                        ...prev,
                        preferences: {
                          ...prev.preferences,
                          meeting_hours: [prev.preferences.meeting_hours[0], e.target.value]
                        }
                      }))}
                      className="time-input"
                    />
                  </div>
                </div>

                <div className="preference-group">
                  <label>Minimum Block Duration (minutes)</label>
                  <input
                    type="number"
                    value={constraints.preferences.min_block_minutes}
                    onChange={(e) => setConstraints(prev => ({
                      ...prev,
                      preferences: {
                        ...prev.preferences,
                        min_block_minutes: parseInt(e.target.value)
                      }
                    }))}
                    className="number-input"
                    min="5"
                    step="5"
                  />
                </div>

                <div className="preference-group">
                  <label>Buffer Time (minutes)</label>
                  <input
                    type="number"
                    value={constraints.preferences.buffer_minutes}
                    onChange={(e) => setConstraints(prev => ({
                      ...prev,
                      preferences: {
                        ...prev.preferences,
                        buffer_minutes: parseInt(e.target.value)
                      }
                    }))}
                    className="number-input"
                    min="0"
                    step="5"
                  />
                </div>
              </div>
            )}

            {activeTab === 'import' && (
              <div className="import-section">
                <h3>Import/Export Settings</h3>
                
                <div className="import-group">
                  <h4>Import from Text</h4>
                  <p>Paste text describing your schedule preferences:</p>
                  <textarea
                    value={uploadText}
                    onChange={(e) => setUploadText(e.target.value)}
                    placeholder="e.g., I work 9-5 Monday to Friday, go to gym Tuesday and Thursday 5-6pm, prefer deep work in the morning..."
                    className="text-input"
                    rows={4}
                  />
                  <button 
                    className="parse-button"
                    onClick={handleTextUpload}
                    disabled={!uploadText.trim()}
                  >
                    Parse Text
                  </button>
                </div>

                <div className="import-group">
                  <h4>Import from File</h4>
                  <input
                    type="file"
                    accept=".json"
                    onChange={importSettings}
                    className="file-input"
                  />
                </div>

                <div className="import-group">
                  <h4>Export Settings</h4>
                  <button className="export-button" onClick={exportSettings}>
                    <Download size={16} />
                    Download JSON
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button 
            className="save-button"
            onClick={saveConstraints}
            disabled={saving}
          >
            <Save size={16} />
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PersonaSettings;
