import requests
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime

from models import LLMDecompositionRequest, LLMDecompositionResponse, SubtaskCreate, TaskType

class LLMService:
    """Service for communicating with Ollama LLM."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "gemma3"):
        self.base_url = base_url
        self.model = model
        self.timeout = 120
    
    async def decompose_task(self, request: LLMDecompositionRequest) -> LLMDecompositionResponse:
        """Decompose a task using LLM."""
        try:
            # Build the prompt
            prompt = self._build_decomposition_prompt(request)
            
            # Call Ollama
            response = await self._call_ollama(prompt)
            
            # Parse the response
            decomposition = self._parse_decomposition_response(response)
            
            return decomposition
            
        except Exception as e:
            raise Exception(f"LLM decomposition failed: {e}")
    
    def _build_decomposition_prompt(self, request: LLMDecompositionRequest) -> str:
        """Build the prompt for task decomposition."""
        deadline_str = request.deadline.strftime("%Y-%m-%d %H:%M") if request.deadline else "No deadline specified"
        calendar_str = request.calendar_target.value if request.calendar_target else "Not specified"
        
        prompt = f"""You are a task planning assistant. Analyze the following task and decide if it needs subtasks.

Task: {request.title}
Description: {request.description or "No description provided"}
Deadline: {deadline_str}
Calendar: {calendar_str}

Rules:
- Simple tasks (calls, single meetings, quick errands) should NOT have subtasks
- Complex tasks should be broken into 2-10 subtasks based on complexity
- Each subtask should be a distinct, actionable step
- Consider logical ordering and dependencies
- Provide realistic time estimates (be conservative)
- Task types: deep_work, meeting, quick_task, research

Return ONLY valid JSON:
{{
  "needs_subtasks": boolean,
  "estimated_minutes": integer,  // if needs_subtasks=false, total time for main task
  "task_type": "deep_work|meeting|quick_task|research",
  "subtasks": [  // empty array if needs_subtasks=false
    {{
      "title": "string",
      "estimated_minutes": integer,
      "order_index": integer,
      "task_type": "deep_work|meeting|quick_task|research"
    }}
  ],
  "reasoning": "brief explanation of decomposition decision"
}}"""
        
        return prompt
    
    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API."""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful task planning assistant. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "options": {"temperature": 0.1},
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            return data["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API call failed: {e}")
    
    def _parse_decomposition_response(self, response: str) -> LLMDecompositionResponse:
        """Parse the LLM response into structured data."""
        try:
            # Extract JSON from response (handle code fences, etc.)
            json_str = self._extract_json_from_response(response)
            
            # Parse JSON
            data = json.loads(json_str)
            
            # Validate and convert to response model
            needs_subtasks = bool(data.get("needs_subtasks", True))
            estimated_minutes = int(data.get("estimated_minutes", 30))
            task_type = TaskType(data.get("task_type", "quick_task"))
            reasoning = str(data.get("reasoning", "No reasoning provided"))
            
            # Parse subtasks
            subtasks = []
            if needs_subtasks and "subtasks" in data:
                for i, subtask_data in enumerate(data["subtasks"]):
                    subtask = SubtaskCreate(
                        title=str(subtask_data.get("title", f"Subtask {i+1}")),
                        estimated_minutes=int(subtask_data.get("estimated_minutes", 30)),
                        order_index=int(subtask_data.get("order_index", i)),
                        task_type=TaskType(subtask_data.get("task_type", "quick_task"))
                    )
                    subtasks.append(subtask)
            
            return LLMDecompositionResponse(
                needs_subtasks=needs_subtasks,
                estimated_minutes=estimated_minutes,
                task_type=task_type,
                subtasks=subtasks,
                reasoning=reasoning
            )
            
        except Exception as e:
            # Fallback to simple task if parsing fails
            return LLMDecompositionResponse(
                needs_subtasks=False,
                estimated_minutes=30,
                task_type=TaskType.QUICK_TASK,
                subtasks=[],
                reasoning=f"Parsing failed, defaulting to simple task: {e}"
            )
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from LLM response, handling various formats."""
        response = response.strip()
        
        # If it's already pure JSON, try directly
        if response.startswith("{"):
            # Find the matching closing brace
            depth = 0
            for i, char in enumerate(response):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return response[:i+1]
        
        # Try code fence ```json ... ```
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, flags=re.DOTALL)
        if fence_match:
            return fence_match.group(1)
        
        # Try to find first {...} block
        block_match = re.search(r"(\{.*\})", response, flags=re.DOTALL)
        if block_match:
            return block_match.group(1)
        
        raise ValueError("No JSON object found in response")
    
    async def improve_estimates(self, task_type: str, estimated_minutes: int, actual_minutes: int) -> int:
        """Improve time estimates based on historical data."""
        # Simple learning algorithm - can be enhanced with more sophisticated ML
        if actual_minutes > 0:
            # Calculate adjustment factor
            factor = actual_minutes / estimated_minutes if estimated_minutes > 0 else 1.0
            
            # Apply smoothing (weighted average with historical data)
            # For now, just return a simple adjustment
            if factor > 1.5:  # Significantly underestimated
                return int(estimated_minutes * 1.2)
            elif factor < 0.7:  # Significantly overestimated
                return int(estimated_minutes * 0.9)
            else:
                return estimated_minutes
        
        return estimated_minutes
    
    async def suggest_task_type(self, title: str, description: Optional[str] = None) -> TaskType:
        """Suggest task type based on title and description."""
        text = f"{title} {description or ''}".lower()
        
        # Simple keyword-based classification
        if any(word in text for word in ["call", "meeting", "zoom", "teams", "discuss", "chat"]):
            return TaskType.MEETING
        elif any(word in text for word in ["research", "study", "learn", "investigate", "analyze"]):
            return TaskType.RESEARCH
        elif any(word in text for word in ["write", "code", "design", "create", "build", "develop"]):
            return TaskType.DEEP_WORK
        else:
            return TaskType.QUICK_TASK
