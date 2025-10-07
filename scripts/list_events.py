import os, requests, argparse
from datetime import datetime

BASE = os.getenv("CALBRIDGE_BASE", "http://127.0.0.1:8765")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--calendar-title", default=None)
    ap.add_argument("--calendar-id", default=None)
    ap.add_argument("--exclude-holidays", action="store_true")
    args = ap.parse_args()

    params = {"days": args.days}
    if args.calendar_title:
        params["calendar_title"] = args.calendar_title
    if args.calendar_id:
        params["calendar_id"] = args.calendar_id
    if args.exclude_holidays:
        params["exclude_holidays"] = True

    evs = requests.get(f"{BASE}/events", params=params, timeout=15).json()
    print(f"Found {len(evs)} events in next {args.days} days:")
    for e in sorted(evs, key=lambda x: x["start_iso"]):
        s = datetime.fromisoformat(e["start_iso"]).strftime("%Y-%m-%d %H:%M")
        en = datetime.fromisoformat(e["end_iso"]).strftime("%H:%M")
        print(f"- {s} → {en} | {e['title']} [{e.get('calendar','')}] id={e['id']}")

if __name__ == "__main__":
    main()
