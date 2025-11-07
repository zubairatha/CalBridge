# Streamlined Agents - Full Pipeline Application

A complete CLI application that processes natural language queries through an 8-stage pipeline and creates calendar events.

## Quick Start

### Basic Usage

```bash
cd /Users/zubair/Desktop/Dev/calendar-test
source .venv/bin/activate
python Streamlined_Agents/app.py "Call mom tomorrow at 2pm for 30 minutes"
```

### Interactive Mode

```bash
python Streamlined_Agents/app.py --interactive
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

## Command Line Options

```bash
python Streamlined_Agents/app.py [QUERY] [OPTIONS]
```

### Arguments

- `QUERY` (optional): Natural language query to process
  - If not provided, use `--interactive` mode

### Options

- `--interactive`, `-i`: Run in interactive mode (prompt for queries)
- `--timezone`, `-t TIMEZONE`: Timezone for processing (default: America/New_York)
- `--db-path`, `-d PATH`: Path to Event Creator database (default: event_creator.db)
- `--json`, `-j`: Output final result as JSON
- `--help`, `-h`: Show help message

## Examples

### Simple Task

```bash
python Streamlined_Agents/app.py "Call mom tomorrow at 2pm for 30 minutes"
```

**Output:**
- Creates 1 calendar event
- Shows all 8 pipeline steps
- Displays task ID and calendar event ID

### Complex Task

```bash
python Streamlined_Agents/app.py "Plan a 5-day Japan trip by Nov 15"
```

**Output:**
- Decomposes into 2-5 subtasks
- Creates events for each subtask
- Shows parent-child relationships

### Custom Timezone

```bash
python Streamlined_Agents/app.py "Review proposal next Monday" --timezone "America/Los_Angeles"
```

### JSON Output

```bash
python Streamlined_Agents/app.py "Call dentist tomorrow at 10am" --json
```

### Interactive Mode

```bash
python Streamlined_Agents/app.py --interactive
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
python Streamlined_Agents/app.py "Your query" --db-path /path/to/custom.db
```

## Integration

The application can be integrated into other systems:

```python
from Streamlined_Agents.app import PipelineOrchestrator

orchestrator = PipelineOrchestrator()
result = orchestrator.run_pipeline("Your query here", timezone="America/New_York")

if result["success"]:
    print("Events created successfully!")
    print(result["results"]["ec"])
```

## Files

- `app.py`: Main application file
- `APP_README.md`: This file
- All agent files in `Streamlined_Agents/`
- Test files in `Streamlined_Agents/test/`

## Next Steps

After running the application:
1. Check your calendar for the created events
2. Verify events have correct notes (task IDs and parent IDs)
3. Use the database to track created tasks
4. Use delete functions to remove events if needed

