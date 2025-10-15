# LLM Task Scheduling System

A smart task scheduling system that uses LLM (Large Language Model) to decompose tasks and automatically schedule them into calendar events with optimal time management.

## Features

- **Smart Task Decomposition**: Uses Ollama Llama3 to intelligently break down complex tasks into 2-5 subtasks
- **Automatic Time Allocation**: Allocates appropriate time for each subtask (max 3 hours per subtask)
- **Calendar Integration**: Seamlessly integrates with CalBridge API for calendar management
- **Intelligent Scheduling**: Uses advanced scheduling algorithms to find optimal time slots
- **Holiday Awareness**: Automatically excludes holidays from busy time calculations
- **Parent-Child Relationships**: Maintains proper relationships between main tasks and subtasks
- **Flexible Constraints**: Supports various scheduling constraints (max tasks per day, gaps, etc.)

## Architecture

The system consists of four main components:

### 1. LLM Decomposer (`llm_decomposer.py`)
- Uses Ollama Llama3 to analyze task descriptions
- Determines appropriate calendar (Work/Home)
- Breaks down complex tasks into manageable subtasks
- Allocates time for each subtask (5-180 minutes)

### 2. Time Allotment Agent (`time_allotment.py`)
- Fetches calendar events from CalBridge API
- Excludes holidays from busy time calculations
- Calculates free time slots until deadline
- Uses the task_scheduler module for optimal scheduling

### 3. Event Creator (`event_creator.py`)
- Generates unique event IDs
- Creates calendar events via CalBridge API
- Manages parent-child relationships for subtasks
- Handles event metadata and notes

### 4. Main Scheduler (`main_scheduler.py`)
- Orchestrates the complete workflow
- Coordinates all components
- Provides unified interface
- Handles error reporting and cleanup

## Installation

1. Ensure you have the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure Ollama is running with Llama3 model:
   ```bash
   ollama serve
   ollama pull llama3
   ```

3. Ensure CalBridge helper app is running:
   ```bash
   python helper_app.py
   ```

## Usage

### Command Line Interface

The system provides a comprehensive CLI for easy usage:

#### Schedule a Complex Task
```bash
python -m LLM_task_scheduling.cli schedule "Write a research paper on AI ethics" "2025-11-15T23:59:00"
```

#### Schedule a Simple Task
```bash
python -m LLM_task_scheduling.cli simple "Call mom" "+1d" --duration 15 --calendar Home
```

#### Check Free Time
```bash
python -m LLM_task_scheduling.cli free-time "2025-11-01T23:59:00" --show-slots
```

#### Run Tests
```bash
python -m LLM_task_scheduling.cli test
```

### Python API

You can also use the system programmatically:

```python
from LLM_task_scheduling import LLMTaskScheduler, SchedulingRequest

# Create scheduler
scheduler = LLMTaskScheduler()

# Create scheduling request
request = SchedulingRequest(
    task_description="Write a research paper on AI ethics",
    deadline="2025-11-15T23:59:00"
)

# Schedule the task
result = scheduler.schedule_task(request)

# Print results
scheduler.print_result(result)

# Clean up if needed
if result.total_events_created > 0:
    scheduler.cleanup_events(result)
```

## Configuration

### Calendar Configuration
The system uses the calendar configuration from `config/calendars.json`:

```json
{
  "default_work_title": "Work",
  "default_home_title": "Home",
  "calendars": [
    {
      "id": "work_id",
      "title": "Work",
      "writable": true
    },
    {
      "id": "home_id", 
      "title": "Home",
      "writable": true
    }
  ]
}
```

