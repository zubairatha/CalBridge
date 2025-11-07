# Time Allotment Agent (TA)

The Time Allotment Agent schedules tasks into calendar slots using the `task_scheduler` optimizer. It handles both simple and complex tasks, fetching free slots from CalBridge and delegating optimization to the scheduler.

## Overview

The TA agent is the final step in the Streamlined Agents pipeline:
- **Input**: TD.output (simple) or LD.output (complex) + TS.output
- **Output**: Scheduled tasks with assigned slots, IDs, and parent relationships

## Architecture

### Two Paths

1. **SIMPLE Tasks**: Single task scheduling
   - Input: `TD.output` (type="simple") + `TS.output`
   - Output: Single scheduled task with slot

2. **COMPLEX Tasks**: Multiple subtasks scheduling
   - Input: `LD.output` (type="complex") + `TS.output`
   - Output: Parent task with scheduled subtasks

## Key Features

- ✅ Fetches free/busy slots from CalBridge API
- ✅ Delegates optimization to `task_scheduler` (no custom heuristics)
- ✅ Validates scheduled slots (bounds, duration, busy compliance, order)
- ✅ Generates UUIDs for tasks/subtasks
- ✅ Maintains parent_id relationships
- ✅ Handles timezone conversion (timezone-aware input → timezone-naive for scheduler → timezone-aware output)
- ✅ Excludes holidays from busy time
- ✅ Enforces precedence for complex subtasks

## Usage

### Simple Task Scheduling

```python
from Time_Allotment.time_allotment_agent import TimeAllotmentAgent

agent = TimeAllotmentAgent()

td_output = {
    "calendar": "work_1",
    "type": "simple",
    "title": "Call mom",
    "duration": "PT30M"
}

ts_output = {
    "start": "2025-11-05T00:00:00-05:00",
    "end": "2025-11-05T23:59:59-05:00",
    "duration": "PT30M"
}

result = agent.schedule_simple_task(td_output, ts_output)
print(result.to_dict())
```

### Complex Task Scheduling

```python
ld_output = {
    "calendar": "work_1",
    "type": "complex",
    "title": "Plan 5-day Japan trip",
    "subtasks": [
        {"title": "List must-see cities (Japan trip)", "duration": "PT1H"},
        {"title": "Compare flights and book (Japan trip)", "duration": "PT1H30M"},
        {"title": "Book hotels (Japan trip)", "duration": "PT2H"}
    ]
}

ts_output = {
    "start": "2025-11-05T00:00:00-05:00",
    "end": "2025-11-10T23:59:59-05:00",
    "duration": None
}

result = agent.schedule_complex_task(ld_output, ts_output)
print(result.to_dict())
```

## Output Format

### Simple Task Output

```json
{
  "calendar": "<id>",
  "type": "simple",
  "title": "<string>",
  "slot": ["<ISO start>", "<ISO end>"],
  "id": "<uuid4>",
  "parent_id": null
}
```

### Complex Task Output

```json
{
  "calendar": "<id>",
  "type": "complex",
  "title": "<string>",
  "id": "<uuid4>",
  "parent_id": null,
  "subtasks": [
    {
      "title": "<string>",
      "slot": ["<ISO start>", "<ISO end>"],
      "parent_id": "<parent id>",
      "id": "<uuid4>"
    }
  ]
}
```

## Configuration

```python
agent = TimeAllotmentAgent(
    calbridge_base_url="http://127.0.0.1:8765",  # CalBridge API URL
    work_start_hour=6,  # Start of work day (24-hour format)
    work_end_hour=23    # End of work day (24-hour format)
)
```

## Validation

The agent validates all scheduled slots:

1. **Bounds**: Slot must be within `[TS.start, TS.end]`
2. **Duration**: Actual duration must match required duration (to the minute)
3. **Busy Compliance**: No overlap with CalBridge busy events
4. **Non-overlap**: No overlap among subtasks (complex)
5. **Order**: Complex subtasks respect precedence (each starts ≥ previous ends)

If validation fails, the agent raises a `RuntimeError` with a clear error message.

## Defaults

- **DEFAULT_SIMPLE_DURATION**: `PT30M` (used when `TS.duration` is null)
- **Min gap between subtasks**: 5 minutes (for complex tasks)
- **Work window**: 6:00 AM - 11:00 PM (configurable)

## Testing

### Run All Tests

```bash
cd Streamlined_Agents/Time_Allotment
python test/test_time_allotment_agent.py --test all
```

### Run Specific Tests

```bash
# ISO-8601 conversion
python test/test_time_allotment_agent.py --test iso

# Simple task scheduling
python test/test_time_allotment_agent.py --test simple

# Complex task scheduling
python test/test_time_allotment_agent.py --test complex

# Validation errors
python test/test_time_allotment_agent.py --test validation
```

### Full Pipeline Integration

```bash
# Test simple task pipeline
python test/test_full_pipeline_integration.py --test simple

# Test complex task pipeline
python test/test_full_pipeline_integration.py --test complex

# Test multiple queries
python test/test_full_pipeline_integration.py --test multiple
```

**Note**: Full pipeline tests may take time due to LLM calls.

## Dependencies

- `task_scheduler`: Core scheduling algorithm
- `requests`: CalBridge API communication
- `uuid`: ID generation
- `datetime`: Time handling

## Error Handling

The agent handles various error cases:

- **Missing calendar ID**: Raises `ValueError`
- **Invalid task type**: Raises `ValueError`
- **No free slots**: Raises `RuntimeError`
- **Scheduler failure**: Raises `RuntimeError` with details
- **Validation failure**: Raises `RuntimeError` with constraint violation details

## Integration with Pipeline

The TA agent is Step 7 in the full pipeline:

1. **UQ** (User Query Handler) → validates input
2. **SE** (Slot Extractor) → extracts time information
3. **AR** (Absolute Resolver) → resolves to absolute times
4. **TS** (Time Standardizer) → converts to ISO format
5. **TD** (Task Difficulty Analyzer) → classifies task
6. **LD** (LLM Decomposer) → decomposes complex tasks (if needed)
7. **TA** (Time Allotment Agent) → schedules tasks ← **You are here**

## Files

- `time_allotment_agent.py`: Main agent implementation
- `test/test_time_allotment_agent.py`: Unit tests
- `test/test_full_pipeline_integration.py`: Full pipeline integration tests
- `README.md`: This file

