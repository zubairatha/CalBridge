# CalBridge — Local Apple Calendar Helper (README)

A tiny macOS app (Python + PyObjC + FastAPI) that owns Calendar permissions and exposes a local HTTP API so your planner can read/write Apple Calendar events without TCC headaches. Part of a bigger project i'll be working on. Storing this here - could be useful for multiple apps.

---

## 0) Prerequisites

* macOS (Apple Calendar installed)
* Python 3.11 (works with your `.venv`)
* Tools: `pip`, `py2app`, `pyobjc`, `fastapi`, `uvicorn`, `pydantic`

Create/activate a virtualenv:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Install deps:

```bash
pip install pyobjc fastapi uvicorn py2app pydantic anyio sniffio h11
```

Project files (minimal):

```
helper_app.py    # FastAPI + EventKit
setup.py         # py2app config
```

---

## 1) Build & Run

### A) **Dev / Alias build** (recommended while iterating)

Uses your source files directly (no need to rebuild on every code change).

```bash
# from project root
rm -rf build dist
python setup.py py2app -A
./dist/CalBridge.app/Contents/MacOS/CalBridge
```

You should see logs:

```
Calendar access: True/False
CalBridge listening on http://127.0.0.1:8765 ...
INFO:     Uvicorn running on http://127.0.0.1:8765
```

### B) Normal (frozen) build

```bash
rm -rf build dist
python setup.py py2app
open dist/CalBridge.app
```

> Note: When launched via Finder, stdout is hidden. To see logs:

```bash
./dist/CalBridge.app/Contents/MacOS/CalBridge
```

---

## 2) Permissions (TCC)

* Calendar permission is **per-app/binary**. Grant it to **CalBridge.app** once; it persists.
* First run should show a system dialog. If not:

Open: **System Settings → Privacy & Security → Calendars**
Ensure **CalBridge** is listed and toggled **On**.

Reset (if needed):

```bash
# resets Calendar permission for the app bundle id in setup.py
tccutil reset Calendar dev.zubair.CalBridge
```

---

## 3) API Endpoints (HTTP, local-only)

Base URL (default): `http://127.0.0.1:8765`

* `GET /status` → `{"authorized": true/false, "status_code": <int>}`
* `GET /calendars` → list calendars with `id`, `title`, `allows_modifications`, `color_hex`
* `GET /events?days=7`
  Optional query:
  `calendar_id`, `calendar_title`, `exclude_holidays=true`, `all_day_only=true`, `non_all_day_only=true`
* `POST /add` (JSON)

  ```json
  {
    "title": "Title",
    "start_iso": "2025-10-03T10:00:00-04:00",
    "end_iso":   "2025-10-03T10:45:00-04:00",
    "notes": "optional",
    "calendar_id": "…",          // preferred
    "calendar_title": "Home"      // fallback
  }
  ```

  Returns: `{ id, title, start_iso, end_iso, calendar }`
* `POST /delete?event_id=…` → `{ "deleted": true/false }`

*(Optional utilities you might add: `/free_gaps`, `/delete_many`, `/update`, `/add_recurring`.)*

---

## 4) Quick Tests

### A) `curl`

```bash
curl -s http://127.0.0.1:8765/status
curl -s http://127.0.0.1:8765/calendars
curl -s "http://127.0.0.1:8765/events?days=3"
```

### B) Notebook snippets (assuming the app is running)

**Status & calendars**

```python
import requests
BASE = "http://127.0.0.1:8765"
print(requests.get(f"{BASE}/status").json())
for c in requests.get(f"{BASE}/calendars").json():
    print(c)
```

**Add → verify → delete**

```python
from datetime import datetime, timedelta
import requests, time

BASE = "http://127.0.0.1:8765"

start = (datetime.now().astimezone() + timedelta(minutes=5)).isoformat()
end   = (datetime.now().astimezone() + timedelta(minutes=35)).isoformat()

# choose a calendar_id from /calendars
CAL_ID = "PASTE_YOURS"

added = requests.post(f"{BASE}/add", json={
    "title": "Notebook Test Event",
    "start_iso": start, "end_iso": end,
    "notes": "created from notebook",
    "calendar_id": CAL_ID
}).json()
print("ADDED:", added)

eid = added["id"]
events = requests.get(f"{BASE}/events", params={"days": 3}).json()
print("FOUND:", any(e["id"] == eid for e in events))

print("DELETE:", requests.post(f"{BASE}/delete", params={"event_id": eid}).json())
```

---

## 5) Running on a Different Port

Add to `helper_app.py`:

```python
import os
def run_server():
    port = int(os.environ.get("CALBRIDGE_PORT", "8765"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
```

Run with:

```bash
export CALBRIDGE_PORT=8787
./dist/CalBridge.app/Contents/MacOS/CalBridge
# update BASE = http://127.0.0.1:8787 in your client
```

---

## 6) Calendar Targeting (Work vs Home)

* Prefer **`calendar_id`** (stable, exact) over title.
* Get IDs:

```bash
curl -s http://127.0.0.1:8765/calendars
```

* Create explicitly in a calendar:

```bash
curl -s -X POST http://127.0.0.1:8765/add \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Test: Work event",
    "start_iso":"2025-10-03T10:00:00-04:00",
    "end_iso":"2025-10-03T10:30:00-04:00",
    "calendar_id":"<WORK_CAL_ID>"
  }'
```

> With the strict resolver, if the requested calendar doesn’t exist or isn’t writable you’ll get a **4xx error** (no silent fallback).

---

## 7) Common Troubleshooting

**A) Port already in use**

```bash
lsof -nP -iTCP:8765 -sTCP:LISTEN
kill <PID>        # or: kill -9 <PID>
pkill -f CalBridge
```

**B) App already running**

* Quit from Dock (right-click → Quit) or:

```bash
pkill -f CalBridge
```

**C) No permission dialog / unauthorized**

* Ensure you’re launching the **app bundle** (not just `python helper_app.py`).
* Check **System Settings → Privacy & Security → Calendars** (toggle **CalBridge** on).
* Reset (if stuck):

```bash
tccutil reset Calendar dev.zubair.CalBridge
open dist/CalBridge.app
```

**D) `/calendars` 404 after changes**

* You’re likely running an **older build**. Use **alias build** while iterating:

```bash
rm -rf build dist
python setup.py py2app -A
./dist/CalBridge.app/Contents/MacOS/CalBridge
```

**E) Uvicorn not bundled**

* Ensure these are included in `setup.py`:

  ```python
  'packages': ['fastapi','starlette','uvicorn','pydantic','anyio','sniffio','h11'],
  'includes': ['EventKit','Foundation','AppKit'],
  ```
* Rebuild clean: `rm -rf build dist && python setup.py py2app`

**F) Verify the binary you’re using**

```bash
which python
```

Make sure your `.venv` is active before building/running.

---

## 8) Helper Design Notes

* Main thread keeps the **Cocoa run loop** alive (EventKit needs it).
* **Uvicorn** runs in a background thread serving HTTP on localhost.
* All Calendar I/O happens inside the authorized app → client code (Cursor/notebook) remains simple and permission-free.

---

## 9) Safety / Idempotency Tip

When creating events, include your own identifiers in `notes` (e.g., `t:task_123 s:sub_a v:1`). If anything gets out of sync, you can reconcile by listing `/events` and matching those tokens.
