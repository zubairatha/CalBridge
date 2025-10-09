from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager

from models import *
from services.task_service import TaskService
from services.persona_service import PersonaService
from services.calendar_service import CalendarService
from services.scheduler_service import SchedulerService
from services.llm_service import LLMService

# Global services
task_service = None
persona_service = None
calendar_service = None
scheduler_service = None
llm_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global task_service, persona_service, calendar_service, scheduler_service, llm_service
    
    # Initialize services
    task_service = TaskService()
    persona_service = PersonaService()
    calendar_service = CalendarService()
    scheduler_service = SchedulerService(calendar_service, persona_service)
    llm_service = LLMService()
    
    yield
    
    # Cleanup on shutdown
    pass

app = FastAPI(
    title="Smart Local Planner API",
    description="Privacy-first task planner with Apple Calendar integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection
def get_task_service() -> TaskService:
    if task_service is None:
        raise HTTPException(status_code=500, detail="Task service not initialized")
    return task_service

def get_persona_service() -> PersonaService:
    if persona_service is None:
        raise HTTPException(status_code=500, detail="Persona service not initialized")
    return persona_service

def get_calendar_service() -> CalendarService:
    if calendar_service is None:
        raise HTTPException(status_code=500, detail="Calendar service not initialized")
    return calendar_service

def get_scheduler_service() -> SchedulerService:
    if scheduler_service is None:
        raise HTTPException(status_code=500, detail="Scheduler service not initialized")
    return scheduler_service

def get_llm_service() -> LLMService:
    if llm_service is None:
        raise HTTPException(status_code=500, detail="LLM service not initialized")
    return llm_service

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Smart Local Planner API", "version": "1.0.0", "docs": "/docs"}

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Smart Local Planner API is running"}

# Task endpoints
@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    task_svc: TaskService = Depends(get_task_service),
    llm_svc: LLMService = Depends(get_llm_service)
):
    """Create a new task and trigger LLM decomposition."""
    try:
        task = await task_svc.create_task(task_data, llm_svc)
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[TaskStatus] = None,
    task_svc: TaskService = Depends(get_task_service)
):
    """List all tasks, optionally filtered by status."""
    try:
        tasks = await task_svc.list_tasks(status)
        return tasks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_svc: TaskService = Depends(get_task_service)
):
    """Get a specific task with its subtasks."""
    try:
        task = await task_svc.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    task_svc: TaskService = Depends(get_task_service)
):
    """Update a task."""
    try:
        task = await task_svc.update_task(task_id, task_data)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: str,
    task_svc: TaskService = Depends(get_task_service),
    calendar_svc: CalendarService = Depends(get_calendar_service)
):
    """Delete a task and all its subtasks and calendar events."""
    try:
        success = await task_svc.delete_task(task_id, calendar_svc)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"success": True, "message": "Task deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Scheduling endpoints
@app.post("/api/tasks/{task_id}/schedule", response_model=ScheduleProposal)
async def generate_schedule(
    task_id: str,
    scheduler_svc: SchedulerService = Depends(get_scheduler_service),
    task_svc: TaskService = Depends(get_task_service)
):
    """Generate a schedule proposal for a task."""
    try:
        task = await task_svc.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        proposal = await scheduler_svc.generate_schedule_proposal(task)
        return proposal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/commit")
async def commit_schedule(
    task_id: str,
    commit_request: ScheduleCommitRequest,
    task_svc: TaskService = Depends(get_task_service),
    calendar_svc: CalendarService = Depends(get_calendar_service)
):
    """Commit a schedule proposal to Apple Calendar."""
    try:
        if not commit_request.approved:
            return {"success": False, "message": "Schedule not approved"}
        
        success = await task_svc.commit_schedule(task_id, commit_request.proposal, calendar_svc)
        if not success:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {"success": True, "message": "Schedule committed to calendar"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Subtask endpoints
@app.post("/api/subtasks/{subtask_id}/complete")
async def complete_subtask(
    subtask_id: str,
    actual_minutes: int,
    task_svc: TaskService = Depends(get_task_service),
    calendar_svc: CalendarService = Depends(get_calendar_service)
):
    """Mark a subtask as complete and learn from actual duration."""
    try:
        success = await task_svc.complete_subtask(subtask_id, actual_minutes, calendar_svc)
        if not success:
            raise HTTPException(status_code=404, detail="Subtask not found")
        
        return {"success": True, "message": "Subtask completed"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Persona endpoints
@app.get("/api/persona", response_model=PersonaConstraints)
async def get_persona(
    persona_svc: PersonaService = Depends(get_persona_service)
):
    """Get user persona constraints."""
    try:
        constraints = await persona_svc.get_constraints()
        return constraints
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/persona")
async def update_persona(
    constraints: PersonaConstraints,
    persona_svc: PersonaService = Depends(get_persona_service)
):
    """Update user persona constraints."""
    try:
        await persona_svc.update_constraints(constraints)
        return {"success": True, "message": "Persona constraints updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Calendar endpoints
@app.get("/api/free-slots", response_model=List[FreeSlotResponse])
async def get_free_slots(
    start: datetime,
    end: datetime,
    duration_minutes: int,
    calendar_target: Optional[CalendarTarget] = None,
    scheduler_svc: SchedulerService = Depends(get_scheduler_service)
):
    """Find available calendar windows."""
    try:
        request = FreeSlotRequest(
            start=start,
            end=end,
            duration_minutes=duration_minutes,
            calendar_target=calendar_target
        )
        slots = await scheduler_svc.find_free_slots(request)
        return slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chat endpoints
@app.post("/api/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    title: str = "New Chat",
    task_svc: TaskService = Depends(get_task_service)
):
    """Create a new chat session."""
    try:
        session = await task_svc.create_chat_session(title)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    task_svc: TaskService = Depends(get_task_service)
):
    """List all chat sessions."""
    try:
        sessions = await task_svc.list_chat_sessions()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    task_svc: TaskService = Depends(get_task_service)
):
    """Get a specific chat session with messages."""
    try:
        session = await task_svc.get_chat_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    task_svc: TaskService = Depends(get_task_service)
):
    """Delete a chat session and all its messages."""
    try:
        success = await task_svc.delete_chat_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Chat session not found")
        return {"success": True, "message": "Chat session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def create_chat_message(
    session_id: str,
    message_data: ChatMessageCreate,
    task_svc: TaskService = Depends(get_task_service)
):
    """Create a new chat message."""
    try:
        message = await task_svc.create_chat_message(session_id, message_data)
        return message
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error", "details": str(exc)}
    )

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
