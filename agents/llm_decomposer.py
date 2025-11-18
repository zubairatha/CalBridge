"""
LLM Decomposer Component - Decomposes complex tasks into subtasks
"""
import json
import re
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from llm_setup import get_llm_decomposer


class Subtask(BaseModel):
    """Subtask model"""
    title: str
    duration: str  # ISO-8601 format (PT...)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "title": self.title,
            "duration": self.duration
        }


class TaskDecomposition(BaseModel):
    """Task decomposition result model"""
    calendar: Optional[str]  # Calendar ID from TD
    type: str  # "complex"
    title: str  # Task title from TD
    subtasks: List[Subtask]  # List of subtasks
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "calendar": self.calendar,
            "type": self.type,
            "title": self.title,
            "subtasks": [st.to_dict() for st in self.subtasks]
        }
    
    def __str__(self) -> str:
        subtasks_str = ", ".join([f"{st.title} ({st.duration})" for st in self.subtasks])
        return f"TaskDecomposition(calendar='{self.calendar}', type='{self.type}', title='{self.title}', subtasks=[{subtasks_str}])"


class LLMDecomposer:
    """LLM-based decomposer for complex tasks"""
    
    def __init__(self):
        self.llm = get_llm_decomposer()
        self.prompt_template = self._create_prompt_template()
    
    def _validate_iso8601_duration(self, duration: str) -> bool:
        """
        Validate ISO-8601 duration format (PT#H#M)
        
        Args:
            duration: Duration string to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Pattern: PT followed by optional hours (H) and/or minutes (M)
        # Examples: PT30M, PT1H, PT2H30M, PT3H
        pattern = r'^PT(\d+H)?(\d+M)?$'
        match = re.match(pattern, duration.upper())
        if not match:
            return False
        
        # Extract hours and minutes
        hours_part = match.group(1)
        minutes_part = match.group(2)
        
        # Must have at least one component
        if not hours_part and not minutes_part:
            return False
        
        # Parse and validate hours (≤ 3)
        if hours_part:
            hours = int(hours_part[:-1])
            if hours > 3:
                return False
        
        # Parse and validate minutes (if hours=3, minutes must be 0)
        if minutes_part:
            minutes = int(minutes_part[:-1])
            if hours_part:
                hours = int(hours_part[:-1])
                if hours == 3 and minutes > 0:
                    return False
        
        return True
    
    def _parse_duration_to_minutes(self, duration: str) -> int:
        """
        Parse ISO-8601 duration to total minutes
        
        Args:
            duration: ISO-8601 duration string (PT#H#M)
            
        Returns:
            Total minutes
        """
        duration = duration.upper()
        hours = 0
        minutes = 0
        
        hours_match = re.search(r'(\d+)H', duration)
        if hours_match:
            hours = int(hours_match.group(1))
        
        minutes_match = re.search(r'(\d+)M', duration)
        if minutes_match:
            minutes = int(minutes_match.group(1))
        
        return hours * 60 + minutes
    
    def _cap_duration_to_pt3h(self, duration: str) -> str:
        """
        Cap duration to PT3H maximum
        
        Args:
            duration: ISO-8601 duration string
            
        Returns:
            Capped duration (max PT3H)
        """
        total_minutes = self._parse_duration_to_minutes(duration)
        max_minutes = 3 * 60  # 3 hours
        
        if total_minutes <= max_minutes:
            return duration
        
        # Cap to PT3H
        return "PT3H"
    
    def _validate_and_fix_subtasks(self, subtasks: List[Dict[str, Any]]) -> List[Subtask]:
        """
        Validate and fix subtasks according to constraints
        
        Args:
            subtasks: List of subtask dictionaries from LLM
            
        Returns:
            List of validated Subtask objects
        """
        validated = []
        
        for st in subtasks:
            title = st.get("title", "").strip()
            duration = st.get("duration", "").strip()
            
            # Validate title
            if not title or len(title) < 3:
                continue  # Skip invalid titles
            
            # Validate and fix duration
            if not self._validate_iso8601_duration(duration):
                # Try to fix common issues
                duration_upper = duration.upper()
                if duration_upper.startswith("PT"):
                    # Try to cap it
                    duration = self._cap_duration_to_pt3h(duration_upper)
                else:
                    # Invalid format, skip this subtask
                    continue
            
            # Cap duration to PT3H
            duration = self._cap_duration_to_pt3h(duration)
            
            validated.append(Subtask(title=title, duration=duration))
        
        # Ensure we have at least 2 subtasks
        if len(validated) < 2:
            # Create default subtasks if needed
            validated = [
                Subtask(title="Plan and outline", duration="PT45M"),
                Subtask(title="Execute and finalize", duration="PT1H")
            ]
        
        # Limit to 5 subtasks
        if len(validated) > 5:
            validated = validated[:5]
        
        return validated
    
    def _create_prompt_template(self) -> str:
        """Create the prompt template for task decomposition"""
        return """
You are an LLM Decomposer that breaks down complex tasks into clear, schedulable subtasks.

**CRITICAL RULES:**
1. **Return STRICT JSON only** - no explanations, no markdown formatting
2. **2-5 subtasks** maximum (minimum 2 recommended)
3. **Each duration must be ≤ PT3H** (ISO-8601 format)
4. **No dates/times** in titles - only task descriptions
5. **Order subtasks** in execution order (first to last)

## Hard Constraints

* **Max subtasks:** 5 (min 2 recommended)
* **Per-subtask duration cap:** ≤ PT3H
* **Duration format:** ISO-8601 only (`PT30M`, `PT1H`, `PT2H30M`, `PT3H`)
* **No dates/times** in titles
* **No sub-subtasks, no bullets, no prose** - JSON only

## Decomposition Rules

### 1) Structure into phases
Choose 2-5 phases that fit:
* **Plan / Research / Gather** (inputs, references, data)
* **Outline / Draft / Design** (structure, skeleton, wireframe)
* **Build / Write / Implement** (main execution)
* **Review / Test / Polish** (self-review, QA, revise)
* **Finalize / Package / Submit** (export, share, send)

### 2) Titles
* **Imperative** and **outcome-focused** (3-7 words)
* **CRITICAL: Include parent task context** - Each subtask title should reference the parent task in parentheses at the end
* Extract a short, relevant phrase from the parent task title (e.g., "Japan trip", "project proposal", "onboarding plan")
* Format: "Action description (parent context)"
* Include the object; avoid filler ("please", "ASAP")
* Examples: "Research background sources (project proposal)", "List must-see cities and dates (Japan trip)", "Draft proposal outline (project proposal)"

### 3) Durations
* Default to **PT45M–PT1H30M** per subtask unless clearly needs more
* Never exceed **PT3H** for any subtask
* Prefer **varied durations** that match the step's heft
* Use sensible granularity (PT15M, PT30M, PT45M, PT1H, PT1H30M, PT2H, PT2H30M, PT3H)

### 4) Order
* Output subtasks in **execution order** (first to last)
* Each subtask should be independently schedulable

### 5) Domain sensitivity
* **Work deliverables**: include at least one review/refinement step
* **Home/personal complex**: include "gather info," "compare options," "decide & book/prepare," "review & finalize"

## Output Format (STRICT JSON):
```json
{{
  "subtasks": [
    {{"title": "...", "duration": "PT..."}},
    ...
  ]
}}
```

## Examples:

1. **Work — "Draft project proposal"**
```json
{{
  "subtasks": [
    {{"title":"Research background and inputs (project proposal)","duration":"PT1H30M"}},
    {{"title":"Create proposal outline (project proposal)","duration":"PT45M"}},
    {{"title":"Write key sections (project proposal)","duration":"PT2H"}},
    {{"title":"Self-review and revise (project proposal)","duration":"PT1H"}},
    {{"title":"Export and share proposal (project proposal)","duration":"PT30M"}}
  ]
}}
```

2. **Home — "Plan 5-day Japan trip"**
```json
{{
  "subtasks": [
    {{"title":"List must-see cities and dates (Japan trip)","duration":"PT1H"}},
    {{"title":"Compare flights and book (Japan trip)","duration":"PT2H"}},
    {{"title":"Draft day-by-day itinerary (Japan trip)","duration":"PT1H30M"}},
    {{"title":"Book lodging and passes (Japan trip)","duration":"PT2H"}},
    {{"title":"Finalize budget and checklist (Japan trip)","duration":"PT45M"}}
  ]
}}
```

3. **Work — "Prepare onboarding plan"**
```json
{{
  "subtasks": [
    {{"title":"Gather role requirements (onboarding plan)","duration":"PT1H"}},
    {{"title":"Draft 30-60-90 plan (onboarding plan)","duration":"PT1H30M"}},
    {{"title":"Create learning resources list (onboarding plan)","duration":"PT1H"}},
    {{"title":"Review and refine with notes (onboarding plan)","duration":"PT1H"}},
    {{"title":"Package and share plan (onboarding plan)","duration":"PT30M"}}
  ]
}}
```

## Task to Decompose:
Title: "{title}"
Type: {type}
Calendar: {calendar}

Decompose this complex task into 2-5 subtasks with ISO-8601 durations (max PT3H each):

**CRITICAL INSTRUCTIONS:**
1. Extract a short, relevant phrase from the parent task title (e.g., if title is "Plan 5-day Japan trip", use "Japan trip")
2. Include this context phrase in parentheses at the end of each subtask title
3. Format each subtask title as: "Action description (context phrase)"
4. Make sure all subtask titles reference the parent task context

**IMPORTANT:** Return ONLY valid JSON. No explanations, no markdown formatting, just the JSON object with "subtasks" array.
"""
    
    def decompose(self, td_output: Dict[str, Any]) -> TaskDecomposition:
        """
        Decompose a complex task into subtasks
        
        Args:
            td_output: Task Difficulty Analysis output (must have type="complex")
            
        Returns:
            TaskDecomposition object with subtasks
        """
        # Validate input
        if not td_output:
            raise ValueError("TD output cannot be empty")
        
        task_type = td_output.get("type", "")
        if task_type != "complex":
            raise ValueError(f"LLM Decomposer only works with complex tasks, got type: '{task_type}'")
        
        title = td_output.get("title", "")
        if not title:
            raise ValueError("Task title cannot be empty")
        
        calendar = td_output.get("calendar")
        
        # Format the prompt
        prompt = self.prompt_template.format(
            title=title,
            type=task_type,
            calendar=calendar or "N/A"
        )
        
        try:
            # Get LLM response
            response = self.llm.invoke(prompt)
            
            # Parse JSON response
            response_text = response.strip()
            
            # Clean up response if it has markdown formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                decomposition_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract JSON from the response
                # More robust pattern that handles nested structures
                json_match = re.search(r'\{[^{}]*"subtasks"\s*:\s*\[[^\]]*\][^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        decomposition_data = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        # Try a simpler extraction
                        import json as json_module
                        # Find the subtasks array
                        subtasks_match = re.search(r'"subtasks"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
                        if subtasks_match:
                            # Try to reconstruct JSON
                            subtasks_str = subtasks_match.group(1)
                            decomposition_data = {"subtasks": []}
                            # This is a fallback - in practice, we should fix the LLM output
                            raise ValueError(f"Could not parse JSON from response: {response_text}")
                        else:
                            raise ValueError(f"Could not parse JSON from response: {response_text}")
                else:
                    raise ValueError(f"Could not parse JSON from response: {response_text}")
            
            # Extract subtasks
            subtasks_raw = decomposition_data.get("subtasks", [])
            if not subtasks_raw:
                raise ValueError("LLM returned no subtasks")
            
            # Validate and fix subtasks
            validated_subtasks = self._validate_and_fix_subtasks(subtasks_raw)
            
            # Create final decomposition
            return TaskDecomposition(
                calendar=calendar,
                type=task_type,
                title=title,
                subtasks=validated_subtasks
            )
            
        except Exception as e:
            raise ValueError(f"Task decomposition failed: {str(e)}")
    
    def decompose_safe(self, td_output: Dict[str, Any]) -> TaskDecomposition:
        """
        Safe version of decompose that returns default decomposition on failure
        
        Args:
            td_output: Task Difficulty Analysis output
            
        Returns:
            TaskDecomposition object (with defaults if decomposition fails)
        """
        try:
            return self.decompose(td_output)
        except Exception as e:
            print(f"Warning: Task decomposition failed: {e}")
            # Return default decomposition
            title = td_output.get("title", "Complex task")
            calendar = td_output.get("calendar")
            
            default_subtasks = [
                Subtask(title="Plan and outline", duration="PT45M"),
                Subtask(title="Execute and finalize", duration="PT1H")
            ]
            
            return TaskDecomposition(
                calendar=calendar,
                type="complex",
                title=title,
                subtasks=default_subtasks
            )


# Example usage
if __name__ == "__main__":
    decomposer = LLMDecomposer()
    
    # Test cases from the spec
    test_cases = [
        {
            "calendar": "work_1",
            "type": "complex",
            "title": "Draft project proposal",
            "duration": None
        },
        {
            "calendar": "home_1",
            "type": "complex",
            "title": "Plan 5-day Japan trip",
            "duration": None
        },
        {
            "calendar": "work_1",
            "type": "complex",
            "title": "Prepare onboarding plan",
            "duration": None
        }
    ]
    
    print("Testing LLM Decomposer:")
    for test_case in test_cases:
        try:
            result = decomposer.decompose_safe(test_case)
            print(f"✅ '{test_case['title']}' -> {len(result.subtasks)} subtasks")
            for i, st in enumerate(result.subtasks, 1):
                print(f"   {i}. {st.title} ({st.duration})")
            print()
        except Exception as e:
            print(f"❌ '{test_case['title']}' -> Error: {e}")
            print()

