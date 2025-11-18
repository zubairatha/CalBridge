"""
Slot Extractor Component - LLM-based extraction of start, end, duration from user queries
"""
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel
from llm_setup import get_llm


class SlotExtraction(BaseModel):
    """Slot extraction result model"""
    start_text: Optional[str] = None
    end_text: Optional[str] = None
    duration: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "start_text": self.start_text,
            "end_text": self.end_text,
            "duration": self.duration
        }
    
    def __str__(self) -> str:
        return f"SlotExtraction(start_text='{self.start_text}', end_text='{self.end_text}', duration='{self.duration}')"


class SlotExtractor:
    """LLM-based slot extractor for time-related information"""
    
    def __init__(self):
        self.llm = get_llm()
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> str:
        """Create the prompt template for slot extraction"""
        return """
You are a slot extractor that extracts time-related information from user queries.

**CRITICAL RULE: ONLY extract time information that is EXPLICITLY stated in the query. Do NOT infer, assume, or hallucinate time information.**

**Output contract (STRICT JSON):**
- Keys: `start_text`, `end_text`, `duration`
- Values: each is **string or `null`**.
- It is **OK (and preferred)** to return `null` when something is not present or unclear. Do **not** invent values.
- Preserve the user's phrasing (e.g., `"tomorrow"`, `"Friday 2pm"`, `"Nov 15"`, `"EOM"`, `"6pm"`, `"in 2 hours"`).
- No absolute dates/times, no ISO, no defaults, no normalization.

```json
{{"start_text": string|null, "end_text": string|null, "duration": string|null}}
```

## Detection Rules

### 1) **Duration** (metadata only)
Extract when any duration phrase is present (keep as-is):
- Forms: `for <N><unit>`, `for <N> <unit>`, `<N><unit>`, `<N> <unit>`, compounds like `2h30m`, `1.5h`, `90m`
- Units: `m|min|mins|minute|minutes|h|hr|hrs|hour|hours`
- Phrases: "for half an hour", "for an hour", "take 45 minutes"
- **Not duration:** phone numbers, prices, counts ("buy 2 apples"), IDs.

### 2) **End (deadline or range-end)** → `end_text`
Mark **end_text** if either of these:

**A) Deadline markers (no explicit range needed)**
- Keywords: **by**, **before**, **no later than**, **due**, **deadline**, **at the latest**, **by EOD/EOW/EOM**, **end of day/week/month**
- "until <time/date>" **without** a clear start ⇒ treat as deadline
- "through <date/time>" **without** "from" ⇒ deadline

**B) Explicit range joiners (capture the end side)**
- Joiners: **from X to Y**, **between X and Y**, **X–Y / X - Y**, **X through Y**, **start … until Y** (when a start exists)

### 3) **Start (when-to-begin anchor)** → `start_text`
Mark **start_text** when you see a start cue:
- Relative/vague anchors: **today**, **tomorrow**, **tonight**, **this <period>**, **next <period/week>**
- Specific dates/times: "Nov 15", "November 15 3pm", "11/15", "at 6", "6pm", "Friday"
- Start verbs: "from 3", "starting tomorrow", "begin at noon", "start Friday"
- "in <X time>" offsets: "in 2 hours", "in 15 minutes"

## Examples (All Combinations):

### Start Only:
- "call mom **tomorrow**" → `{{"start_text":"tomorrow","end_text":null,"duration":null}}`
- "call mom **tomorrow 4pm**" → `{{"start_text":"tomorrow 4pm","end_text":null,"duration":null}}`
- "meeting **at 3pm**" → `{{"start_text":"3pm","end_text":null,"duration":null}}`
- "start **next week**" → `{{"start_text":"next week","end_text":null,"duration":null}}`
- "begin **this evening**" → `{{"start_text":"this evening","end_text":null,"duration":null}}`

### End Only (Deadlines):
- "send report **by Friday 5pm**" → `{{"start_text":null,"end_text":"Friday 5pm","duration":null}}`
- "finish **before 5pm**" → `{{"start_text":null,"end_text":"5pm","duration":null}}`
- "deadline **is tomorrow**" → `{{"start_text":null,"end_text":"tomorrow","duration":null}}`
- "work **until 4**" → `{{"start_text":null,"end_text":"4","duration":null}}`

### Duration Only:
- "call zain **for 30min**" → `{{"start_text":null,"end_text":null,"duration":"30min"}}`
- "study **for 2 hours**" → `{{"start_text":null,"end_text":null,"duration":"2 hours"}}`
- "take a **45-minute break**" → `{{"start_text":null,"end_text":null,"duration":"45-minute"}}`
- "spend **3 hours** on coding" → `{{"start_text":null,"end_text":null,"duration":"3 hours"}}`

### Start + End (Range):
- "**from 10 to 1**" → `{{"start_text":"10","end_text":"1","duration":null}}`
- "**between 9am and noon**" → `{{"start_text":"9am","end_text":"noon","duration":null}}`
- "**from Monday to Friday**" → `{{"start_text":"Monday","end_text":"Friday","duration":null}}`
- "from 9am to 12pm on Oct 30" → `{{"start_text":"Oct 30 9am","end_text":"Oct 30 12 pm","duration":null}}`

### Start + Duration:
- "**study for 45m at 6pm**" → `{{"start_text":"6pm","end_text":null,"duration":"45m"}}`
- "work **tomorrow for 2 hours**" → `{{"start_text":"tomorrow","end_text":null,"duration":"2 hours"}}`
- "meeting **at 3pm for 1 hour**" → `{{"start_text":"3pm","end_text":null,"duration":"1 hour"}}`

### End + Duration:
- "finish **by Friday for 30min**" → `{{"start_text":null,"end_text":"Friday","duration":"30min"}}`
- "complete **before 5pm in 2 hours**" → `{{"start_text":null,"end_text":"5pm","duration":"2 hours"}}`

### Start + End + Duration:
- "work **from 9am to 5pm for 8 hours**" → `{{"start_text":"9am","end_text":"5pm","duration":"8 hours"}}`
- "meeting **at 2pm until 4pm for 2 hours**" → `{{"start_text":"2pm","end_text":"4pm","duration":"2 hours"}}`

### Complex Combinations:
- "start **next week**, finish **by EOM**" → `{{"start_text":"next week","end_text":"EOM","duration":null}}`
- "review documents **this afternoon for 45 minutes before 5pm**" → `{{"start_text":"this afternoon","end_text":"5pm","duration":"45 minutes"}}`

### No Time Information (CRITICAL - These must return ALL nulls):
- "ping Alex about the doc" → `{{"start_text":null,"end_text":null,"duration":null}}`
- "buy groceries at the store" → `{{"start_text":null,"end_text":null,"duration":null}}`
- "clean the house" → `{{"start_text":null,"end_text":null,"duration":null}}`
- "read a book" → `{{"start_text":null,"end_text":null,"duration":null}}`
- "call mom" → `{{"start_text":null,"end_text":null,"duration":null}}`
- "call customer support" → `{{"start_text":null,"end_text":null,"duration":null}}`
- "send email" → `{{"start_text":null,"end_text":null,"duration":null}}`
- "write report" → `{{"start_text":null,"end_text":null,"duration":null}}`

## CRITICAL: No Time Information Detection
**ONLY extract time information if the query explicitly contains time-related words.**

If the query contains NO explicit time-related words, dates, durations, or temporal references, return ALL nulls:
- "call mom" (no time words) → `{{"start_text":null,"end_text":null,"duration":null}}`
- "buy groceries" (no time words) → `{{"start_text":null,"end_text":null,"duration":null}}`
- "clean the house" (no time words) → `{{"start_text":null,"end_text":null,"duration":null}}`
- "read a book" (no time words) → `{{"start_text":null,"end_text":null,"duration":null}}`

**DO NOT infer or assume time information. Only extract what is explicitly stated.**
**DO NOT extract location phrases like "at the store", "in the library", "at home" as time information.**

**IMPORTANT:** Return ONLY valid JSON. No explanations, no markdown formatting, just the JSON object.

User Query: "{query}"
User Timezone: {timezone}

Extract the slots and return JSON:
"""
    
    def extract_slots(self, query: str, timezone: str = "UTC") -> SlotExtraction:
        """
        Extract time-related slots from a user query
        
        Args:
            query: The user query string
            timezone: User's timezone
            
        Returns:
            SlotExtraction object with extracted slots
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Format the prompt
        prompt = self.prompt_template.format(
            query=query.strip(),
            timezone=timezone
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
                slots_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, try to extract JSON from the response
                import re
                json_match = re.search(r'\{[^}]*\}', response_text)
                if json_match:
                    slots_data = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse JSON from response: {response_text}")
            
            # Validate and create SlotExtraction
            return SlotExtraction(
                start_text=slots_data.get("start_text"),
                end_text=slots_data.get("end_text"),
                duration=slots_data.get("duration")
            )
            
        except Exception as e:
            raise ValueError(f"Slot extraction failed: {str(e)}")
    
    def extract_slots_safe(self, query: str, timezone: str = "UTC") -> SlotExtraction:
        """
        Safe version of extract_slots that returns all nulls on failure
        
        Args:
            query: The user query string
            timezone: User's timezone
            
        Returns:
            SlotExtraction object (with nulls if extraction fails)
        """
        try:
            return self.extract_slots(query, timezone)
        except Exception as e:
            print(f"Warning: Slot extraction failed for '{query}': {e}")
            return SlotExtraction(start_text=None, end_text=None, duration=None)


# Example usage
if __name__ == "__main__":
    extractor = SlotExtractor()
    
    # Test basic functionality
    test_queries = [
        "Complete Math HW by 14 Nov",
        "Call Mom tomorrow for 30 minutes",
        "Plan John's Bday by 21st November",
        "Work on project from 9am to 5pm",
        "Study for 2 hours tonight",
        "Meeting at 3pm for 1 hour",
        "Deadline is Friday",
        "Start next week, finish by EOM"
    ]
    
    print("Testing Slot Extractor:")
    for query in test_queries:
        try:
            slots = extractor.extract_slots(query)
            print(f"✅ '{query}' -> {slots}")
        except Exception as e:
            print(f"❌ '{query}' -> Error: {e}")
