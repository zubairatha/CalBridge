"""
LLM Task Decomposer Agent

This module provides a smart LLM-based task decomposer that takes a task description
along with a deadline and intelligently:
1. Decides which calendar to add the event to (Work/Home)
2. Breaks the event down into 2-5 subtasks with time allotments
3. Ensures no subtask exceeds 3 hours (180 minutes)
4. Returns subtasks with time in minutes, or None if no subtasks needed
"""

import json
import re
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Subtask:
    """Represents a subtask with its time allocation"""
    title: str
    duration_minutes: int
    description: Optional[str] = None


@dataclass
class TaskDecomposition:
    """Result of task decomposition"""
    calendar_type: str  # "Work" or "Home"
    subtasks: Optional[List[Subtask]] = None
    total_duration_minutes: int = 0
    reasoning: Optional[str] = None


class LLMTaskDecomposer:
    """
    Smart LLM decomposer agent using Ollama Llama3
    
    Takes a task description and deadline, then uses LLM to:
    - Determine appropriate calendar (Work/Home)
    - Break down into subtasks if needed
    - Allocate time for each subtask (max 3 hours each)
    """
    
    def __init__(self, 
                 ollama_base: str = "http://127.0.0.1:11434",
                 model: str = "llama3",
                 calendar_config_path: Optional[str] = None):
        """
        Initialize the LLM Task Decomposer
        
        Args:
            ollama_base: Base URL for Ollama API
            model: Model name to use (default: llama3)
            calendar_config_path: Path to calendar configuration
        """
        self.ollama_base = ollama_base
        self.model = model
        
        # Load calendar configuration
        if calendar_config_path is None:
            calendar_config_path = Path(__file__).parent.parent / "config" / "calendars.json"
        
        self.calendar_config = self._load_calendar_config(calendar_config_path)
    
    def _load_calendar_config(self, config_path: str) -> Dict[str, Any]:
        """Load calendar configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback configuration
            return {
                "default_work_title": "Work",
                "default_home_title": "Home",
                "calendars": [
                    {"id": "work_id", "title": "Work", "writable": True},
                    {"id": "home_id", "title": "Home", "writable": True}
                ]
            }
    
    def _get_system_prompt(self, deadline: str) -> str:
        """Generate system prompt for the LLM"""
        return f"""You are a task decomposition agent. Your ONLY job is to analyze a task and return JSON.

CRITICAL: Return ONLY valid JSON. Do not write essays, papers, or any other text.

Rules:
1. Choose calendar: "Work" for professional tasks, "Home" for personal tasks
2. If task is simple (like "Call mom"), set subtasks to null
3. If complex, break into 2-5 subtasks, each 5-180 minutes
4. Each subtask title should be short and actionable

DEADLINE: {deadline}

Return ONLY this JSON format (no other text):
{{
  "calendar_type": "Work",
  "subtasks": [
    {{
      "title": "Research phase",
      "duration_minutes": 120
    }},
    {{
      "title": "Writing phase", 
      "duration_minutes": 180
    }}
  ],
  "total_duration_minutes": 300,
  "reasoning": "Complex task needs decomposition"
}}

