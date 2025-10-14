# Smart Task Scheduling System

A comprehensive AI-powered task scheduling system that integrates with CalBridge to intelligently break down tasks, allocate time slots, and create calendar events.

## Features

- **User Memory System**: Stores and manages user preferences and scheduling patterns
- **Smart Task Decomposition**: Uses Ollama LLM to break down complex tasks into manageable subtasks
- **Intelligent Time Allocation**: Allocates optimal time slots based on availability and user preferences
- **Calendar Integration**: Creates events in Apple Calendar via CalBridge API
- **SQL Database Storage**: Tracks tasks, subtasks, and scheduling history
- **Command Line Interface**: Easy-to-use CLI for all operations

## Prerequisites

1. **CalBridge Running**: The CalBridge helper app must be running on `http://127.0.0.1:8765`
2. **Ollama with llama3**: Ollama must be running with the `llama3` model available
3. **Calendar Cache**: Run `scripts/cache_calendars.py` to create the calendar cache
4. **Python 3.11+**: Compatible with the existing CalBridge setup

## Installation

1. Navigate to the smart_task_scheduling directory:
   ```bash
   cd smart_task_scheduling
   ```

2. Install dependencies (if needed):
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure CalBridge is running:
   ```bash
   # From the main project directory
   ./dist/CalBridge.app/Contents/MacOS/CalBridge
   ```

4. Ensure Ollama is running with llama3:
   ```bash
   ollama serve
   ollama pull llama3
   ```

## Quick Start

### 1. Schedule Your First Task

```bash
python -m smart_task_scheduling.cli schedule "Build a mobile app for tracking fitness goals" --deadline "2025-02-15"
```

### 2. List All Tasks

```bash
python -m smart_task_scheduling.cli list
```

### 3. View Task Details

```bash
python -m smart_task_scheduling.cli show 1
```

### 4. Update User Preferences

```bash
python -m smart_task_scheduling.cli preference update preferences.wake_up_time "07:00"
```

## Architecture

### Components

1. **UserMemory** (`user_memory.py`): Manages user preferences and scheduling patterns
2. **TaskDecomposer** (`task_decomposer.py`): Uses LLM to break down tasks and determine calendar assignment
3. **TimeAllotter** (`time_allotter.py`): Allocates time slots based on availability and preferences
4. **TaskScheduler** (`task_scheduler.py`): Manages SQL database and creates calendar events
5. **SmartScheduler** (`smart_scheduler.py`): Main orchestrator that combines all components
6. **CLI** (`cli.py`): Command-line interface for easy usage

### Database Schema

- **tasks**: Main task information
- **subtasks**: Individual subtasks with scheduling details
- **calendar_events**: Track created calendar events

## Usage Examples

### Basic Task Scheduling

```python
from smart_task_scheduling import SmartScheduler
from datetime import datetime, timedelta

scheduler = SmartScheduler()

# Schedule a task
result = scheduler.schedule_task(
    "Build a mobile app for tracking fitness goals",
    deadline=datetime.now() + timedelta(days=14)
)

if result['success']:
    print(f"Task {result['task_id']} scheduled successfully!")
    print(f"Created {len(result['created_events'])} calendar events")
```

### Custom User Preferences

```python
# Update wake-up time
scheduler.update_user_preference('preferences.wake_up_time', '07:00')

# Update work hours
scheduler.update_user_preference('preferences.work_hours.start', '09:00')
scheduler.update_user_preference('preferences.work_hours.end', '17:00')

# Add recurring events
scheduler.update_user_preference('recurring_events.gym', {
    'days': ['monday', 'wednesday', 'friday'],
    'time': '13:00-14:00',
    'calendar': 'Home'
})
```

### CLI Commands

```bash
# Schedule a task
python -m smart_task_scheduling.cli schedule "Research AI trends" --deadline "2025-01-20"

# List tasks with status filter
python -m smart_task_scheduling.cli list --status pending

# Show detailed task information
python -m smart_task_scheduling.cli show 1 --verbose

# Update preferences
python -m smart_task_scheduling.cli preference update preferences.sleep_time "22:00"

# Reschedule a task
python -m smart_task_scheduling.cli reschedule 1 --deadline "2025-01-25"

# Delete a task
python -m smart_task_scheduling.cli delete 1 --force
```

## Configuration

### Environment Variables

- `OLLAMA_BASE`: Ollama server URL (default: `http://127.0.0.1:11434`)
- `OLLAMA_MODEL`: Model to use (default: `llama3`)
- `CALBRIDGE_BASE`: CalBridge API URL (default: `http://127.0.0.1:8765`)

### User Memory Structure

The system stores user preferences in JSON format:

```json
{
  "preferences": {
    "wake_up_time": "06:00",
    "sleep_time": "23:00",
    "work_hours": {
      "start": "09:00",
      "end": "17:00"
    },
    "time_blocks": {
      "gym": "13:00-14:00",
      "uni_work": "early_morning",
      "side_projects": "late_evening"
    }
  },
  "recurring_events": {
    "weekly_capstone_meeting": {
      "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
      "time": "14:00-15:00",
      "calendar": "Work"
    }
  },
  "calendar_preferences": {
    "work_calendar": "Work",
    "personal_calendar": "Home"
  },
  "scheduling_rules": {
    "no_scheduling_before": "06:00",
    "no_scheduling_after": "23:00",
    "buffer_time_minutes": 15,
    "max_task_duration_hours": 4
  }
}
```

## Testing

Run the comprehensive test suite:

```bash
python -m smart_task_scheduling.test_components
```

The tests cover:
- User memory operations
- Task decomposition with mocked LLM responses
- Time allocation logic
- Database operations
- Integration workflows

## Integration with CalBridge

This system seamlessly integrates with the existing CalBridge setup:

1. **Calendar Access**: Uses CalBridge's HTTP API to read/write calendar events
2. **Holiday Exclusion**: Automatically excludes holiday events when finding free time
3. **Calendar Selection**: Supports Work/Home calendar assignment based on task type
4. **Event Creation**: Creates properly formatted calendar events with task metadata

## Troubleshooting

### Common Issues

1. **CalBridge not running**: Ensure CalBridge.app is running on port 8765
2. **Ollama connection failed**: Check that Ollama is running and llama3 model is available
3. **Calendar cache missing**: Run `scripts/cache_calendars.py` first
4. **Permission denied**: Ensure CalBridge has calendar permissions

### Debug Mode

Use the `--verbose` flag for detailed output:

```bash
python -m smart_task_scheduling.cli schedule "Test task" --verbose
```

### Logs

The system provides detailed logging for troubleshooting:
- Task decomposition results
- Time allocation decisions
- Calendar event creation status
- Database operations

## Future Enhancements

- **LangGraph Integration**: Multi-step LLM workflows for complex task decomposition
- **Learning System**: Adapt to user scheduling patterns over time
- **Conflict Resolution**: Smart handling of scheduling conflicts
- **Recurring Tasks**: Support for recurring task patterns
- **Team Scheduling**: Multi-user task coordination
- **Mobile Interface**: Mobile app for task management

## Contributing

This system is designed to be extensible. Key extension points:

1. **Custom LLM Models**: Modify `TaskDecomposer` to use different models
2. **Additional Constraints**: Extend `UserMemory` with new preference types
3. **Alternative Calendars**: Add support for Google Calendar, Outlook, etc.
4. **Advanced Scheduling**: Implement more sophisticated time allocation algorithms

## License

Part of the CalBridge project. See main project LICENSE for details.
