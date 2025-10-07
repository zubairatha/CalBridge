import os, json, requests, pathlib

BASE = os.getenv("CALBRIDGE_BASE", "http://127.0.0.1:8765")
OUT = pathlib.Path(__file__).resolve().parents[1] / "config" / "calendars.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

def main():
    r = requests.get(f"{BASE}/calendars", timeout=10)
    r.raise_for_status()
    cals = r.json()
    data = {
        "default_work_title": "Work",
        "default_home_title": "Home",
        "calendars": [
            {"id": c["id"], "title": c["title"], "writable": bool(c["allows_modifications"])}
            for c in cals
        ]
    }
    OUT.write_text(json.dumps(data, indent=2))
    print(f"wrote {OUT} with {len(cals)} calendars")

if __name__ == "__main__":
    main()
