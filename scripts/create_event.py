import os, json, requests, argparse
from datetime import datetime, timedelta
from dateutil import tz

BASE = os.getenv("CALBRIDGE_BASE", "http://127.0.0.1:8765")
TZ = os.getenv("TIMEZONE", "America/New_York")

def iso_in_tz(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz.gettz(TZ))
    return dt.astimezone(tz.gettz(TZ)).isoformat()

def main():
    ap = argparse.ArgumentParser(description="Create a single event via CalBridge")
    ap.add_argument("--title", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM-DDTHH:MM (local)")
    ap.add_argument("--duration-min", type=int, required=True)
    ap.add_argument("--calendar-id", required=False)
    ap.add_argument("--calendar-title", required=False)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    start_local = datetime.fromisoformat(args.start)
    end_local = start_local + timedelta(minutes=args.duration_min)

    payload = {
        "title": args.title,
        "start_iso": iso_in_tz(start_local),
        "end_iso": iso_in_tz(end_local),
        "notes": args.notes
    }
    if args.calendar_id:
        payload["calendar_id"] = args.calendar_id
    elif args.calendar_title:
        payload["calendar_title"] = args.calendar_title

    r = requests.post(f"{BASE}/add", json=payload, timeout=10)
    print("STATUS:", r.status_code)
    print(r.text)

if __name__ == "__main__":
    main()
