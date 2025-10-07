import os, json, requests, argparse, re
from datetime import datetime, timedelta
from dateutil import tz, parser as dateparser
from pathlib import Path

CALBRIDGE_BASE = os.getenv("CALBRIDGE_BASE", "http://127.0.0.1:8765")
OLLAMA_BASE = os.getenv("OLLAMA_BASE", "http://127.0.0.1:11434")
MODEL = os.getenv("OLLAMA_MODEL", "gemma3")
TZNAME = os.getenv("TIMEZONE", "America/New_York")

CACHE_PATH = Path(__file__).resolve().parents[1] / "config" / "calendars.json"

SYSTEM_PROMPT = """You convert a natural sentence into STRICT JSON for creating ONE calendar event.
Return ONLY valid JSON and nothing else.

Schema:
{
  "title": "string",
  "calendar_hint": "Work|Home|null",
  "start_local": "YYYY-MM-DDTHH:MM",   // local wall time (no timezone)
  "duration_minutes": 30               // integer >= 5
}

Context:
- now_local = {NOW_LOCAL}  (timezone: {TZ})
- Treat all relative dates/times relative to now_local.

Relative date/time rules (must follow):
- “today” → today’s date. If time missing, default 10:00.
- “tomorrow” → now_local + 1 day.
- “day after tomorrow” / “day after” → now_local + 2 days.
- “in N days” → now_local + N days. “in N hours/minutes” adjusts time accordingly.
- Weekdays:
  - “this Friday” = the upcoming Friday in the current week (or today if it’s Friday).
  - “next Friday” = the Friday of the following week (strictly > this Friday).
- Times:
  - Accept “10”, “10am”, “10 am”, “10:30”, “noon” (12:00), “midnight” (00:00).
  - “morning” = 09:00, “afternoon” = 15:00, “evening/tonight” = 19:00 unless a time is given.
- Dates like “Oct 10, 2025” or “2025-10-10” keep that date; if time missing default 10:00.
- If both date and duration are missing, set duration_minutes=30.

Rules:
- Title should be short and actionable (e.g., "Call with Uncle").
- If they say Work/Home explicitly, set calendar_hint accordingly; otherwise infer if obvious; else null.
"""

def load_calendar_cache():
    if not CACHE_PATH.exists():
        raise SystemExit(f"Calendar cache not found: {CACHE_PATH}. Run scripts/cache_calendars.py first.")
    data = json.loads(CACHE_PATH.read_text())
    # lowercase title -> entry
    by_title_lc = { (c["title"] or "").lower(): c for c in data.get("calendars", []) }
    return data, by_title_lc

def iso_with_tz(local_dt_str: str) -> datetime:
    # parse "YYYY-MM-DDTHH:MM" (no tz) as local TZ
    dt = dateparser.parse(local_dt_str)
    return dt.replace(tzinfo=tz.gettz(TZNAME))

def extract_json_str(s: str) -> str:
    """Be tolerant if the model wrapped JSON with text or code fences."""
    s = s.strip()
    # if it's already pure JSON, try directly
    if s.startswith("{"):
        # try to find the matching closing brace by simple stack
        depth = 0
        for i, ch in enumerate(s):
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[:i+1]
    # try code fence ```json ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, flags=re.S)
    if fence:
        return fence.group(1)
    # fallback: grab first {...} block
    m = re.search(r"(\{.*\})", s, flags=re.S)
    if m:
        return m.group(1)
    raise ValueError("No JSON object found in model output.")

def call_ollama(user_text: str, now_local: str, tzname: str) -> dict:
    prompt = SYSTEM_PROMPT.replace("{NOW_LOCAL}", now_local).replace("{TZ}", tzname)
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_text}
        ],
        "options": {"temperature": 0.1},
        "stream": False  # IMPORTANT: disable streaming so .json() works
    }
    r = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=120)
    r.raise_for_status()

    # Newer Ollama (non-stream) returns a single JSON with message.content
    try:
        data = r.json()
        content = data["message"]["content"]
    except Exception:
        # If server still streamed or returned text, fall back to raw text parsing
        content = r.text

    # Extract strict JSON
    json_str = extract_json_str(content)
    return json.loads(json_str)

def main():
    ap = argparse.ArgumentParser(
        description="Turn NL into a concrete calendar event via Ollama + CalBridge"
    )
    ap.add_argument("text", help="e.g. 'Create a Home event for Oct 10, 2025 call with my uncle for 30 minutes'")
    args = ap.parse_args()

    now_local = datetime.now(tz.gettz(TZNAME)).strftime("%Y-%m-%dT%H:%M")
    plan = call_ollama(args.text, now_local, TZNAME)

    # Pull fields with sane defaults/validation
    print(plan)
    title = (plan.get("title") or "").strip() or "Untitled"
    cal_hint = (plan.get("calendar_hint") or "").strip().lower() or None
    start_local_str = plan.get("start_local")
    if not start_local_str:
        raise SystemExit("Model did not return 'start_local'.")
    dur = int(plan.get("duration_minutes") or 30)
    if dur < 5:
        dur = 30

    start_dt = iso_with_tz(start_local_str)
    end_dt = start_dt + timedelta(minutes=dur)

    # Resolve calendar_id from cache if hint provided
    _, by_title_lc = load_calendar_cache()
    calendar_id = None
    if cal_hint in ("work", "home"):
        entry = by_title_lc.get(cal_hint)
        if not entry:
            # try exact titles “Work”/“Home” in lowercase map
            entry = by_title_lc.get("work" if cal_hint == "work" else "home")
        if entry and entry.get("writable"):
            calendar_id = entry["id"]

    payload = {
        "title": title,
        "start_iso": start_dt.isoformat(),
        "end_iso": end_dt.isoformat(),
        "notes": f"source=ollama; tz={TZNAME}"
    }
    if calendar_id:
        payload["calendar_id"] = calendar_id

    print("→ Creating event with payload:")
    print(json.dumps(payload, indent=2))

    cr = requests.post(f"{CALBRIDGE_BASE}/add", json=payload, timeout=15)
    print("CalBridge STATUS:", cr.status_code)
    print(cr.text)

if __name__ == "__main__":
    main()
