from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    DEEP_WORK = "deep_work"
    MEETING = "meeting"
    QUICK_TASK = "quick_task"
    RESEARCH = "research"

class CalendarTarget(str, Enum):
    WORK = "Work"
    HOME = "Home"

# Task Models
class SubtaskCreate(BaseModel):
    title: str
    estimated_minutes: int
    order_index: int
    task_type: TaskType

class SubtaskResponse(BaseModel):
    id: str
    parent_task_id: str
    title: str
    estimated_minutes: int
    actual_minutes: Optional[int] = None
    order_index: int
    calendar_event_id: Optional[str] = None
    status: TaskStatus
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    task_type: TaskType

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    calendar_target: Optional[CalendarTarget] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    calendar_target: Optional[CalendarTarget] = None
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    needs_subtasks: bool
    estimated_minutes: Optional[int] = None
    task_type: Optional[TaskType] = None
    subtasks: List[SubtaskResponse] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    calendar_target: Optional[CalendarTarget] = None
    status: Optional[TaskStatus] = None

# LLM Models
class LLMDecompositionRequest(BaseModel):
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    calendar_target: Optional[CalendarTarget] = None

class LLMDecompositionResponse(BaseModel):
    needs_subtasks: bool
    estimated_minutes: int
    task_type: TaskType
    subtasks: List[SubtaskCreate] = []
    reasoning: str

# Scheduling Models
class TimeSlot(BaseModel):
    start: datetime
    end: datetime
    score: float
    reason: str

class ScheduleProposal(BaseModel):
    task_id: str
    subtasks: List[SubtaskResponse]
    time_slots: List[TimeSlot]
    total_estimated_minutes: int
    conflicts: List[str] = []

class ScheduleCommitRequest(BaseModel):
    proposal: ScheduleProposal
    approved: bool = True

# Persona Models
class WorkHours(BaseModel):
    monday: Optional[List[str]] = None
    tuesday: Optional[List[str]] = None
    wednesday: Optional[List[str]] = None
    thursday: Optional[List[str]] = None
    friday: Optional[List[str]] = None
    saturday: Optional[List[str]] = None
    sunday: Optional[List[str]] = None

class RecurringBlock(BaseModel):
    title: str
    days: List[str]
    time: List[str]  # [start, end]

class Preferences(BaseModel):
    deep_work_hours: List[str] = ["09:00", "12:00"]
    meeting_hours: List[str] = ["14:00", "17:00"]
    min_block_minutes: int = 30
    buffer_minutes: int = 15

class PersonaConstraints(BaseModel):
    work_hours: WorkHours
    recurring_blocks: List[RecurringBlock] = []
    preferences: Preferences = Preferences()

# Chat Models
class ChatMessageCreate(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    task_id: Optional[str] = None

class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    task_id: Optional[str] = None
    created_at: datetime

class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    last_message_at: datetime
    messages: List[ChatMessageResponse] = []

# Calendar Models (for CalBridge integration)
class CalendarEvent(BaseModel):
    id: str
    title: str
    start_iso: str
    end_iso: str
    calendar: str
    notes: Optional[str] = None

class FreeSlotRequest(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int
    calendar_target: Optional[CalendarTarget] = None

class FreeSlotResponse(BaseModel):
    start: datetime
    end: datetime
    duration_minutes: int
    score: float
    reason: str

# API Response Models
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[Dict[str, Any]] = None
