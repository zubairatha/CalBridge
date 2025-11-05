# Streamlined Agents

A LangGraph-based agent system for processing natural language queries and extracting time-related information.

## Components Implemented

### 1. User Query (UQ)
- **File**: `user_query.py`
- **Purpose**: Simple input handler for user queries with timezone management
- **Features**: Input validation, timezone support, clean data models

### 2. Slot Extractor (SE)
- **File**: `slot_extractor.py`
- **Purpose**: LLM-based extraction of start, end, duration from user queries
- **Features**: Extracts raw time information using Ollama (llama3), robust error handling

### 3. Absolute Resolver (AR)
- **File**: `absolute_resolver.py`
- **Purpose**: LLM-based resolution of time slots to absolute dates/times
- **Features**: Converts relative time expressions to absolute datetime strings

### 4. Time Standardizer (TS)
- **File**: `time_standardizer.py`
- **Purpose**: Convert Absolute Resolver output to ISO formats
- **Features**: Regex-based parsing, timezone handling, duration normalization, invariant enforcement

### 5. Task Difficulty Analyzer (TD)
- **File**: `task_difficulty_analyzer.py`
- **Purpose**: LLM-based classification of tasks and calendar assignment
- **Features**: Classifies tasks as simple/complex, assigns Work/Home calendar via CalBridge API, generates short imperative titles, preserves duration unchanged

## Testing

### Full Pipeline Test (UQ → SE → AR → TS)
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_ts.py "your query here"
```

### Full Pipeline Test with TD (UQ → SE → AR → TS → TD)
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_td.py "your query here"
```

### Interactive Pipeline Mode
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_ts.py --interactive
```

### Test Multiple Examples
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_ts.py --multiple
```

### Test Specific Scenarios
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_ts.py --scenarios
```

### Test Individual Components

#### Slot Extractor Only
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_slot_extractor.py "your query here"
```

#### Absolute Resolver Only
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_absolute_resolver.py --test
```

#### Time Standardizer Only
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_time_standardizer.py --test
```

#### Time Standardizer Edge Cases
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_time_standardizer.py --edge
```

#### Time Standardizer Interactive
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_time_standardizer.py --interactive
```

#### Task Difficulty Analyzer
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_task_difficulty_analyzer.py --basic
```

#### Task Difficulty Analyzer - All Tests
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_task_difficulty_analyzer.py --all
```

#### Task Difficulty Analyzer - Interactive
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_task_difficulty_analyzer.py --interactive
```

#### Full Pipeline with TD - Multiple Examples
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_td.py --multiple
```

#### Full Pipeline with TD - Interactive
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_td.py --interactive
```

#### Full Pipeline with TD - Scenarios
```bash
cd /Users/zubair/Desktop/Dev/calendar-test && source .venv/bin/activate && python Streamlined_Agents/test/test_full_pipeline_with_td.py --scenarios
```

## Configuration

- **LLM**: Ollama with Qwen2.5:14b-instruct (temperature 0.7 for most agents, 0.2 for TD)
- **Timezone**: Default America/New_York (configurable)
- **CalBridge API**: Default http://127.0.0.1:8765 (for calendar lookup)
- **Output**: JSON format with time information and task classification

## Requirements

See `requirements.txt` for dependencies.

## Pipeline Flow

The complete pipeline includes:
1. **UQ** → User Query Handler (input validation)
2. **SE** → Slot Extractor (extract time information)
3. **AR** → Absolute Resolver (resolve to absolute dates/times)
4. **TS** → Time Standardizer (convert to ISO formats)
5. **TD** → Task Difficulty Analyzer (classify task and assign calendar)

The Time Standardizer provides ISO format datetime strings, and the Task Difficulty Analyzer provides calendar assignment and task classification suitable for calendar integration via CalBridge API.
