"""
Smart LLM Task Decomposer
Uses Ollama LLM to intelligently break down tasks and determine calendar assignment.
"""

import json
import requests
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Default configuration
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "llama3")  # Changed to llama3 as specified in TODO
CALBRIDGE_BASE = os.getenv("CALBRIDGE_BASE", "http://127.0.0.1:8765")


class TaskDecomposer:
    """Uses LLM to decompose tasks and determine calendar assignment."""
    
    def __init__(self, ollama_base: str = OLLAMA_BASE, model: str = MODEL):
        """Initialize the task decomposer.
        
        Args:
            ollama_base: Base URL for Ollama API
            model: Model name to use for decomposition
        """
        self.ollama_base = ollama_base
        self.model = model
        self.calendars = self._load_calendar_cache()
    
    def _load_calendar_cache(self) -> Dict[str, str]:
        """Load calendar cache from config file."""
        cache_path = Path(__file__).resolve().parents[1] / "config" / "calendars.json"
        
        if not cache_path.exists():
            raise FileNotFoundError(f"Calendar cache not found: {cache_path}. Run scripts/cache_calendars.py first.")
        
        with open(cache_path, 'r') as f:
            data = json.load(f)
        
        calendars = {}
        for cal in data.get("calendars", []):
            if cal.get("writable"):
                calendars[cal["title"].lower()] = cal["id"]
        
        return calendars
    
    def decompose_task(self, task_description: str, deadline: Optional[datetime] = None, 
                      user_memory: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Decompose a task into subtasks and determine calendar assignment.
        
        Args:
            task_description: Description of the task to decompose
            deadline: Optional deadline for the task
            user_memory: Optional user memory list (title, description, tags format)
            
        Returns:
            Dictionary containing calendar assignment and subtasks
        """
        # Create the system prompt
        system_prompt = self._create_system_prompt(user_memory)
        
        # Create user prompt with task details
        user_prompt = self._create_user_prompt(task_description, deadline)
        
        # Call Ollama
        response = self._call_ollama(system_prompt, user_prompt)
        
        # Parse and validate response
        result = self._parse_response(response)
        
        # Validate calendar assignment
        result = self._validate_calendar_assignment(result)
        
        return result
    
    def _create_system_prompt(self, user_memory: Optional[List[Dict[str, str]]] = None) -> str:
        """Create the system prompt for task decomposition."""
        available_calendars = list(self.calendars.keys())
        
        prompt = f"""You are an intelligent task decomposition assistant. Your job is to:

1. Determine which calendar to assign the task to (Work, Home, etc.)
2. Break down complex tasks into 1-10 manageable subtasks
3. Estimate difficulty and time requirements for each subtask

CRITICAL CONSTRAINT: NO subtask can exceed 3 hours. Break any longer task into multiple subtasks.

Available calendars: {', '.join(available_calendars)}

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
  "calendar_assignment": "work|home|personal",
  "task_complexity": "low|medium|high",
  "estimated_total_hours": 2.5,
  "subtasks": [
    {{
      "id": "subtask_1",
      "title": "Specific subtask title",
      "description": "Detailed description of what needs to be done",
      "estimated_hours": 1.0,
      "difficulty": "low|medium|high",
      "dependencies": ["subtask_2"],
      "priority": 1
    }}
  ],
  "notes": "Any additional context or considerations"
}}

