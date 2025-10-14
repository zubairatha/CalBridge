"""
Time Allotment System
Uses LLM to intelligently assign time slots to tasks and subtasks based on
available free time and user preferences.
"""

import json
import requests
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from user_memory import UserMemory

# Default configuration
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3")
CALBRIDGE_BASE = os.getenv("CALBRIDGE_BASE", "http://127.0.0.1:8765")


class TimeAllotter:
    """Intelligently assigns time slots to tasks based on availability and preferences."""
    
    def __init__(self, ollama_base: str = OLLAMA_BASE, model: str = MODEL):
        """Initialize the time allotter.
        
        Args:
            ollama_base: Base URL for Ollama API
            model: Model name to use for time allocation
        """
        self.ollama_base = ollama_base
        self.model = model
        self.user_memory = UserMemory()
    
    def allot_time_slots(self, decomposed_task: Dict[str, Any], 
                        available_slots: List[Dict[str, Any]], 
                        deadline: Optional[datetime] = None) -> Dict[str, Any]:
        """Allocate time slots to subtasks based on availability and preferences.
        
        Args:
            decomposed_task: Task decomposition result from TaskDecomposer
            available_slots: List of available time slots
            deadline: Optional deadline for the task
            
        Returns:
            Dictionary containing time slot assignments
        """
        # Create the system prompt
        system_prompt = self._create_system_prompt()
        
        # Create user prompt with task and availability details
        user_prompt = self._create_user_prompt(decomposed_task, available_slots, deadline)
        
        # Try LLM scheduling first
        try:
            # Call Ollama for time allocation
            response = self._call_ollama(system_prompt, user_prompt)
            
            # Parse and validate response
            result = self._parse_response(response)
            
            # Validate time slot assignments
            result = self._validate_time_assignments(result, available_slots, decomposed_task)
            
            return result
            
        except Exception as e:
            print(f"⚠️  LLM scheduling failed: {e}")
            print("🔄 Falling back to simple scheduling algorithm...")
            return self._create_fallback_schedule(decomposed_task, available_slots)
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for time allocation."""
        constraints = self.user_memory.get_scheduling_constraints()
        user_memories = self.user_memory.get_memories_for_llm()
        
        prompt = f"""You are an intelligent time allocation assistant. Your job is to assign specific time slots to subtasks based on:

1. Available free time slots
2. User preferences and constraints
3. Task priority and dependencies
4. Optimal scheduling patterns

User constraints:
- Wake up: {constraints['wake_up_time']}
- Sleep: {constraints['sleep_time']}
- Buffer time: 15 minutes

User preferences and patterns:"""
        
        for memory in user_memories:
            prompt += f"\n- {memory['title']}: {memory['description']}"
        
        prompt += f"""

CRITICAL JSON FORMATTING REQUIREMENTS:
- Return ONLY valid JSON - no explanations, no markdown, no comments
- Start your response with {{ and end with }}
- NO text before or after the JSON
- NO comments in JSON (remove all // comments)
- NO trailing commas before }} or ]
- Ensure all strings are properly quoted
- Valid JSON only

Return ONLY valid JSON in this exact format:
{{
  "allocations": [
    {{
      "subtask_id": "subtask_1",
      "scheduled_start": "2025-01-15T09:00:00",
      "scheduled_end": "2025-01-15T11:00:00",
      "duration_minutes": 120,
      "slot_used": 0,
      "reasoning": "High priority task scheduled during peak productivity hours"
    }}
  ],
  "total_scheduled_time": 180,
  "unscheduled_subtasks": [],
  "notes": "Scheduling notes and recommendations"
}}

Rules:
- Schedule nothing before {constraints['wake_up_time']} or after {constraints['sleep_time']} unless specifically requested
- Respect task dependencies (higher priority tasks first)
- Consider user's preferred work patterns from the preferences above
- Leave 15-minute buffer time between tasks
- Try to schedule similar tasks together
- If a task can't be scheduled, add it to unscheduled_subtasks with reasoning
- Use available_slots array indices for slot_used field
- Be realistic about task durations"""

        return prompt
    
    def _create_user_prompt(self, decomposed_task: Dict[str, Any], 
                           available_slots: List[Dict[str, Any]], 
                           deadline: Optional[datetime] = None) -> str:
        """Create the user prompt with task and availability details."""
        prompt = f"""Task to schedule: {decomposed_task.get('notes', 'No additional notes')}