For simple tasks, use:
{{
  "calendar_type": "Home",
  "subtasks": null,
  "total_duration_minutes": 30,
  "reasoning": "Simple task, no decomposition needed"
}}"""

    def _call_ollama(self, task_description: str, deadline: str) -> Dict[str, Any]:
        """Call Ollama API to decompose the task"""
        system_prompt = self._get_system_prompt(deadline)
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task_description}
            ],
            "options": {"temperature": 0.1},
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.ollama_base}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            # Extract content from response
            data = response.json()
            content = data.get("message", {}).get("content", "")
            
            # Extract JSON from response
            json_str = self._extract_json(content)
            return json.loads(json_str)
            
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to call Ollama API: {e}")
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Failed to parse LLM response: {e}")
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response text"""
        text = text.strip()
        
        # Try to find JSON object
        if text.startswith("{"):
            # Find matching closing brace
            depth = 0
            for i, char in enumerate(text):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return text[:i+1]
        
        # Try code fence
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if fence_match:
            return fence_match.group(1)
        
        # Fallback: find first {...} block
        match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if match:
            return match.group(1)
        
        raise ValueError("No JSON object found in LLM response")
    
    def _validate_decomposition(self, result: Dict[str, Any]) -> None:
        """Validate the decomposition result"""
        # Check required fields
        if "calendar_type" not in result:
            raise ValueError("Missing calendar_type in decomposition result")
        
        if result["calendar_type"] not in ["Work", "Home"]:
            raise ValueError("calendar_type must be 'Work' or 'Home'")
        
        # Validate subtasks if present
        if result.get("subtasks") is not None:
            subtasks = result["subtasks"]
            if not isinstance(subtasks, list):
                raise ValueError("subtasks must be a list or null")
            
            if len(subtasks) < 2 or len(subtasks) > 5:
                raise ValueError("subtasks must be 2-5 items or null")
            
            for i, subtask in enumerate(subtasks):
                if not isinstance(subtask, dict):
                    raise ValueError(f"subtask {i} must be a dictionary")
                
                if "title" not in subtask or "duration_minutes" not in subtask:
                    raise ValueError(f"subtask {i} missing required fields")
                
                duration = subtask["duration_minutes"]
                if not isinstance(duration, int) or duration < 5 or duration > 180:
                    raise ValueError(f"subtask {i} duration must be 5-180 minutes")
    
    def decompose_task(self, task_description: str, deadline: str) -> TaskDecomposition:
        """
        Decompose a task into subtasks with time allocation
        
        Args:
            task_description: Description of the task to decompose
            deadline: ISO format deadline string
            
        Returns:
            TaskDecomposition object with calendar type and subtasks
        """
        try:
            # Call LLM to decompose task
            result = self._call_ollama(task_description, deadline)
            
            # Validate result
            self._validate_decomposition(result)
            
            # Convert to TaskDecomposition object
            subtasks = None
            if result.get("subtasks"):
                subtasks = [
                    Subtask(
                        title=st["title"],
                        duration_minutes=st["duration_minutes"],
                        description=st.get("description")
                    )
                    for st in result["subtasks"]
                ]
            
            return TaskDecomposition(
                calendar_type=result["calendar_type"],
                subtasks=subtasks,
                total_duration_minutes=result.get("total_duration_minutes", 0),
                reasoning=result.get("reasoning")
            )
            
        except Exception as e:
            raise RuntimeError(f"Task decomposition failed: {e}")
    
    def get_calendar_id(self, calendar_type: str) -> Optional[str]:
        """
        Get calendar ID for the given calendar type
        
        Args:
            calendar_type: "Work" or "Home"
            
        Returns:
            Calendar ID or None if not found
        """
        calendars = self.calendar_config.get("calendars", [])
        for cal in calendars:
            if cal.get("title", "").lower() == calendar_type.lower() and cal.get("writable", False):
                return cal.get("id")
        return None


def main():
    """Test the LLM Task Decomposer"""
    decomposer = LLMTaskDecomposer()
    
    # Test cases
    test_cases = [
        ("Write a research paper on AI ethics", "2025-11-15T23:59:00"),
        ("Call mom for 15 minutes", "2025-10-20T18:00:00"),
        ("Plan company retreat", "2025-12-01T23:59:00"),
        ("Buy groceries", "2025-10-15T20:00:00")
    ]
    
    for task, deadline in test_cases:
        print(f"\n=== Task: {task} ===")
        print(f"Deadline: {deadline}")
        
        try:
            result = decomposer.decompose_task(task, deadline)
            print(f"Calendar: {result.calendar_type}")
            print(f"Total Duration: {result.total_duration_minutes} minutes")
            print(f"Reasoning: {result.reasoning}")
            
            if result.subtasks:
                print("Subtasks:")
                for i, subtask in enumerate(result.subtasks, 1):
                    print(f"  {i}. {subtask.title} ({subtask.duration_minutes} min)")
                    if subtask.description:
                        print(f"     {subtask.description}")
            else:
                print("No subtasks needed")
                
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
