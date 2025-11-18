# Agents System

A multi-agent system that processes natural language queries through an 8-stage pipeline to automatically schedule tasks in your calendar.

## Overview

The agents system transforms natural language like "Call mom tomorrow at 2pm" into scheduled calendar events. It uses a combination of LLM-based agents and rule-based processors to understand, classify, and schedule tasks.

## Quick Start

```bash
# From project root
source .venv/bin/activate
python agents/app.py "Call mom tomorrow at 2pm for 30 minutes"
```

For more examples and usage, see [QUICK_START.md](QUICK_START.md) and [APP_README.md](APP_README.md).

## Pipeline Components

The system consists of 8 specialized agents working together:

| Agent | Purpose | Type |
|-------|---------|------|
| **UQ** - User Query Handler | Validates input and sets timezone | Rule-based |
| **SE** - Slot Extractor | Extracts time expressions from natural language | LLM-based |
| **AR** - Absolute Resolver | Resolves relative time to absolute dates/times | LLM-based |
| **TS** - Time Standardizer | Converts to ISO-8601 format | Rule-based |
| **TD** - Task Difficulty Analyzer | Classifies task (simple/complex) and assigns calendar | LLM-based |
| **LD** - LLM Decomposer | Decomposes complex tasks into 2-5 subtasks | LLM-based |
| **TA** - Time Allotment Agent | Schedules tasks into available calendar slots | Optimization |
| **EC** - Event Creator Agent | Creates calendar events via CalBridge API | API Integration |

### How It Works

1. **UQ** validates your query and sets the timezone
2. **SE** extracts time expressions ("tomorrow at 2pm", "30 minutes")
3. **AR** resolves relative times to absolute dates ("October 14, 2025 2:00 PM")
4. **TS** standardizes to ISO-8601 format
5. **TD** classifies the task as simple or complex and assigns Work/Home calendar
6. **LD** (if complex) breaks down into manageable subtasks
7. **TA** schedules tasks into available calendar slots using CalBridge API
8. **EC** creates calendar events and tracks them in SQLite database

## Usage

### Basic Usage

```bash
python agents/app.py "Your natural language query"
```

### Interactive Mode

```bash
python agents/app.py --interactive
```

### List All Events

```bash
python agents/app.py --list
```

### Delete Events

```bash
# Delete a specific task
python agents/app.py --delete <task_id>

# Delete all children of a parent task
python agents/app.py --delete-parent <parent_id>

# Delete all events (requires confirmation)
python agents/app.py --delete-all
```

## Configuration

- **LLM**: Ollama with Qwen2.5:14b-instruct
- **Timezone**: Default `America/New_York` (configurable via `--timezone`)
- **CalBridge API**: Default `http://127.0.0.1:8765`
- **Database**: SQLite (`event_creator.db`)

## Database

The Event Creator Agent uses SQLite to track tasks and calendar events:

- **Tasks Table**: Task IDs, titles, and parent-child relationships
- **Event Map Table**: Maps task IDs to calendar event IDs

All delete operations remove events from both the calendar (via CalBridge) and the database.

## Testing

For development and testing, see the `test/` directory. Test files are organized by component and pipeline stage.

**Note**: Most users should use `agents/app.py` directly. The test files are for development and debugging.

## Requirements

See `requirements.txt` for Python dependencies. Requires:
- Python 3.11+
- Ollama running locally
- CalBridge API running (`http://127.0.0.1:8765`)

## Documentation

- **[QUICK_START.md](QUICK_START.md)**: Quick examples and common use cases
- **[APP_README.md](APP_README.md)**: Complete CLI reference and detailed examples
- **[Time_Allotment/README.md](Time_Allotment/README.md)**: Time Allotment Agent details
