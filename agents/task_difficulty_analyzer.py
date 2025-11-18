"""
Task Difficulty Analyzer Component - LLM-based classification of tasks and calendar assignment
"""
import json
import requests
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from llm_setup import get_llm_low_temp


class TaskDifficultyAnalysis(BaseModel):
    """Task difficulty analysis result model"""
    calendar: Optional[str] = None  # Calendar ID from CalBridge
    type: str  # "simple" or "complex"
    title: str  # Short imperative title
    duration: Optional[str] = None  # Passed through unchanged from TS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "calendar": self.calendar,
            "type": self.type,
            "title": self.title,
            "duration": self.duration
        }
    
    def __str__(self) -> str:
        return f"TaskDifficultyAnalysis(calendar='{self.calendar}', type='{self.type}', title='{self.title}', duration='{self.duration}')"


class TaskDifficultyAnalyzer:
    """LLM-based task difficulty analyzer for classifying tasks and assigning calendars"""
    
    def __init__(self, calbridge_base_url: str = "http://127.0.0.1:8765"):
        self.llm = get_llm_low_temp()  # Low temperature for deterministic JSON output
        self.calbridge_base_url = calbridge_base_url
        self.prompt_template = self._create_prompt_template()
    
    def _fetch_calendars(self) -> List[Dict[str, Any]]:
        """
        Fetch calendars from CalBridge API
        
        Returns:
            List of calendar dictionaries with id, title, allows_modifications
        """
        try:
            response = requests.get(f"{self.calbridge_base_url}/calendars", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Warning: Failed to fetch calendars from CalBridge: {e}")
            return []
    
    def _find_work_home_calendars(self, calendars: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        """
        Find Work and Home calendars from the list
        
        Args:
            calendars: List of calendar dictionaries from CalBridge
            
        Returns:
            Dictionary with 'work_id' and 'home_id' keys
        """
        work_id = None
        home_id = None
        
        # First pass: look for exact matches (case-insensitive)
        for cal in calendars:
            title = (cal.get('title', '') or '').strip().lower()
            is_writable = cal.get('allows_modifications', False)
            
            if not is_writable:
                continue
            
            if title == 'work' and work_id is None:
                work_id = cal.get('id')
            elif title == 'home' and home_id is None:
                home_id = cal.get('id')
        
        # Second pass: look for partial matches (if exact not found)
        for cal in calendars:
            title = (cal.get('title', '') or '').strip().lower()
            is_writable = cal.get('allows_modifications', False)
            
            if not is_writable:
                continue
            
            if work_id is None and 'work' in title:
                work_id = cal.get('id')
            elif home_id is None and 'home' in title:
                home_id = cal.get('id')
        
        return {'work_id': work_id, 'home_id': home_id}
    
    def _create_prompt_template(self) -> str:
        """Create the prompt template for task difficulty analysis"""
        return """
You are a Task Difficulty Analyzer that classifies tasks and assigns calendars.

**CRITICAL RULES:**
1. **Return STRICT JSON only** - no explanations, no markdown formatting
2. **Do NOT modify duration** - pass it through exactly as provided
3. **Type classification:**
   - If `duration != null` → type = "simple"
   - If `duration == null` AND task is atomic → type = "simple"
   - If `duration == null` AND task is multi-step/composite → type = "complex"
4. **Calendar selection:** Choose Work or Home based on keywords in the user query
5. **Title generation:** Short, imperative, concrete (3-7 words), verb + object format

## Type Classification Rules

### Simple (when duration == null):
- Single, atomic action finishable in one sitting
- Clear verb + object: "call mom", "send invoice", "book dentist", "pay rent"
- Quick work actions: "email NDA", "submit expense", "merge approved PR"
- Personal errands with narrow scope: "buy milk", "pick up package", "laundry"

### Complex (when duration == null):
- Multi-step phrasing: "plan", "research and write", "draft then revise"
- Composite deliverables: "proposal", "report", "deck", "architecture", "analysis"
- Coordination/dependencies: "with team", "get approvals", "collect feedback"
- Open-ended: "explore", "investigate", "prototype", "compare vendors"
- Broad scope: "organize files", "clean apartment", "refactor module", "prepare taxes"
- Time-horizon/meta: "this week/month/quarter", "roadmap", "milestones"

**Borderline?** If atomic → simple; if not clearly atomic → complex.

## Calendar Selection Rules

### Work keywords (case-insensitive):
client, manager, team, meeting, deck, proposal, report, PRD, sprint, code, repo, deploy, invoice, expense, contract, NDA, design, marketing, sales, finance, legal, roadmap, OKR

### Home keywords (case-insensitive):
mom, dad, family, friend, groceries, laundry, gym, workout, dentist, doctor, birthday, rent, clean, apartment, house, travel (personal), visa (personal), taxes (personal)

### Selection logic:
1. If UQ matches Work keywords → choose Work calendar
2. If UQ matches Home keywords → choose Home calendar
3. If matches both → prefer Work for professional deliverables (proposal/deck/report/meeting), else Home for people/errands/health
4. If only one calendar exists → use that one
5. If neither exists → return calendar: null

## Title Generation Rules
- Short, imperative, concrete (3-7 words)
- Format: verb + object
- Remove time/deadlines/duration and filler ("please", "ASAP")
- No emojis, minimal punctuation
- Examples: "Call mom", "Send invoice to Acme", "Draft project proposal", "Buy groceries"

## Output Format (STRICT JSON):
```json
{{
  "calendar": "<calendar_id>" | null,
  "type": "simple" | "complex",
  "title": "<short imperative title>",
  "duration": "<PT...>" | null
}}
```

**IMPORTANT:** 
- Return ONLY valid JSON. No explanations, no markdown formatting, just the JSON object.
- Duration must be IDENTICAL to the input duration (pass through unchanged).
- Calendar ID must be one of: {work_id} (Work) or {home_id} (Home), or null if neither exists.

## Examples:

1. UQ: "call mom tomorrow for 20 minutes"
   Duration: "PT20M"
   Calendars: Work={work_id}, Home={home_id}
   Output: {{"calendar":"{home_id}","type":"simple","title":"Call mom","duration":"PT20M"}}

2. UQ: "finish project proposal by Nov 15"
   Duration: null
   Calendars: Work={work_id}, Home={home_id}
   Output: {{"calendar":"{work_id}","type":"complex","title":"Draft project proposal","duration":null}}

3. UQ: "send the signed NDA to the client"
   Duration: null
   Calendars: Work={work_id}, Home={home_id}
   Output: {{"calendar":"{work_id}","type":"simple","title":"Send signed NDA","duration":null}}

4. UQ: "buy groceries and fruits"
   Duration: null
   Calendars: Work={work_id}, Home={home_id}
   Output: {{"calendar":"{home_id}","type":"simple","title":"Buy groceries","duration":null}}

5. UQ: "prepare onboarding plan for new hire"
   Duration: null
   Calendars: Work={work_id}, Home={home_id}
   Output: {{"calendar":"{work_id}","type":"complex","title":"Prepare onboarding plan","duration":null}}

## Current Context:
User Query: "{query}"
Duration: {duration}
Available Calendars:
- Work: {work_id}
- Home: {home_id}

Analyze the task and return JSON:
"""
    
    def analyze(self, query: str, duration: Optional[str] = None) -> TaskDifficultyAnalysis:
        """
        Analyze task difficulty and assign calendar
        
        Args:
            query: User query (UQ)
            duration: Duration from Time Standardizer (TS.duration) - "PT..." or null
            
        Returns:
            TaskDifficultyAnalysis object with calendar, type, title, duration
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Fetch calendars from CalBridge
        calendars = self._fetch_calendars()
        work_home_ids = self._find_work_home_calendars(calendars)
        
        work_id = work_home_ids.get('work_id')
        home_id = work_home_ids.get('home_id')
        
        # Format work_id and home_id for prompt (use "null" string if None)
        work_id_str = str(work_id) if work_id else "null"
        home_id_str = str(home_id) if home_id else "null"
        
        # Format duration for prompt (use "null" string if None)
        duration_str = str(duration) if duration is not None else "null"
        
        # Format the prompt
        prompt = self.prompt_template.format(
            query=query.strip(),
            duration=duration_str,
            work_id=work_id_str,
            home_id=home_id_str
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
                analysis_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{[^}]*\}', response_text)
                if json_match:
                    analysis_data = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from response: {response_text}")
            
            # Validate calendar ID
            calendar_id = analysis_data.get("calendar")
            if calendar_id and calendar_id not in [work_id, home_id]:
                # If LLM returned an invalid calendar ID, try to fix it
                # Check if it's a work or home task based on keywords
                query_lower = query.lower()
                work_keywords = ['client', 'manager', 'team', 'meeting', 'deck', 'proposal', 'report', 'prd', 'sprint', 'code', 'repo', 'deploy', 'invoice', 'expense', 'contract', 'nda', 'design', 'marketing', 'sales', 'finance', 'legal', 'roadmap', 'okr']
                home_keywords = ['mom', 'dad', 'family', 'friend', 'groceries', 'laundry', 'gym', 'workout', 'dentist', 'doctor', 'birthday', 'rent', 'clean', 'apartment', 'house']
                
                has_work = any(kw in query_lower for kw in work_keywords)
                has_home = any(kw in query_lower for kw in home_keywords)
                
                if has_work and work_id:
                    calendar_id = work_id
                elif has_home and home_id:
                    calendar_id = home_id
                elif work_id:  # Default to work if available
                    calendar_id = work_id
                elif home_id:  # Otherwise home if available
                    calendar_id = home_id
                else:
                    calendar_id = None
            
            # Validate and create TaskDifficultyAnalysis
            # CRITICAL RULE: If duration != null, type MUST be "simple"
            if duration is not None:
                task_type = "simple"  # Enforce: duration present → simple
            else:
                task_type = analysis_data.get("type", "complex")
                if task_type not in ["simple", "complex"]:
                    task_type = "complex"  # Default to complex if unclear
            
            # Ensure duration is passed through unchanged
            output_duration = duration  # Use the input duration, not what LLM returned
            
            return TaskDifficultyAnalysis(
                calendar=calendar_id,
                type=task_type,
                title=analysis_data.get("title", query.strip()[:50]),  # Fallback to truncated query
                duration=output_duration
            )
            
        except Exception as e:
            raise ValueError(f"Task difficulty analysis failed: {str(e)}")
    
    def analyze_safe(self, query: str, duration: Optional[str] = None) -> TaskDifficultyAnalysis:
        """
        Safe version of analyze that returns default values on failure
        
        Args:
            query: User query (UQ)
            duration: Duration from Time Standardizer (TS.duration)
            
        Returns:
            TaskDifficultyAnalysis object (with defaults if analysis fails)
        """
        try:
            return self.analyze(query, duration)
        except Exception as e:
            print(f"Warning: Task difficulty analysis failed for '{query}': {e}")
            # Return default analysis
            calendars = self._fetch_calendars()
            work_home_ids = self._find_work_home_calendars(calendars)
            default_calendar = work_home_ids.get('work_id') or work_home_ids.get('home_id')
            
            # Determine type based on duration
            task_type = "simple" if duration is not None else "complex"
            
            return TaskDifficultyAnalysis(
                calendar=default_calendar,
                type=task_type,
                title=query.strip()[:50],  # Fallback to truncated query
                duration=duration
            )


# Example usage
if __name__ == "__main__":
    analyzer = TaskDifficultyAnalyzer()
    
    # Test cases
    test_cases = [
        {
            "query": "call mom tomorrow for 20 minutes",
            "duration": "PT20M"
        },
        {
            "query": "finish project proposal by Nov 15",
            "duration": None
        },
        {
            "query": "send the signed NDA to the client",
            "duration": None
        },
        {
            "query": "buy groceries and fruits",
            "duration": None
        },
        {
            "query": "prepare onboarding plan for new hire",
            "duration": None
        }
    ]
    
    print("Testing Task Difficulty Analyzer:")
    for test_case in test_cases:
        try:
            result = analyzer.analyze_safe(test_case["query"], test_case["duration"])
            print(f"✅ Query: '{test_case['query']}'")
            print(f"   Duration: {test_case['duration']}")
            print(f"   Result: {result}")
            print()
        except Exception as e:
            print(f"❌ Query: '{test_case['query']}' -> Error: {e}")
            print()

