# Streamlined Agents - Full Pipeline Application

A complete CLI application that processes natural language queries through an 8-stage pipeline and creates calendar events.

## Quick Start

### Basic Usage

```bash
cd /Users/zubair/Desktop/Dev/calendar-test
source .venv/bin/activate
python agents/app.py "Call mom tomorrow at 2pm for 30 minutes"
```

### Interactive Mode

```bash
python agents/app.py --interactive
```

This will prompt you for queries continuously until you type 'quit' or 'exit'.

## Features

- ✅ **Complete 8-Stage Pipeline**: Processes queries from natural language to calendar events
- ✅ **Detailed Step Tracking**: Shows output from each stage with clear formatting
- ✅ **Error Handling**: Graceful error handling at each step
- ✅ **Simple & Complex Tasks**: Handles both simple tasks and complex multi-subtask tasks
- ✅ **Interactive Mode**: Continuous query processing
- ✅ **JSON Output**: Optional JSON output for programmatic use
- ✅ **Timezone Support**: Configurable timezone processing
- ✅ **List Events**: View all events in the database with parent/child relationships
- ✅ **Delete Events**: Delete tasks by ID, parent ID, or all events (with confirmation)
- ✅ **Database Management**: SQLite database tracks all tasks and calendar event mappings

## Command Line Options

```bash
python agents/app.py [QUERY] [OPTIONS]
```

### Arguments

- `QUERY` (optional): Natural language query to process
  - If not provided, use `--interactive` mode

### Options

- `--interactive`, `-i`: Run in interactive mode (prompt for queries)
- `--timezone`, `-t TIMEZONE`: Timezone for processing (default: America/New_York)
- `--db-path`, `-d PATH`: Path to Event Creator database (default: event_creator.db)
- `--json`, `-j`: Output final result as JSON
- `--list`, `-l`: List all events in the database
- `--delete`, `-D TASK_ID`: Delete a task by ID (cascade if parent)
- `--delete-parent PARENT_ID`: Delete all children of a parent task by parent ID
- `--delete-all`: Delete all events from both the database and calendar (WARNING: requires confirmation)
- `--help`, `-h`: Show help message

## Examples

### Simple Task

```bash
python agents/app.py "Call mom tomorrow at 2pm for 30 minutes"
```

**Output:**
- Creates 1 calendar event
- Shows all 8 pipeline steps
- Displays task ID and calendar event ID

### Complex Task

```bash
python agents/app.py "Plan a 5-day Japan trip by Nov 15"
```

**Output:**
- Decomposes into 2-5 subtasks
- Creates events for each subtask
- Shows parent-child relationships

### Custom Timezone

```bash
python agents/app.py "Review proposal next Monday" --timezone "America/Los_Angeles"
```

### JSON Output

```bash
python agents/app.py "Call dentist tomorrow at 10am" --json
```

### List All Events

```bash
python agents/app.py --list
```

**Output:**
- Shows all events in the database
- Groups parent tasks with their children
- Displays task IDs, calendar event IDs, and calendar IDs
- Shows simple tasks separately

### Delete Events

```bash
# Delete a task by ID (cascade if parent)
python agents/app.py --delete <task_id>

# Delete all children of a parent task
python agents/app.py --delete-parent <parent_id>

# Delete all events (requires confirmation)
python agents/app.py --delete-all
```

**Delete Operations:**
- Removes events from both the calendar (via CalBridge API) and the database
- Cascade deletion: Deleting a parent task automatically deletes all children
- Confirmation required for `--delete-all` (type 'yes' to confirm)

### Interactive Mode

```bash
python agents/app.py --interactive
```

Then enter queries one by one:
```
📝 Query: Call mom tomorrow at 2pm for 30 minutes
[Full pipeline output...]

📝 Query: Plan team retreat by December 1st
[Full pipeline output...]

📝 Query: quit
👋 Goodbye!
```

## Pipeline Stages

The application processes queries through 8 stages:

1. **UQ (User Query Handler)**: Validates input and sets timezone
2. **SE (Slot Extractor)**: Extracts time expressions from natural language
3. **AR (Absolute Resolver)**: Resolves relative time to absolute dates/times
4. **TS (Time Standardizer)**: Converts to ISO-8601 format
5. **TD (Task Difficulty Analyzer)**: Classifies task as simple/complex and assigns calendar
6. **LD (LLM Decomposer)**: Decomposes complex tasks into subtasks (only for complex tasks)
7. **TA (Time Allotment Agent)**: Schedules tasks into calendar slots
8. **EC (Event Creator Agent)**: Creates calendar events via CalBridge API

## Output Format

### Step-by-Step Output

Each step shows:
- ✅ Success indicators
- ⚠️ Warnings
- ❌ Errors
- 📊 Data summaries
- 🆔 IDs and references
- ⏰ Time slots
- 📅 Calendar information

### Final Summary

The application ends with a summary showing:
- Status of each pipeline stage
- Final result (success/failure)
- Created event IDs
- Any errors encountered

## Error Handling

- **Graceful Degradation**: If a step fails, the pipeline stops and reports the error
- **Partial Failures**: For complex tasks, partial success is reported (some subtasks created)
- **Clear Error Messages**: Each error includes context about what failed and why

## Requirements

- Python 3.11+
- Virtual environment activated (`.venv`)
- CalBridge API running (`http://127.0.0.1:8765`)
- Ollama running with Qwen2.5:14b-instruct model
- All dependencies from `requirements.txt`

## Troubleshooting

### CalBridge Not Available

If CalBridge is not running, the pipeline will fail at TA or EC stages. Make sure:
```bash
# Check if CalBridge is running
curl http://127.0.0.1:8765/status
```

### LLM Not Available

If Ollama is not running, SE, AR, TD, and LD stages will fail. Make sure:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags
```

### Database Issues

If the Event Creator database has issues, you can specify a custom path:
```bash
python agents/app.py "Your query" --db-path /path/to/custom.db
```

## Integration

The application can be integrated into other systems:

```python
from agents.app import PipelineOrchestrator

orchestrator = PipelineOrchestrator()
result = orchestrator.run_pipeline("Your query here", timezone="America/New_York")

if result["success"]:
    print("Events created successfully!")
    print(result["results"]["ec"])
```

## Files

- `app.py`: Main application file
- `APP_README.md`: This file
- All agent files in `agents/`
- Test files in `agents/test/`

## Database Management

The application uses a SQLite database (`event_creator.db`) to track all tasks and calendar events:

- **Tasks Table**: Stores task IDs, titles, and parent-child relationships
- **Event Map Table**: Maps task IDs to calendar event IDs and calendar IDs

### List Events

```bash
python agents/app.py --list
```

### Delete Events

```bash
# Delete a single task (cascade if parent)
python agents/app.py --delete <task_id>

# Delete all children of a parent task
python agents/app.py --delete-parent <parent_id>

# Delete all events (requires confirmation)
python agents/app.py --delete-all
```

**Note**: All delete operations remove events from both the calendar (via CalBridge API) and the database.

## Next Steps

After running the application:
1. Check your calendar for the created events
2. Verify events have correct notes (task IDs and parent IDs)
3. Use `--list` to view all events in the database
4. Use `--delete` to remove specific events
5. Use `--delete-all` to clear all events (with confirmation)