Calendar assignment: {decomposed_task.get('calendar_assignment', 'work')}
Task complexity: {decomposed_task.get('task_complexity', 'medium')}
Estimated total hours: {decomposed_task.get('estimated_total_hours', 2.0)}

Subtasks to schedule:
"""
        
        for subtask in decomposed_task.get('subtasks', []):
            prompt += f"- {subtask['id']}: {subtask['title']} (Priority: {subtask['priority']}, "
            prompt += f"Est. hours: {subtask['estimated_hours']}, Difficulty: {subtask['difficulty']})\n"
            if subtask.get('dependencies'):
                prompt += f"  Dependencies: {', '.join(subtask['dependencies'])}\n"
        
        prompt += f"\nAvailable time slots:\n"
        for i, slot in enumerate(available_slots):
            start_str = slot['start'].strftime('%Y-%m-%dT%H:%M:%S')
            end_str = slot['end'].strftime('%Y-%m-%dT%H:%M:%S')
            duration_hours = slot['duration_minutes'] / 60
            prompt += f"- Slot {i}: {start_str} to {end_str} ({slot['duration_minutes']} minutes / {duration_hours:.1f} hours)\n"
        
        prompt += f"\nIMPORTANT SLOT CONSTRAINTS:\n"
        prompt += f"- You MUST schedule tasks ONLY within the exact time boundaries of each slot\n"
        prompt += f"- scheduled_start must be >= slot start time\n"
        prompt += f"- scheduled_end must be <= slot end time\n"
        prompt += f"- Do NOT schedule across multiple slots in one allocation\n"
        prompt += f"- Each allocation must fit completely within one slot\n"
        prompt += f"- If a task is 3 hours, it needs a slot with at least 3 hours available\n"
        prompt += f"- Check slot durations carefully before scheduling\n"
        
        if deadline:
            prompt += f"\nDeadline: {deadline.strftime('%Y-%m-%d %H:%M:%S')}"
        
        return prompt
    
    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama API for time allocation."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {"temperature": 0.2},  # Very low temperature for consistent scheduling
            "stream": False
        }
        
        print("\n" + "="*80)
        print("⏰ TIME ALLOTTER - LLM INTERACTION")
        print("="*80)
        print(f"📋 Model: {self.model}")
        print(f"🌡️  Temperature: 0.2")
        print(f"🔗 Endpoint: {self.ollama_base}/api/chat")
        
        print("\n📝 SYSTEM PROMPT:")
        print("-" * 40)
        print(system_prompt)
        
        print("\n👤 USER PROMPT:")
        print("-" * 40)
        print(user_prompt)
        
        try:
            print(f"\n⏳ Calling Ollama API...")
            response = requests.post(
                f"{self.ollama_base}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            data = response.json()
            llm_response = data["message"]["content"]
            
            print(f"\n🤖 LLM RESPONSE:")
            print("-" * 40)
            print(llm_response)
            print("="*80)
            
            return llm_response
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ API Error: {e}")
            raise Exception(f"Failed to call Ollama API: {e}")
        except KeyError as e:
            print(f"\n❌ Response Format Error: {e}")
            raise Exception(f"Unexpected response format from Ollama: {e}")
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        # Extract JSON from response
        json_str = self._extract_json_from_response(response)
        
        # Try multiple parsing attempts with different cleaning strategies
        for attempt in range(3):
            try:
                result = json.loads(json_str)
                break
            except json.JSONDecodeError as e:
                if attempt < 2:  # Try cleaning strategies
                    print(f"JSON parsing attempt {attempt + 1} failed: {e}")
                    
                    # Strategy 1: Remove more trailing commas
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    
                    # Strategy 2: Remove any remaining comments
                    json_str = re.sub(r'//.*', '', json_str)
                    
                    # Strategy 3: Fix common issues
                    json_str = json_str.replace(',,', ',')
                    json_str = json_str.replace('{ ,', '{')
                    json_str = json_str.replace('[ ,', '[')
                    
                    print(f"Cleaned JSON (attempt {attempt + 1}): {json_str[:200]}...")
                else:
                    print(f"Final JSON parsing failed: {e}")
                    print(f"Final JSON string: {json_str}")
                    raise Exception(f"Failed to parse JSON response after 3 attempts: {e}")
        
        # Validate required fields
        required_fields = ["allocations", "total_scheduled_time", "unscheduled_subtasks", "notes"]
        for field in required_fields:
            if field not in result:
                raise Exception(f"Missing required field in response: {field}")
        
        # Validate allocations structure
        for allocation in result.get("allocations", []):
            required_allocation_fields = ["subtask_id", "scheduled_start", "scheduled_end", "duration_minutes"]
            for field in required_allocation_fields:
                if field not in allocation:
                    raise Exception(f"Missing required allocation field: {field}")
        
        return result
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from potentially formatted LLM response."""
        response = response.strip()
        
        # Remove any text before the JSON
        if "Here is the scheduled allocation:" in response:
            response = response.split("Here is the scheduled allocation:")[1].strip()
        
        # Try to find JSON within markdown code blocks
        import re
        
        # Look for ```json ... ``` blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, flags=re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Look for any {...} block - find the largest complete JSON object
        json_start = response.find('{')
        if json_start == -1:
            raise Exception("No JSON object found in response")
        
        # Find the matching closing brace
        brace_count = 0
        json_end = -1
        for i, char in enumerate(response[json_start:], json_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i
                    break
        
        if json_end == -1:
            raise Exception("No complete JSON object found in response")
        
        json_str = response[json_start:json_end + 1]
        
        # Clean up common JSON issues
        # Remove comments (// ...)
        json_str = re.sub(r'//.*', '', json_str)
        
        # Remove trailing commas before closing braces/brackets
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        # Fix common issues
        json_str = json_str.replace('"subtask_6", "reasoning": "Medium priority task scheduled during peak productivity hours"', '"subtask_6"')
        
        return json_str
        
        # If it's already pure JSON, return as is
        if response.startswith("{") and response.endswith("}"):
            return response
        
        raise Exception("No valid JSON found in LLM response")
    
    def _validate_time_assignments(self, result: Dict[str, Any], 
                                 available_slots: List[Dict[str, Any]], 
                                 decomposed_task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate time slot assignments against available slots."""
        subtask_ids = {subtask["id"] for subtask in decomposed_task.get("subtasks", [])}
        
        for allocation in result.get("allocations", []):
            subtask_id = allocation.get("subtask_id")
            
            # Validate subtask ID exists
            if subtask_id not in subtask_ids:
                raise Exception(f"Invalid subtask_id in allocation: {subtask_id}")
            
            # Validate time slot usage
            slot_used = allocation.get("slot_used", -1)
            if slot_used >= len(available_slots):
                raise Exception(f"Invalid slot_used index: {slot_used}")
            
            # Validate time format
            try:
                start_time = datetime.fromisoformat(allocation["scheduled_start"])
                end_time = datetime.fromisoformat(allocation["scheduled_end"])
                
                # Ensure timezone awareness for comparison
                if start_time.tzinfo is None:
                    start_time = start_time.astimezone()
                if end_time.tzinfo is None:
                    end_time = end_time.astimezone()
                
                # Check if scheduled time is within available slot
                if slot_used >= 0:
                    available_slot = available_slots[slot_used]
                    slot_start = available_slot["start"]
                    slot_end = available_slot["end"]
                    
                    if start_time < slot_start or end_time > slot_end:
                        print(f"❌ Slot validation failed:")
                        print(f"   Scheduled: {allocation['scheduled_start']} to {allocation['scheduled_end']}")
                        print(f"   Slot {slot_used}: {slot_start} to {slot_end}")
                        raise Exception(f"Allocated time exceeds available slot boundaries")
                    
                    # Additional check: ensure the task fits within the slot duration
                    task_duration = (end_time - start_time).total_seconds() / 60
                    slot_duration = (slot_end - slot_start).total_seconds() / 60
                    
                    if task_duration > slot_duration:
                        print(f"❌ Duration validation failed:")
                        print(f"   Task duration: {task_duration} minutes")
                        print(f"   Slot duration: {slot_duration} minutes")
                        raise Exception(f"Task duration ({task_duration:.1f} min) exceeds slot duration ({slot_duration:.1f} min)")
                
            except ValueError as e:
                raise Exception(f"Invalid datetime format in allocation: {e}")
        
        return result
    
    def _create_fallback_schedule(self, decomposed_task: Dict[str, Any], 
                                 available_slots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a simple fallback schedule when LLM fails."""
        allocations = []
        unscheduled = []
        
        subtasks = decomposed_task.get("subtasks", [])
        current_slot = 0
        current_time = None
        
        for subtask in subtasks:
            estimated_hours = subtask.get("estimated_hours", 0)
            estimated_minutes = int(estimated_hours * 60)
            
            # Find a suitable slot
            scheduled = False
            for slot_idx in range(current_slot, len(available_slots)):
                slot = available_slots[slot_idx]
                slot_duration = slot["duration_minutes"]
                
                if estimated_minutes <= slot_duration:
                    # Schedule in this slot
                    start_time = slot["start"]
                    end_time = start_time + timedelta(minutes=estimated_minutes)
                    
                    allocations.append({
                        "subtask_id": subtask["id"],
                        "scheduled_start": start_time.strftime('%Y-%m-%dT%H:%M:%S'),
                        "scheduled_end": end_time.strftime('%Y-%m-%dT%H:%M:%S'),
                        "duration_minutes": estimated_minutes,
                        "slot_used": slot_idx,
                        "reasoning": "Fallback schedule - simple sequential allocation"
                    })
                    
                    current_slot = slot_idx
                    scheduled = True
                    break
            
            if not scheduled:
                unscheduled.append(subtask["id"])
        
        total_time = sum(alloc["duration_minutes"] for alloc in allocations)
        
        return {
            "allocations": allocations,
            "total_scheduled_time": total_time,
            "unscheduled_subtasks": unscheduled,
            "notes": f"Fallback schedule created. {len(allocations)} scheduled, {len(unscheduled)} unscheduled."
        }
    
    def get_free_time_slots(self, days: int = 30, exclude_holidays: bool = True) -> List[Dict[str, Any]]:
        """Get free time slots from calendar using CalBridge API.
        
        Args:
            days: Number of days to look ahead
            exclude_holidays: Whether to exclude holiday events
            
        Returns:
            List of available time slots
        """
        try:
            # Get events from CalBridge
            params = {"days": days}
            if exclude_holidays:
                params["exclude_holidays"] = "true"
            
            response = requests.get(f"{CALBRIDGE_BASE}/events", params=params, timeout=20)
            response.raise_for_status()
            
            events = response.json()
            
            # Filter out holidays if requested
            if exclude_holidays:
                events = [e for e in events if "holiday" not in (e.get("calendar") or "").lower()]
            
            # Convert to timezone-aware datetime objects and get available slots
            start_date = datetime.now().astimezone()
            end_date = start_date + timedelta(days=days)
            
            return self.user_memory.get_available_time_slots(start_date, end_date, events)
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get events from CalBridge: {e}")


# Example usage and testing
if __name__ == "__main__":
    try:
        allotter = TimeAllotter()
        
        # Get available time slots
        print("Getting available time slots...")
        available_slots = allotter.get_free_time_slots(days=7)
        print(f"Found {len(available_slots)} available time slots")
        
        # Example decomposed task
        decomposed_task = {
            "calendar_assignment": "work",
            "task_complexity": "medium",
            "estimated_total_hours": 4.0,
            "subtasks": [
                {
                    "id": "subtask_1",
                    "title": "Research requirements",
                    "estimated_hours": 1.0,
                    "priority": 1,
                    "difficulty": "low"
                },
                {
                    "id": "subtask_2", 
                    "title": "Design system architecture",
                    "estimated_hours": 2.0,
                    "priority": 2,
                    "difficulty": "high",
                    "dependencies": ["subtask_1"]
                },
                {
                    "id": "subtask_3",
                    "title": "Implement core features",
                    "estimated_hours": 1.0,
                    "priority": 3,
                    "difficulty": "medium",
                    "dependencies": ["subtask_2"]
                }
            ]
        }
        
        # Allocate time slots
        deadline = datetime.now() + timedelta(days=5)
        result = allotter.allot_time_slots(decomposed_task, available_slots, deadline)
        
        print("Time Allocation Result:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
