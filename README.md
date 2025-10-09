# Smart Local Planner

A privacy-first, LLM-powered task planner that understands your habits and constraints, breaks tasks into smart subtasks, and automatically schedules them into Apple Calendar—then adapts as things change.

## Features

- **Personalization**: Capture user persona (work hours, gym times, preferences) and enforce constraints
- **LLM-driven planning**: Natural language requests → task decomposition with time estimates
- **Smart scheduling**: Find optimal time slots based on task type, energy levels, and constraints
- **Apple Calendar integration**: Seamless read/write via CalBridge
- **Learning system**: Improve estimates over time based on actual durations
- **Privacy-first**: Everything runs locally (Ollama + CalBridge)

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│  FastAPI Backend │────▶│  CalBridge API  │
│  (Port 3000)    │     │  (Port 8000)     │     │  (Port 8765)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                           │
                               ▼                           ▼
                        ┌──────────────┐          ┌──────────────┐
                        │  SQLite DB   │          │Apple Calendar│
                        │  (tasks.db)  │          └──────────────┘
                        └──────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │ Ollama (LLM) │
                        │ (Port 11434) │
                        └──────────────┘
```

## Quick Start

### Prerequisites

- macOS with Apple Calendar
- Python 3.11+
- Node.js 18+
- Ollama with a compatible model (e.g., `gemma3`)

### Installation

1. **Clone and setup Python environment:**
```bash
git clone <repo-url>
cd calendar-test
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Build and run CalBridge:**
```bash
# Build CalBridge app
rm -rf build dist
python setup.py py2app -A
./dist/CalBridge.app/Contents/MacOS/CalBridge
```

3. **Start the Smart Planner backend:**
```bash
cd planner/backend
python main.py
```

4. **Start the React frontend:**
```bash
cd planner-frontend
npm install
npm run dev
```

5. **Start Ollama (if not running):**
```bash
ollama serve
ollama pull gemma3  # or your preferred model
```

### First Run

1. Open http://localhost:3000 in your browser
2. Grant calendar permissions to CalBridge when prompted
3. Configure your persona settings (work hours, preferences)
4. Start planning: "Finish project proposal by next Friday"

## Usage

### Chat Interface

The main interface is a chat-like experience:

1. **Type your request**: "Call with dad for 30 minutes" or "Plan vacation to Europe"
2. **AI analyzes**: Determines if task needs subtasks, estimates time
3. **Review & edit**: Adjust subtasks, durations, or task details
4. **Schedule**: AI finds optimal time slots based on your constraints
5. **Approve**: Commit to Apple Calendar

### Persona Settings

Configure your constraints and preferences:

- **Work Hours**: Set available hours for each day
- **Recurring Blocks**: Define gym, lunch, or other fixed commitments
- **Preferences**: Deep work hours, meeting times, buffer periods
- **Import/Export**: Upload text descriptions or JSON configs

### Calendar View

- **Week/Month views**: See all scheduled tasks
- **Task types**: Color-coded by type (deep work, meetings, etc.)
- **Drag & drop**: Reschedule tasks (coming soon)
- **Sync**: Manual refresh from Apple Calendar

## API Endpoints

### Tasks
- `POST /api/tasks` - Create task with LLM decomposition
- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{id}` - Get task details
- `PUT /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task and calendar events

### Scheduling
- `POST /api/tasks/{id}/schedule` - Generate schedule proposal
- `POST /api/tasks/{id}/commit` - Commit schedule to calendar
- `GET /api/free-slots` - Find available time windows

### Persona
- `GET /api/persona` - Get user constraints
- `PUT /api/persona` - Update constraints

### Chat
- `GET /api/chat/sessions` - List chat sessions
- `POST /api/chat/sessions/{id}/messages` - Send message

## Configuration

### Environment Variables

```bash
# Ollama
OLLAMA_BASE=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3

# CalBridge
CALBRIDGE_BASE=http://127.0.0.1:8765

# Timezone
TIMEZONE=America/New_York
```

### Persona Constraints

