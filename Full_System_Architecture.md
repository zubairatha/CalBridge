# Components

## 1. User Query (UQ) [Simple]

Eg: "Complete Math HW  by 14 Nov", "Call Mom tomorrow for 30 minutes", "Plan John's Bday by 21st November"

## 2. Slot Extractor (SE) [LLM-based]
"""
Extract raw start, end, duration texts from Raw User query
"""
### Input: 
UQ, User Timezone
### Output: 
JSON

{
    start_text: string | null,
    end_text: string | null,
    duration: string | null 
}

### Rules:
agent-rules/2_slot_extractor.txt

## 3. Absolute Resolver (AR) [LLM-based]
"""
Extract absolute values (like: October 21, 2025 9:00am) from SE; even parse duration if it exists
"""
### Input:
SE.output,
NOW_ISO (ISO with offset), TIMEZONE (IANA),TODAY_HUMAN (e.g., Saturday, October 18, 2025), TODAY_DOW_INDEX (0=Mon … 6=Sun), Whether daylight saving is active (IS_DST true/false)

Precomputed helpers (strings in canonical format):

END_OF_TODAY (e.g., October 18, 2025 11:59 pm)
END_OF_WEEK (end of current week at 11:59 pm)
END_OF_MONTH (EOM at 11:59 pm)
NEXT_MONDAY (next Monday 09:00 am as an anchor for “next week”)
NEXT_OCCURRENCES for each weekday (e.g., Friday: October 24, 2025)

Other info if needed (go through rules for more details)

### Output:
JSON
{
    start_text: string; ("Month DD, YYYY HH:MM am/pm" - canonical format),
    end_text: string; ("Month DD, YYYY HH:MM am/pm" - canonical format),
    duration: string | null (if exists)
}

### Rules:
agent-rules/3_absolute_resolver.txt

## 4. Time Standardizer (TS) [Code-Based]
"""
Convert AR output to standard formats (ISO etc) based on regex and rule-based checks
"""
### Input:
AR.output, Regex rules

### Output: 
{
    start: ISO Format,
    end: ISO Format,
    duration: Standard Format (TBD) | null
}

### Rules:
agent-rules/4_time_standardizer.txt

## 5. Task Difficulty Analyzer (TD) [LLM-Based]
"""
Classify task into simple/complex, assign a calendar id
"""

### Input:
UQ, TS.duration, Calendar Types (from CalBridge API)

### Output: 
JSON
{
    calendar: id,
    type: "simple" | "complex",
    title: string,
    duration: TS.duration
}

### Working:

A task is
- simple: when (TS.duration != null) OR (TS.duration==null AND Task is genuinely simple)
- complex: when (TS.duration==null AND Task is genuinely complex)

## 6. LLM Decomposer (LD) [LLM-Based]
"""
Creates sub-tasks for complex tasks
"""
### Input:
TD.output (where TD.type=="complex")

### Output:
JSON

{
    calendar: id,
    type: "complex",
    title: string,
    subtasks : [
        subtask1: {
            title: string,
            duration: Standard Format (TBD)
        }
        ...
        subtaskn: {
            title: string,
            duration: Standard Format (TBD)
        }
    ]
}

## 7. Time Allotment Agent (TA) [Code-Based]
"""
Uses CalBridge API (Getting Free slots), TS.output for time range and a smart task scheduler along with task data to assign slots to each task (or subtask) along with assigning proper IDs
"""

There are two paths for this agent based on task-complexity (Simple/Complex).

1) TYPE=SIMPLE

### Input:

Fetch Free Slots (CalbridgeAPI) (handle day overflow constraints), TD.output, TS.output, Task Scheduler

### Output:
JSON

{
    calendar: id,
    type: simple,
    title: string,
    slot: [start, end],
    id: <randomly_generated_id>
    parent_id: null
}

note: parent_id for all simple tasks is null; id is randomly-generated

1) TYPE=COMPLEX

### Input:

Fetch Free Slots (CalbridgeAPI) (handle day overflow constraints), LD.output, TS.output, Task Scheduler

### Output:
JSON

{
    calendar: id,
    type: "complex",
    title: string,
    id: <randomly_generated_id>
    parent_id: null,
    subtasks : [
        subtask1: {
            title: string,
            slot: [start, end],
            parent_id: id (same as id of parent task),
            id: <new_randomly_generated_id>
        }
        ...
        subtaskn: {
            title: string,
            slot: [start, end],
            parent_id: id (same as id of parent task),
            id: <new_randomly_generated_id>
        }
    ]
}

note: 
- parent_id for all subtasks of complex tasks is the same (id of the parent task)
- parent_id for the parent task of the subtasks is null.

## 8. Event Creator Agent (EC) [Code-Based]
"""
Creates events on the calendar using CalBridge API with notes (information of parent_id)
"""

### Input:
TA.output

### Output:

CalBridge POST request

### Working:

- If the task is simple, create an event with note: "id: id, parent_id: null". Store in DB. 
- If the task is complex, create events of subtasks on the calendar with note: "id: id,parent_id: <generated_parent_id>". Make sure to not create an event on the calendar for the parent task but merely store it in a local DB.
- Local DB storage:
    - 3 columns: Title, id, parent_id
    - Store all tasks, subtasks as per the information provided above.