### Environment Variables
- `OLLAMA_BASE`: Ollama API base URL (default: http://127.0.0.1:11434)
- `CALBRIDGE_BASE`: CalBridge API base URL (default: http://127.0.0.1:8765)
- `OLLAMA_MODEL`: LLM model to use (default: llama3)

## Deadline Formats

The system supports various deadline formats:

- **ISO format**: `"2025-11-15T23:59:00"`
- **Date only**: `"2025-11-15"` (defaults to 23:59)
- **Relative days**: `"+7d"` (7 days from now)
- **Relative hours**: `"+2h"` (2 hours from now)

## Task Decomposition Rules

The LLM decomposer follows these rules:

1. **Simple tasks** (like "Call mom for 15 minutes") are not decomposed
2. **Complex tasks** are broken into 2-5 subtasks
3. Each subtask is limited to 5-180 minutes (max 3 hours)
4. Calendar selection: Work for professional tasks, Home for personal tasks
5. If unclear, defaults to Home calendar

## Event Creation Behavior

The system creates events based on task decomposition:

- **Simple tasks** (no decomposition): Creates ONE event with `parent_id: NULL`
- **Complex tasks** (with decomposition): Creates ONLY subtask events (no main event), each with `parent_id` pointing to the generated parent task ID

This ensures that:
- Simple tasks appear as single calendar events
- Complex tasks appear as their constituent subtasks, making them actionable
- Subtasks maintain proper parent-child relationships via parent_id references
- No redundant "parent" events are created for decomposed tasks

## Scheduling Constraints

The system supports various scheduling constraints:

```python
from task_scheduler import ConstraintAdder
from datetime import time, date

constraints = ConstraintAdder()
constraints.add_weekly_blackout(weekday=0, start_t=time(12,0), end_t=time(13,0))  # Monday lunch
constraints.add_date_blackout(date(2025,10,15), start_t=time(9,0), end_t=time(9,30))  # Specific date
constraints.set_min_gap_minutes(30)  # 30 min gap between tasks
constraints.set_max_tasks_per_day(2)  # Max 2 tasks per day
```

## Error Handling

The system provides comprehensive error handling:

- **LLM API errors**: Network issues, model unavailability
- **Calendar API errors**: CalBridge connection issues
- **Scheduling errors**: Infeasible schedules, constraint violations
- **Validation errors**: Invalid inputs, malformed data

All errors are captured and reported in the scheduling result.

## Testing

Run the comprehensive test suite:

```bash
python -m LLM_task_scheduling.cli test
```

The test suite covers:
- LLM decomposer functionality
- Time allotment calculations
- Event creation and management
- Main scheduler integration
- End-to-end workflows

## Examples

### Example 1: Research Paper
```bash
python -m LLM_task_scheduling.cli schedule "Write a research paper on machine learning ethics" "2025-12-01T23:59:00"
```

**Expected Output:**
- Calendar: Work
- Subtasks: Research (120 min), Outline (60 min), Writing (180 min), Review (90 min)
- Total: 4 events created (only subtasks, no main event)
- Each subtask has parent_id pointing to the same generated parent task ID

### Example 2: Simple Task
```bash
python -m LLM_task_scheduling.cli simple "Call mom" "+1d" --duration 15 --calendar Home
```

**Expected Output:**
- Single event created
- 15 minutes duration
- Home calendar
- Scheduled in next available slot

### Example 3: Free Time Check
```bash
python -m LLM_task_scheduling.cli free-time "2025-11-01T23:59:00" --show-slots
```

**Expected Output:**
- Total free time available
- List of free time slots
- Excludes holidays automatically

## Troubleshooting

### Common Issues

1. **Ollama not running**: Ensure Ollama is running and Llama3 model is available
2. **CalBridge not running**: Start the helper app with `python helper_app.py`
3. **No free time slots**: Check if deadline is too soon or calendar is too busy
4. **LLM errors**: Check Ollama API connectivity and model availability

### Debug Mode

Enable debug output by setting environment variables:
```bash
export OLLAMA_BASE=http://127.0.0.1:11434
export CALBRIDGE_BASE=http://127.0.0.1:8765
```

## Contributing

1. Follow the existing code structure
2. Add tests for new functionality
3. Update documentation
4. Ensure all tests pass

## License

This project is part of the calendar-test system and follows the same license terms.