Example `constraints.json`:
```json
{
  "work_hours": {
    "monday": ["09:00", "17:00"],
    "tuesday": ["09:00", "17:00"],
    "wednesday": ["09:00", "17:00"],
    "thursday": ["09:00", "17:00"],
    "friday": ["09:00", "17:00"],
    "saturday": null,
    "sunday": null
  },
  "recurring_blocks": [
    {
      "title": "Gym",
      "days": ["tuesday", "thursday"],
      "time": ["17:00", "18:00"]
    }
  ],
  "preferences": {
    "deep_work_hours": ["09:00", "12:00"],
    "meeting_hours": ["14:00", "17:00"],
    "min_block_minutes": 30,
    "buffer_minutes": 15
  }
}
```

## Development

### Project Structure

```
calendar-test/
├── helper_app.py              # CalBridge (Apple Calendar API)
├── setup.py                   # CalBridge build config
├── scripts/                   # Helper CLI tools
├── planner/
│   ├── backend/               # FastAPI server
│   │   ├── main.py           # API endpoints
│   │   ├── models.py         # Pydantic models
│   │   ├── database.py       # SQLite setup
│   │   └── services/         # Business logic
│   │       ├── llm_service.py
│   │       ├── calendar_service.py
│   │       ├── persona_service.py
│   │       ├── task_service.py
│   │       └── scheduler_service.py
│   └── data/
│       ├── tasks.db          # SQLite database
│       └── persona/
│           └── constraints.json
└── planner-frontend/          # React app
    ├── src/
    │   ├── components/
    │   │   ├── AppLayout.jsx
    │   │   ├── ChatArea.jsx
    │   │   ├── TaskProposal.jsx
    │   │   ├── ScheduleProposal.jsx
    │   │   ├── PersonaSettings.jsx
    │   │   └── CalendarModal.jsx
    │   └── App.jsx
    └── package.json
```

### Database Schema

```sql
-- Main tasks
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    deadline TIMESTAMP,
    calendar_target TEXT,
    status TEXT DEFAULT 'pending',
    needs_subtasks BOOLEAN DEFAULT 1,
    estimated_minutes INTEGER,
    task_type TEXT
);

-- Subtasks (LLM-generated)
CREATE TABLE subtasks (
    id TEXT PRIMARY KEY,
    parent_task_id TEXT NOT NULL,
    title TEXT NOT NULL,
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    order_index INTEGER,
    calendar_event_id TEXT,
    status TEXT DEFAULT 'pending',
    scheduled_start TIMESTAMP,
    scheduled_end TIMESTAMP,
    task_type TEXT
);

-- User persona constraints
CREATE TABLE persona_constraints (
    id INTEGER PRIMARY KEY,
    constraint_type TEXT,
    data JSON,
    active BOOLEAN DEFAULT 1
);

-- Learning from actual durations
CREATE TABLE duration_history (
    id INTEGER PRIMARY KEY,
    subtask_id TEXT,
    task_type TEXT,
    estimated_minutes INTEGER,
    actual_minutes INTEGER,
    completed_at TIMESTAMP
);
```

### Smart Scheduling Algorithm

The scheduler considers:

1. **Persona Constraints**: Work hours, recurring blocks, preferences
2. **Task Type Scoring**: Deep work → morning, meetings → afternoon
3. **Energy Levels**: Peak morning energy, afternoon dip, recovery
4. **Time-of-Day Optimization**: Match task difficulty to energy
5. **Calendar Gaps**: Find available windows between existing events

### LLM Integration

Uses structured prompts to:
- Analyze task complexity
- Decide if subtasks are needed (2-10 based on complexity)
- Generate realistic time estimates
- Classify task types (deep_work, meeting, quick_task, research)

## Troubleshooting

### CalBridge Issues

```bash
# Check if CalBridge is running
curl http://127.0.0.1:8765/status

# Reset calendar permissions
tccutil reset Calendar dev.zubair.CalBridge

# Kill existing processes
pkill -f CalBridge
```

### Ollama Issues

```bash
# Check if Ollama is running
curl http://127.0.0.1:11434/api/tags

# Pull model if missing
ollama pull gemma3

# Check model availability
ollama list
```

### Database Issues

```bash
# Reset database
rm planner/data/tasks.db
# Restart backend to recreate schema
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Roadmap

- [ ] Drag & drop rescheduling in calendar view
- [ ] Recurring task templates
- [ ] Team collaboration features
- [ ] Mobile app
- [ ] Advanced learning algorithms
- [ ] Integration with other calendar providers
- [ ] Voice input support
- [ ] Task templates and workflows