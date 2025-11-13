# Quick Start Guide

## Run Your First Query

```bash
cd /Users/zubair/Desktop/Dev/calendar-test
source .venv/bin/activate
python Streamlined_Agents/app.py "Call mom tomorrow at 2pm for 30 minutes"
```

## Interactive Mode

```bash
python Streamlined_Agents/app.py --interactive
```

## Common Examples

### Simple Tasks
```bash
# Call with duration
python Streamlined_Agents/app.py "Call dentist tomorrow at 10am for 45 minutes"

# Meeting
python Streamlined_Agents/app.py "Team meeting next Monday at 2pm for 1 hour"

# Deadline task
python Streamlined_Agents/app.py "Complete report by Friday"
```

### Complex Tasks
```bash
# Trip planning
python Streamlined_Agents/app.py "Plan a 5-day Japan trip by Nov 15"

# Event organization
python Streamlined_Agents/app.py "Organize team retreat by December 1st"

# Project planning
python Streamlined_Agents/app.py "Launch new product by end of month"
```

## What Happens

1. **Query Processing**: Your natural language query is parsed
2. **Time Extraction**: Time information is extracted and resolved
3. **Task Classification**: Task is classified as simple or complex
4. **Scheduling**: Tasks are scheduled into available calendar slots
5. **Event Creation**: Calendar events are created via CalBridge

## Check Results

After running, check your calendar app (Calendar.app on macOS) to see the created events.

Events will have notes like:
- Simple: `id: <uuid>, parent_id: null`
- Complex subtask: `id: <uuid>, parent_id: <parent-uuid>`

## List Events

View all events in the database:

```bash
python Streamlined_Agents/app.py --list
```

## Delete Events

```bash
# Delete a task by ID (cascade if parent)
python Streamlined_Agents/app.py --delete <task_id>

# Delete all children of a parent task
python Streamlined_Agents/app.py --delete-parent <parent_id>

# Delete all events (requires confirmation)
python Streamlined_Agents/app.py --delete-all
```

## Troubleshooting

**CalBridge not running?**
```bash
# Start helper_app.py in another terminal
python helper_app.py
```

**Ollama not running?**
```bash
# Start Ollama
ollama serve
```

**Need help?**
```bash
python Streamlined_Agents/app.py --help
```

