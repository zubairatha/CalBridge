import uuid
import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from models import (
    TaskCreate, TaskResponse, TaskUpdate, SubtaskResponse, 
    LLMDecompositionRequest, LLMDecompositionResponse,
    ScheduleProposal, ChatSessionResponse, ChatMessageCreate, ChatMessageResponse,
    TaskStatus, TaskType
)
from database import get_connection
from .llm_service import LLMService
from .calendar_service import CalendarService

class TaskService:
    """Service for managing tasks and subtasks."""
    
    def __init__(self):
        self.db_path = Path(__file__).resolve().parents[2] / "data" / "tasks.db"
    
    async def create_task(self, task_data: TaskCreate, llm_service: LLMService) -> TaskResponse:
        """Create a new task and trigger LLM decomposition."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Create LLM decomposition request
            llm_request = LLMDecompositionRequest(
                title=task_data.title,
                description=task_data.description,
                deadline=task_data.deadline,
                calendar_target=task_data.calendar_target
            )
            
            # Get LLM decomposition
            decomposition = await llm_service.decompose_task(llm_request)
            
            # Insert task
            cursor.execute("""
                INSERT INTO tasks (
                    id, title, description, deadline, calendar_target, 
                    needs_subtasks, estimated_minutes, task_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                task_data.title,
                task_data.description,
                task_data.deadline.isoformat() if task_data.deadline else None,
                task_data.calendar_target.value if task_data.calendar_target else None,
                decomposition.needs_subtasks,
                decomposition.estimated_minutes,
                decomposition.task_type.value
            ))
            
            # Insert subtasks if needed
            subtasks = []
            if decomposition.needs_subtasks and decomposition.subtasks:
                for subtask_data in decomposition.subtasks:
                    subtask_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO subtasks (
                            id, parent_task_id, title, estimated_minutes, 
                            order_index, task_type
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        subtask_id,
                        task_id,
                        subtask_data.title,
                        subtask_data.estimated_minutes,
                        subtask_data.order_index,
                        subtask_data.task_type.value
                    ))
                    
                    subtasks.append(SubtaskResponse(
                        id=subtask_id,
                        parent_task_id=task_id,
                        title=subtask_data.title,
                        estimated_minutes=subtask_data.estimated_minutes,
                        order_index=subtask_data.order_index,
                        task_type=subtask_data.task_type,
                        status=TaskStatus.PENDING
                    ))
            
            conn.commit()
            
            # Return task with subtasks
            return TaskResponse(
                id=task_id,
                title=task_data.title,
                description=task_data.description,
                deadline=task_data.deadline,
                calendar_target=task_data.calendar_target,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                needs_subtasks=decomposition.needs_subtasks,
                estimated_minutes=decomposition.estimated_minutes,
                task_type=decomposition.task_type,
                subtasks=subtasks
            )
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create task: {e}")
        finally:
            conn.close()
    
    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[TaskResponse]:
        """List all tasks, optionally filtered by status."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            if status:
                cursor.execute("""
                    SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC
                """, (status.value,))
            else:
                cursor.execute("""
                    SELECT * FROM tasks ORDER BY created_at DESC
                """)
            
            tasks = []
            for row in cursor.fetchall():
                task = await self._row_to_task_response(row, cursor)
                tasks.append(task)
            
            return tasks
            
        except Exception as e:
            raise Exception(f"Failed to list tasks: {e}")
        finally:
            conn.close()
    
    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        """Get a specific task with its subtasks."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return await self._row_to_task_response(row, cursor)
            
        except Exception as e:
            raise Exception(f"Failed to get task: {e}")
        finally:
            conn.close()
    
    async def update_task(self, task_id: str, task_data: TaskUpdate) -> Optional[TaskResponse]:
        """Update a task."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Build update query dynamically
            updates = []
            values = []
            
            if task_data.title is not None:
                updates.append("title = ?")
                values.append(task_data.title)
            
            if task_data.description is not None:
                updates.append("description = ?")
                values.append(task_data.description)
            
            if task_data.deadline is not None:
                updates.append("deadline = ?")
                values.append(task_data.deadline.isoformat())
            
            if task_data.calendar_target is not None:
                updates.append("calendar_target = ?")
                values.append(task_data.calendar_target.value)
            
            if task_data.status is not None:
                updates.append("status = ?")
                values.append(task_data.status.value)
                
                if task_data.status == TaskStatus.COMPLETED:
                    updates.append("completed_at = ?")
                    values.append(datetime.now().isoformat())
            
            if not updates:
                return await self.get_task(task_id)
            
            values.append(task_id)
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            
            cursor.execute(query, values)
            
            if cursor.rowcount == 0:
                return None
            
            conn.commit()
            return await self.get_task(task_id)
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to update task: {e}")
        finally:
            conn.close()
    
    async def delete_task(self, task_id: str, calendar_service: CalendarService) -> bool:
        """Delete a task and all its subtasks and calendar events."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get subtasks with calendar events
            cursor.execute("""
                SELECT calendar_event_id FROM subtasks 
                WHERE parent_task_id = ? AND calendar_event_id IS NOT NULL
            """, (task_id,))
            
            event_ids = [row[0] for row in cursor.fetchall()]
            
            # Delete calendar events
            for event_id in event_ids:
                try:
                    await calendar_service.delete_event(event_id)
                except Exception as e:
                    print(f"Warning: Failed to delete calendar event {event_id}: {e}")
            
            # Delete task (subtasks will be deleted by CASCADE)
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            
            if cursor.rowcount == 0:
                return False
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to delete task: {e}")
        finally:
            conn.close()
    
    async def commit_schedule(
        self, 
        task_id: str, 
        proposal: ScheduleProposal, 
        calendar_service: CalendarService
    ) -> bool:
        """Commit a schedule proposal to Apple Calendar."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get task
            task = await self.get_task(task_id)
            if not task:
                return False
            
            # Create calendar events for each time slot
            events_to_create = []
            subtask_updates = []
            
            for i, time_slot in enumerate(proposal.time_slots):
                if i < len(task.subtasks):
                    subtask = task.subtasks[i]
                    
                    # Prepare event data
                    event_data = {
                        "title": subtask.title,
                        "start_iso": time_slot.start.isoformat(),
                        "end_iso": time_slot.end.isoformat(),
                        "notes": f"Task: {task.title} | Subtask: {subtask.title}",
                        "calendar_title": task.calendar_target.value if task.calendar_target else None
                    }
                    
                    events_to_create.append(event_data)
                    subtask_updates.append((subtask.id, time_slot.start.isoformat(), time_slot.end.isoformat()))
            
            # Create events in batch
            created_events = await calendar_service.create_events_batch(events_to_create)
            
            # Update subtasks with calendar event IDs and scheduled times
            for i, (subtask_id, start_iso, end_iso) in enumerate(subtask_updates):
                if i < len(created_events):
                    event_id = created_events[i].id
                    cursor.execute("""
                        UPDATE subtasks 
                        SET calendar_event_id = ?, scheduled_start = ?, scheduled_end = ?, status = ?
                        WHERE id = ?
                    """, (event_id, start_iso, end_iso, TaskStatus.SCHEDULED.value, subtask_id))
            
            # Update task status
            cursor.execute("""
                UPDATE tasks SET status = ? WHERE id = ?
            """, (TaskStatus.SCHEDULED.value, task_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to commit schedule: {e}")
        finally:
            conn.close()
    
    async def complete_subtask(
        self, 
        subtask_id: str, 
        actual_minutes: int, 
        calendar_service: CalendarService
    ) -> bool:
        """Mark a subtask as complete and learn from actual duration."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get subtask details
            cursor.execute("""
                SELECT s.*, t.task_type FROM subtasks s
                JOIN tasks t ON s.parent_task_id = t.id
                WHERE s.id = ?
            """, (subtask_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            # Update subtask
            cursor.execute("""
                UPDATE subtasks 
                SET actual_minutes = ?, status = ?
                WHERE id = ?
            """, (actual_minutes, TaskStatus.COMPLETED.value, subtask_id))
            
            # Record duration history for learning
            cursor.execute("""
                INSERT INTO duration_history (
                    subtask_id, task_type, estimated_minutes, actual_minutes
                ) VALUES (?, ?, ?, ?)
            """, (subtask_id, row['task_type'], row['estimated_minutes'], actual_minutes))
            
            # Delete calendar event
            if row['calendar_event_id']:
                try:
                    await calendar_service.delete_event(row['calendar_event_id'])
                except Exception as e:
                    print(f"Warning: Failed to delete calendar event: {e}")
            
            # Check if all subtasks are complete
            cursor.execute("""
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM subtasks WHERE parent_task_id = ?
            """, (row['parent_task_id'],))
            
            counts = cursor.fetchone()
            if counts['total'] > 0 and counts['completed'] == counts['total']:
                # All subtasks complete, mark task as complete
                cursor.execute("""
                    UPDATE tasks SET status = ?, completed_at = ?
                    WHERE id = ?
                """, (TaskStatus.COMPLETED.value, datetime.now().isoformat(), row['parent_task_id']))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to complete subtask: {e}")
        finally:
            conn.close()
    
    async def create_chat_session(self, title: str = "New Chat") -> ChatSessionResponse:
        """Create a new chat session."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            session_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO chat_sessions (id, title, created_at, last_message_at)
                VALUES (?, ?, ?, ?)
            """, (session_id, title, now, now))
            
            conn.commit()
            
            return ChatSessionResponse(
                id=session_id,
                title=title,
                created_at=datetime.fromisoformat(now),
                last_message_at=datetime.fromisoformat(now)
            )
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create chat session: {e}")
        finally:
            conn.close()

    async def list_chat_sessions(self) -> List[ChatSessionResponse]:
        """List all chat sessions."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM chat_sessions ORDER BY last_message_at DESC
            """)
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append(ChatSessionResponse(
                    id=row['id'],
                    title=row['title'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    last_message_at=datetime.fromisoformat(row['last_message_at'])
                ))
            
            return sessions
            
        except Exception as e:
            raise Exception(f"Failed to list chat sessions: {e}")
        finally:
            conn.close()
    
    async def get_chat_session(self, session_id: str) -> Optional[ChatSessionResponse]:
        """Get a specific chat session with messages."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Get session
            cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
            session_row = cursor.fetchone()
            
            if not session_row:
                return None
            
            # Get messages
            cursor.execute("""
                SELECT * FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY created_at ASC
            """, (session_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append(ChatMessageResponse(
                    id=row['id'],
                    session_id=row['session_id'],
                    role=row['role'],
                    content=row['content'],
                    task_id=row['task_id'],
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            
            return ChatSessionResponse(
                id=session_row['id'],
                title=session_row['title'],
                created_at=datetime.fromisoformat(session_row['created_at']),
                last_message_at=datetime.fromisoformat(session_row['last_message_at']),
                messages=messages
            )
            
        except Exception as e:
            raise Exception(f"Failed to get chat session: {e}")
        finally:
            conn.close()
    
    async def create_chat_message(
        self, 
        session_id: str, 
        message_data: ChatMessageCreate
    ) -> ChatMessageResponse:
        """Create a new chat message."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            message_id = str(uuid.uuid4())
            
            # Insert message
            cursor.execute("""
                INSERT INTO chat_messages (
                    id, session_id, role, content, task_id
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                message_id,
                session_id,
                message_data.role,
                message_data.content,
                message_data.task_id
            ))
            
            # Update session last_message_at
            cursor.execute("""
                UPDATE chat_sessions 
                SET last_message_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
            
            return ChatMessageResponse(
                id=message_id,
                session_id=session_id,
                role=message_data.role,
                content=message_data.content,
                task_id=message_data.task_id,
                created_at=datetime.now()
            )
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create chat message: {e}")
        finally:
            conn.close()
    
    async def _row_to_task_response(self, row: sqlite3.Row, cursor: sqlite3.Cursor) -> TaskResponse:
        """Convert database row to TaskResponse."""
        # Get subtasks
        cursor.execute("""
            SELECT * FROM subtasks WHERE parent_task_id = ? ORDER BY order_index
        """, (row['id'],))
        
        subtasks = []
        for subtask_row in cursor.fetchall():
            subtasks.append(SubtaskResponse(
                id=subtask_row['id'],
                parent_task_id=subtask_row['parent_task_id'],
                title=subtask_row['title'],
                estimated_minutes=subtask_row['estimated_minutes'],
                actual_minutes=subtask_row['actual_minutes'],
                order_index=subtask_row['order_index'],
                calendar_event_id=subtask_row['calendar_event_id'],
                status=TaskStatus(subtask_row['status']),
                scheduled_start=datetime.fromisoformat(subtask_row['scheduled_start']) if subtask_row['scheduled_start'] else None,
                scheduled_end=datetime.fromisoformat(subtask_row['scheduled_end']) if subtask_row['scheduled_end'] else None,
                task_type=TaskType(subtask_row['task_type'])
            ))
        
        return TaskResponse(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            deadline=datetime.fromisoformat(row['deadline']) if row['deadline'] else None,
            calendar_target=row['calendar_target'],
            status=TaskStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']),
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            needs_subtasks=bool(row['needs_subtasks']),
            estimated_minutes=row['estimated_minutes'],
            task_type=TaskType(row['task_type']) if row['task_type'] else None,
            subtasks=subtasks
        )
    
    async def delete_chat_session(self, session_id: str) -> bool:
        """Delete a chat session and all its messages."""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if session exists
            cursor.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,))
            if not cursor.fetchone():
                return False
            
            # Delete messages first (due to foreign key constraint)
            cursor.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            
            # Delete session
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to delete chat session: {e}")
        finally:
            conn.close()