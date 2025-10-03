# client_test.py
import requests
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8765"

print("STATUS:", requests.get(f"{BASE}/status").json())
print("EVENTS:", requests.get(f"{BASE}/events", params={"days": 2}).json()[:2])

start = (datetime.now().astimezone() + timedelta(minutes=5)).isoformat()
end   = (datetime.now().astimezone() + timedelta(minutes=35)).isoformat()

added = requests.post(f"{BASE}/add", json={
    "title": "CalBridge test event",
    "start_iso": start,
    "end_iso": end,
    "notes": "hello from client_test.py"
}).json()
print("ADDED:", added)

deleted = requests.post(f"{BASE}/delete", params={"event_id": added["id"]}).json()
print("DELETED:", deleted)