Rules:
- If task is simple (can be done in <2 hours), return empty subtasks array
- Calendar assignment: use "work" for professional/business tasks, "home" for personal
- Be specific in subtask titles (avoid vague terms like "research" or "plan")
- Dependencies should reference other subtask IDs
- Priority 1 = must do first, 2 = can be done in parallel, 3 = can be done last
- Total estimated_hours should roughly sum to estimated_total_hours
- MAXIMUM subtask time: 3 hours - break down any subtask longer than 3 hours into smaller ones
- If a task would take more than 3 hours, split it into multiple subtasks of 1-3 hours each
- Example: "Design database" (6 hours) should become "Design database schema" (3 hours) + "Set up database tables" (3 hours)"""

        if user_memory:
            prompt += f"\n\nUser preferences and patterns:"
            for memory in user_memory:
                prompt += f"\n- {memory['title']}: {memory['description']}"
        
        return prompt
    
    def _create_user_prompt(self, task_description: str, deadline: Optional[datetime] = None) -> str:
        """Create the user prompt with task details."""
        prompt = f"Task: {task_description}"
        
        if deadline:
            prompt += f"\nDeadline: {deadline.strftime('%Y-%m-%d %H:%M')}"
            days_until_deadline = (deadline - datetime.now()).days
            prompt += f"\nDays until deadline: {days_until_deadline}"
        
        return prompt
    
    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Call Ollama API for task decomposition."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {"temperature": 0.3},  # Lower temperature for more consistent results
            "stream": False
        }
        
        print("\n" + "="*80)
        print("🤖 TASK DECOMPOSER - LLM INTERACTION")
        print("="*80)
        print(f"📋 Model: {self.model}")
        print(f"🌡️  Temperature: 0.3")
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
        # Extract JSON from response (handle potential markdown formatting)
        json_str = self._extract_json_from_response(response)
        
        try:
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse JSON response: {e}")
        
        # Validate required fields
        required_fields = ["calendar_assignment", "task_complexity", "estimated_total_hours", "subtasks"]
        for field in required_fields:
            if field not in result:
                raise Exception(f"Missing required field in response: {field}")
        
        # Validate subtasks structure
        for subtask in result.get("subtasks", []):
            required_subtask_fields = ["id", "title", "estimated_hours", "difficulty", "priority"]
            for field in required_subtask_fields:
                if field not in subtask:
                    raise Exception(f"Missing required subtask field: {field}")
            
            # Validate and auto-fix subtask time constraint (max 3 hours)
            estimated_hours = subtask.get("estimated_hours", 0)
            if estimated_hours > 3.0:
                # Auto-break down oversized subtasks
                num_subtasks = int(estimated_hours / 3.0) + (1 if estimated_hours % 3.0 > 0 else 0)
                new_hours_per_subtask = estimated_hours / num_subtasks
                
                # Update the current subtask to fit within 3 hours
                subtask["estimated_hours"] = min(3.0, new_hours_per_subtask)
                
                # Add additional subtasks if needed
                subtasks = result.get("subtasks", [])
                current_index = subtasks.index(subtask)
                
                for i in range(1, num_subtasks):
                    new_subtask = {
                        "id": f"{subtask['id']}_part{i+1}",
                        "title": f"{subtask['title']} (Part {i+1})",
                        "description": f"Continued work on {subtask['title']}",
                        "estimated_hours": min(3.0, new_hours_per_subtask),
                        "difficulty": subtask.get("difficulty", "medium"),
                        "dependencies": [f"{subtask['id']}_part{i}"] if i > 1 else [subtask['id']],
                        "priority": subtask.get("priority", 2)
                    }
                    subtasks.insert(current_index + i, new_subtask)
                
                # Update the original subtask title
                subtask["title"] = f"{subtask['title']} (Part 1)"
        
        return result
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from potentially formatted LLM response."""
        response = response.strip()
        
        # Try to find JSON within markdown code blocks first
        import re
        
        # Look for ```json ... ``` blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, flags=re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Look for any {...} block
        json_match = re.search(r'(\{.*\})', response, flags=re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # If it's already pure JSON, return as is
        if response.startswith("{") and response.endswith("}"):
            return response
        
        raise Exception("No valid JSON found in LLM response")
    
    def _validate_calendar_assignment(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix calendar assignment."""
        calendar_assignment = result.get("calendar_assignment", "").lower()
        
        # Map to available calendars
        if calendar_assignment in ["work", "business", "professional"]:
            result["calendar_assignment"] = "work"
        elif calendar_assignment in ["home", "personal", "private"]:
            result["calendar_assignment"] = "home"
        else:
            # Default to work calendar
            result["calendar_assignment"] = "work"
        
        # Add calendar ID
        calendar_title = result["calendar_assignment"]
        result["calendar_id"] = self.calendars.get(calendar_title)
        
        return result
    
    def get_calendar_id(self, calendar_title: str) -> Optional[str]:
        """Get calendar ID for a given title."""
        return self.calendars.get(calendar_title.lower())


# Example usage and testing
if __name__ == "__main__":
    try:
        decomposer = TaskDecomposer()
        
        # Test task decomposition
        task = "Build a mobile app for tracking fitness goals"
        deadline = datetime.now() + timedelta(days=14)
        
        result = decomposer.decompose_task(task, deadline)
        
        print("Task Decomposition Result:")
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
