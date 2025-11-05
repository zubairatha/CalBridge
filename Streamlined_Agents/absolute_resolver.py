"""
Absolute Resolver Component - LLM-based resolution of time slots to absolute dates/times
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
from llm_setup import get_llm


class AbsoluteResolution(BaseModel):
    """Absolute resolution result model"""
    start_text: str
    end_text: str
    duration: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "start_text": self.start_text,
            "end_text": self.end_text,
            "duration": self.duration
        }
    
    def __str__(self) -> str:
        return f"AbsoluteResolution(start_text='{self.start_text}', end_text='{self.end_text}', duration='{self.duration}')"


class AbsoluteResolver:
    """LLM-based absolute resolver for time slots"""
    
    def __init__(self):
        self.llm = get_llm()
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> str:
        """Create the prompt template for absolute resolution"""
        return """
You are an Absolute Resolver that converts time slots to absolute dates/times.

**CRITICAL RULE: ONLY resolve time information that is EXPLICITLY provided. Do NOT infer, assume, or hallucinate time information.**

**DURATION RULE: NEVER use duration to calculate or modify start/end times. Duration is metadata only - copy it AS-IS.**

**CRITICAL: Use the provided context (NOW_ISO, END_OF_TODAY, etc.) - do NOT overfit to examples in this prompt.**

## Input Requirements:
- NOW_ISO: Current time in ISO format with timezone offset
- TIMEZONE: IANA timezone (e.g., America/New_York)
- TODAY_HUMAN: Human-readable today's date
- END_OF_TODAY: End of today (11:59 pm)
- END_OF_WEEK: End of current week (Sunday 11:59 pm)
- END_OF_MONTH: End of current month (EOM 11:59 pm)
- NEXT_MONDAY: Next Monday 09:00 am anchor
- NEXT_OCCURRENCES: Next occurrences of weekdays
- Slots: JSON with start_text, end_text, duration

## Output Format (STRICT JSON):
```json
{{
  "start_text": "Month DD, YYYY HH:MM am/pm",
  "end_text": "Month DD, YYYY HH:MM am/pm", 
  "duration": "2h" | "45m" | null
}}
```

**Use EXACT canonical format: "Month DD, YYYY HH:MM am/pm"**
**Copy duration as-is (do not convert or use it to move start/end)**

## Core Principles:
1. **Determinism:** Always produce one specific calendar date/time for both start_text and end_text
2. **Duration is metadata:** Never shift start_text or end_text because of duration
3. **Safety:** Always ensure start ≤ end. If not, repair deterministically
4. **End time for start-only:** When only start_text is provided, end should be 11:59 pm on the SAME DATE as the resolved start

## Resolution Rules:

### 1) Both start_text and end_text present:
- Treat as window with start anchor and end anchor
- Resolve each side to absolute datetime
- If one/both sides specify only times (no date), attach to same resolved date
- **Cross-midnight rule:** if end < start, move end forward 1 day
- If end phrase is weekday and still lands before start, move to next occurrence

### 2) Only end_text present (deadline):
- Start = NOW_ISO expressed in canonical format
- End = resolved deadline; if no time, set to 11:59 pm on that date
- If end < start, move end to next plausible occurrence

### 3) Only start_text present (start-only):
- Start = resolved start anchor
- End = 11:59 pm on the SAME DATE as the resolved start
- If start time is < today, push both start and end to next day
- If that would be < start, set end = 11:59 pm on start's date

### 4) Neither start_text nor end_text present (duration only or no time info):
- Start = NOW_ISO expressed in canonical format
- End = END_OF_TODAY (based on current context)
- This applies when ONLY duration is present OR when no time information exists

## Phrase Resolution Details:

