# helper_app.py
import threading, time
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import objc
from Foundation import NSDate, NSRunLoop
from AppKit import NSApplication
from EventKit import EKEventStore, EKEntityTypeEvent, EKAuthorizationStatusAuthorized

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from EventKit import EKEntityTypeEvent
from AppKit import NSColor
from fastapi import HTTPException

def find_calendar(calendar_id: str | None, calendar_title: str | None):
    # Try ID first (exact)
    if calendar_id:
        c = store.calendarWithIdentifier_(calendar_id)
        if c and c.allowsContentModifications():
            return c
    # Then try title (case-insensitive)
    if calendar_title:
        wanted = calendar_title.strip().lower()
        for c in store.calendarsForEntityType_(EKEntityTypeEvent) or []:
            if (c.title() or "").strip().lower() == wanted and c.allowsContentModifications():
                return c
    # Fallback: default calendar
    return store.defaultCalendarForNewEvents()



def resolve_calendar_or_error(calendar_id: str | None, calendar_title: str | None):
    # Try by ID first (exact)
    if calendar_id:
        c = store.calendarWithIdentifier_(calendar_id)
        if not c:
            raise HTTPException(status_code=404, detail=f"calendar_id not found: {calendar_id}")
        if not c.allowsContentModifications():
            raise HTTPException(status_code=400, detail=f"calendar_id not writable: {calendar_id} ({c.title()})")
        return c

    # Then by title (case-insensitive)
    if calendar_title:
        wanted = calendar_title.strip().lower()
        for c in store.calendarsForEntityType_(EKEntityTypeEvent) or []:
            if (c.title() or "").strip().lower() == wanted:
                if not c.allowsContentModifications():
                    raise HTTPException(status_code=400, detail=f"calendar_title not writable: {c.title()}")
                return c
        raise HTTPException(status_code=404, detail=f"calendar_title not found: {calendar_title}")

    # Neither provided → default calendar
    c = store.defaultCalendarForNewEvents()
    if not c or not c.allowsContentModifications():
        raise HTTPException(status_code=400, detail="default calendar not writable")
    return c


# ---------- EventKit ----------
store = EKEventStore()

def nsdate(py_dt: datetime) -> NSDate:
    if py_dt.tzinfo is None:
        py_dt = py_dt.astimezone()
    return NSDate.dateWithTimeIntervalSince1970_(py_dt.timestamp())

def pump(dt=0.05):
    NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(dt))

def ensure_access(timeout_s=90) -> bool:
    granted = {"val": None}
    if store.respondsToSelector_("requestFullAccessToEventsWithCompletion:"):
        def handler(ok, err): granted["val"] = bool(ok)
        store.requestFullAccessToEventsWithCompletion_(handler)
    else:
        def handler(ok, err): granted["val"] = bool(ok)
        store.requestAccessToEntityType_completion_(EKEntityTypeEvent, handler)

    deadline = time.time() + timeout_s
    while granted["val"] is None and time.time() < deadline:
        pump(0.1)
    return bool(granted["val"])

# ---------- FastAPI models ----------
class EventIn(BaseModel):
    title: str
    start_iso: str
    end_iso: str
    notes: str | None = None
    calendar_id: str | None = None       # <-- NEW
    calendar_title: str | None = None    # <-- optional fallback



class EventOut(BaseModel):
    title: str
    start_iso: str
    end_iso: str
    id: Optional[str] = None
    calendar: Optional[str] = None

# ---------- API ----------
app = FastAPI()

@app.get("/status")
def status():
    st = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
    return {"authorized": bool(st == EKAuthorizationStatusAuthorized), "status_code": int(st)}

@app.get("/events")
def events(days: int = 7) -> List[EventOut]:
    start = datetime.now().astimezone()
    end = start + timedelta(days=days)
    pred = store.predicateForEventsWithStartDate_endDate_calendars_(nsdate(start), nsdate(end), None)
    evs = sorted(store.eventsMatchingPredicate_(pred) or [], key=lambda e: e.startDate())
    out = []
    for e in evs:
        sd = datetime.fromtimestamp(e.startDate().timeIntervalSince1970(), tz=timezone.utc).astimezone()
        ed = datetime.fromtimestamp(e.endDate().timeIntervalSince1970(), tz=timezone.utc).astimezone()
        out.append(EventOut(
            title=str(e.title() or ""),
            start_iso=sd.isoformat(),
            end_iso=ed.isoformat(),
            id=str(e.eventIdentifier() or ""),
            calendar=str(e.calendar().title() if e.calendar() else "")
        ))
    return out



def nscolor_to_hex(nscolor):
    if nscolor is None: return None
    c = nscolor.colorUsingColorSpaceName_("NSCalibratedRGBColorSpace")
    if c is None: return None
    r = int(round(c.redComponent()*255)); g = int(round(c.greenComponent()*255)); b = int(round(c.blueComponent()*255))
    return f"#{r:02x}{g:02x}{b:02x}"

@app.get("/calendars")
def calendars():
    out = []
    for c in store.calendarsForEntityType_(EKEntityTypeEvent) or []:
        out.append({
            "id": str(c.calendarIdentifier()),
            "title": str(c.title() or ""),
            "allows_modifications": bool(c.allowsContentModifications()),
            "color_hex": nscolor_to_hex(c.color()),
        })
    return out


@app.post("/add")
def add(ev: EventIn) -> EventOut:
    from EventKit import EKEvent
    start = datetime.fromisoformat(ev.start_iso)
    end   = datetime.fromisoformat(ev.end_iso)

    cal = resolve_calendar_or_error(ev.calendar_id, ev.calendar_title)

    e = EKEvent.eventWithEventStore_(store)
    e.setTitle_(ev.title)
    e.setStartDate_(nsdate(start))
    e.setEndDate_(nsdate(end))
    if ev.notes:
        e.setNotes_(ev.notes)
    e.setCalendar_(cal)
    store.saveEvent_span_error_(e, 0, None)

    return EventOut(
        title=ev.title,
        start_iso=start.isoformat(),
        end_iso=end.isoformat(),
        id=str(e.eventIdentifier()),
        calendar=str(cal.title() or "")
    )




@app.post("/delete")
def delete(event_id: str):
    ev = store.eventWithIdentifier_(event_id)
    if ev:
        store.removeEvent_span_error_(ev, 0, None)
        return {"deleted": True}
    return {"deleted": False}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")

if __name__ == "__main__":
    # bring to front and request permission (shows the dialog for THIS app bundle)
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    ok = ensure_access(90)
    print("Calendar access:", ok)

    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    print("CalendarHelper listening on http://127.0.0.1:8765 ...")
    while True:
        pump(0.2)