### Weekday Resolution:
- Unqualified weekday (e.g., "Friday"): choose next occurrence (or today if hasn't passed)
- If today is that weekday and referenced time window has already passed, use same weekday next week
- "this Friday" → Friday of current week
- "next Friday" → Friday of following week

### Bare Times (no date):
- If time today is after or equal to NOW, schedule for today
- If time today is already past, schedule for tomorrow
- When both sides are bare times → put both on same inferred date

### Vague Periods (default anchors):
- morning → 09:00
- afternoon → 13:00
- evening → 18:00
- tonight → 20:00
- noon → 12:00
- midnight → 00:00
- tomorrow (without time) → 12:00 am (midnight) of next day

### Midnight Disambiguation:
- "midnight Friday" → 00:00 at start of Friday
- "Friday midnight" → 00:00 at start of Saturday

### Special Cases:
- "next week" (as start-only) → NEXT_MONDAY 09:00 am
- "end of week" (deadline) → END_OF_WEEK 11:59 pm
- "by EOM" / "end of month" (deadline) → END_OF_MONTH 11:59 pm

## Safety & Repairs:
- Always ensure start ≤ end
- If violated after resolution, set end = 11:59 pm on start's date
- Do not invent times other than specified anchors

## Examples (assume NOW = 2025-10-21T15:00:00-04:00, TZ = America/New_York):

**Deadline only:**
Slots: {{"start_text":null,"end_text":"Nov 15","duration":"2h"}}
Output: {{"start_text":"October 21, 2025 03:00 pm","end_text":"November 15, 2025 11:59 pm","duration":"2h"}}
Note: start_text is set to NOW_ISO

**Start-only**
Slots: {{"start_text":"tomorrow","end_text":null,"duration":"30m"}}
Output: {{"start_text":"October 22, 2025 12:00 am","end_text":"October 22, 2025 11:59 pm","duration":"30m"}}
note: tomorrow so 12am of next day

Slots: {{"start_text":"tomorrow morning","end_text":null,"duration":null}}
Output: {{"start_text":"October 22, 2025 09:00 am","end_text":"October 22, 2025 11:59 pm","duration":null}}
note: tomorrow morning so 9am of next day

**Explicit times on weekday:**
Slots: {{"start_text":"Friday 2pm","end_text":"Friday 4pm","duration":"30m"}}
Output: {{"start_text":"October 24, 2025 02:00 pm","end_text":"October 24, 2025 04:00 pm","duration":"30m"}}

**Range with times:**
Slots: {{"start_text":"9am","end_text":"5pm","duration":null}}
Output: {{"start_text":"October 21, 2025 09:00 am","end_text":"October 21, 2025 05:00 pm","duration":null}}

**Next week start:**
Slots: {{"start_text":"next week","end_text":null,"duration":"1h"}}
Output: {{"start_text":"October 27, 2025 12:00 am","end_text":"October 27, 2025 11:59 pm","duration":"1h"}}
note: next week so 12am of next_monday

**End of month deadline:**
Slots: {{"start_text":null,"end_text":"EOM","duration":"2h"}}
Output: {{"start_text":"October 21, 2025 03:00 pm","end_text":"October 31, 2025 11:59 pm","duration":"2h"}}

**No time information:**
Slots: {{"start_text":null,"end_text":null,"duration":null}}
Output: {{"start_text":"October 21, 2025 03:00 pm","end_text":"October 21, 2025 11:59 pm","duration":null}}

**Duration only - CRITICAL EXAMPLE:**
Slots: {{"start_text":null,"end_text":null,"duration":"2 hours"}}
Output: {{"start_text":"October 21, 2025 03:00 pm","end_text":"October 21, 2025 11:59 pm","duration":"2 hours"}}
Note: Duration is ignored for start/end calculation. Always use (NOW, END_OF_TODAY)

**Start with duration - CORRECT behavior:**
Slots: {{"start_text":"tonight","end_text":null,"duration":"2 hours"}}
Output: {{"start_text":"October 21, 2025 08:00 pm","end_text":"October 21, 2025 11:59 pm","duration":"2 hours"}}
Note: End time is 11:59 pm on same date as start, NOT start + duration

**IMPORTANT:** Return ONLY valid JSON. No explanations, no markdown formatting, just the JSON object.

## Duration handling:
* Copy `duration` straight through AS-IS.
* Do **not** compute `start = end − duration` or `end = start + duration`. 
* Do **not** process or modify duration values.
* Do **not** use duration to calculate or adjust start/end times.
* Duration is metadata only - pass it through unchanged.
* **NEVER** add duration to start time to get end time.
* **NEVER** subtract duration from end time to get start time.
* **IGNORE** duration when calculating start/end times.

## CRITICAL: Duration-only cases (no start_text, no end_text):
* When ONLY duration is present: Start = NOW_ISO, End = END_OF_TODAY
* Do NOT use duration to calculate anything
* Do NOT infer start/end times from duration
* Always use (NOW, END_OF_TODAY) for duration-only cases
* **WARNING: Do NOT add duration to start time to get end time**
* **WARNING: Do NOT subtract duration from end time to get start time**
* **WARNING: Duration is IGNORED for all calculations**

## Current Context:
NOW_ISO: {now_iso}
TIMEZONE: {timezone}
TODAY_HUMAN: {today_human}
END_OF_TODAY: {end_of_today}
END_OF_WEEK: {end_of_week}
END_OF_MONTH: {end_of_month}
NEXT_MONDAY: {next_monday}
NEXT_OCCURRENCES: {next_occurrences}

## Slots to Resolve:
{slots_json}

Resolve to absolute dates/times:

**FINAL REMINDER: If slots have duration but no start/end, use (NOW_ISO, END_OF_TODAY) and copy duration as-is. Do NOT calculate anything from duration.**
"""
    
    def resolve_absolute(self, slots: Dict[str, Any], context: Dict[str, Any]) -> AbsoluteResolution:
        """
        Resolve time slots to absolute dates/times
        
        Args:
            slots: Dictionary with start_text, end_text, duration
            context: Context information (NOW_ISO, TIMEZONE, helpers, etc.)
            
        Returns:
            AbsoluteResolution object with resolved absolute times
        """
        if not slots:
            raise ValueError("Slots cannot be empty")
        
        # Format the prompt
        prompt = self.prompt_template.format(
            now_iso=context.get('NOW_ISO', ''),
            timezone=context.get('TIMEZONE', ''),
            today_human=context.get('TODAY_HUMAN', ''),
            end_of_today=context.get('END_OF_TODAY', ''),
            end_of_week=context.get('END_OF_WEEK', ''),
            end_of_month=context.get('END_OF_MONTH', ''),
            next_monday=context.get('NEXT_MONDAY', ''),
            next_occurrences=json.dumps(context.get('NEXT_OCCURRENCES', {})),
            slots_json=json.dumps(slots)
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
                resolved_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{[^}]*\}', response_text)
                if json_match:
                    resolved_data = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from response: {response_text}")
            
            # Validate and create AbsoluteResolution
            return AbsoluteResolution(
                start_text=resolved_data.get("start_text", ""),
                end_text=resolved_data.get("end_text", ""),
                duration=resolved_data.get("duration")
            )
            
        except Exception as e:
            raise ValueError(f"Absolute resolution failed: {str(e)}")
    
    def resolve_absolute_safe(self, slots: Dict[str, Any], context: Dict[str, Any]) -> AbsoluteResolution:
        """
        Safe version of resolve_absolute that returns default values on failure
        
        Args:
            slots: Dictionary with start_text, end_text, duration
            context: Context information
            
        Returns:
            AbsoluteResolution object (with defaults if resolution fails)
        """
        try:
            return self.resolve_absolute(slots, context)
        except Exception as e:
            print(f"Warning: Absolute resolution failed: {e}")
            # Return default resolution based on current time
            now_iso = context.get('NOW_ISO', '')
            end_of_today = context.get('END_OF_TODAY', '')
            return AbsoluteResolution(
                start_text=now_iso,
                end_text=end_of_today,
                duration=slots.get('duration')
            )


# Example usage
if __name__ == "__main__":
    resolver = AbsoluteResolver()
    
    # Example context (you would get this from a context provider)
    example_context = {
        'NOW_ISO': '2025-10-18T15:00:00-04:00',
        'TIMEZONE': 'America/New_York',
        'TODAY_HUMAN': 'Saturday, October 18, 2025',
        'END_OF_TODAY': 'October 18, 2025 11:59 pm',
        'END_OF_WEEK': 'October 19, 2025 11:59 pm',
        'END_OF_MONTH': 'October 31, 2025 11:59 pm',
        'NEXT_MONDAY': 'October 20, 2025 09:00 am',
        'NEXT_OCCURRENCES': {
            'Monday': 'October 20, 2025',
            'Tuesday': 'October 21, 2025',
            'Wednesday': 'October 22, 2025',
            'Thursday': 'October 23, 2025',
            'Friday': 'October 24, 2025',
            'Saturday': 'October 25, 2025',
            'Sunday': 'October 26, 2025'
        }
    }
    
    # Test cases
    test_slots = [
        {"start_text": None, "end_text": "Nov 15", "duration": "2h"},
        {"start_text": "tomorrow", "end_text": None, "duration": None},
        {"start_text": "Friday 2pm", "end_text": "Friday 4pm", "duration": "30m"},
        {"start_text": "11am", "end_text": None, "duration": None},
        {"start_text": None, "end_text": None, "duration": None}
    ]
    
    print("Testing Absolute Resolver:")
    for slots in test_slots:
        try:
            resolution = resolver.resolve_absolute_safe(slots, example_context)
            print(f"✅ Slots: {slots} -> Resolution: {resolution}")
        except Exception as e:
            print(f"❌ Slots: {slots} -> Error: {e}")
