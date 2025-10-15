# Load the polished scheduler code (module-style) and run all previously discussed cases.
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

# ----------------------------------------------------------------------
# Utilities
# ----------------------------------------------------------------------

def day_start(dt: datetime) -> datetime:
    return datetime(dt.year, dt.month, dt.day)

def next_midnight(dt: datetime) -> datetime:
    return day_start(dt) + timedelta(days=1)

def split_interval_by_midnight(a: datetime, b: datetime) -> List[Tuple[datetime, datetime]]:
    """Split [a,b) into day-contained intervals (no midnight crossing)."""
    out = []
    cur = a
    while cur < b:
        out.append((cur, min(b, next_midnight(cur))))
        cur = out[-1][1]
    return out

def intersect(iv1: Tuple[datetime, datetime], iv2: Tuple[datetime, datetime]) -> Optional[Tuple[datetime, datetime]]:
    s = max(iv1[0], iv2[0]); e = min(iv1[1], iv2[1])
    return (s, e) if s < e else None

def subtract_block(intervals: List[Tuple[datetime, datetime]],
                   s: datetime, e: datetime) -> List[Tuple[datetime, datetime]]:
    """Return intervals \ (s,e)."""
    out = []
    for a,b in intervals:
        if e <= a or s >= b:
            out.append((a,b))
        else:
            if a < s:
                out.append((a, s))
            if e < b:
                out.append((e, b))
    out.sort()
    merged = []
    for iv in out:
        if not merged or merged[-1][1] < iv[0]:
            merged.append(iv)
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], iv[1]))
    return merged

def find_earliest_block(intervals: List[Tuple[datetime, datetime]], duration_min: int) -> Optional[Tuple[datetime, datetime]]:
    need = timedelta(minutes=duration_min)
    for a,b in intervals:
        if (b - a) >= need:
            return (a, a + need)
    return None

def choose_even_spread_targets(num_tasks: int, num_days: int) -> List[int]:
    """Return target day indices for even spacing across [0..num_days-1]."""
    if num_tasks == 1:
        return [num_days // 2]
    return [round(i * (num_days - 1) / (num_tasks - 1)) for i in range(num_tasks)]

# ----------------------------------------------------------------------
# Constraints
# ----------------------------------------------------------------------

@dataclass
class ConstraintAdder:
    """
    Add optional constraints on top of baseline rules.
    - weekly_blackouts: recurring per weekday (Mon=0..Sun=6)
    - date_blackouts: for specific calendar dates
    - max_tasks_per_day: cap tasks per day (None = unlimited)
    - min_gap_minutes: cooldown after each placed task (same day)
    """
    weekly_blackouts: Dict[int, List[Tuple[time, time]]] = field(default_factory=lambda: defaultdict(list))
    date_blackouts: Dict[date, List[Tuple[time, time]]] = field(default_factory=lambda: defaultdict(list))
    max_tasks_per_day: Optional[int] = None
    min_gap_minutes: int = 0

    def add_weekly_blackout(self, weekday: int, start_t: time, end_t: time) -> None:
        self.weekly_blackouts[weekday].append((start_t, end_t))

    def add_date_blackout(self, d: date, start_t: time, end_t: time) -> None:
        self.date_blackouts[d].append((start_t, end_t))

    def set_max_tasks_per_day(self, cap: int) -> None:
        self.max_tasks_per_day = cap

    def set_min_gap_minutes(self, gap: int) -> None:
        self.min_gap_minutes = max(0, gap)

    def apply_blackouts(self, day_windows: Dict[date, List[Tuple[datetime, datetime]]]) -> None:
        """Subtract blackout windows from day availability, in-place."""
        for d, intervals in list(day_windows.items()):
            # Build blackout intervals (as datetimes) for this date
            blocks: List[Tuple[datetime, datetime]] = []
            weekday = datetime.combine(d, time(0,0)).weekday()

            for st, et in self.weekly_blackouts.get(weekday, []):
                blocks.append((datetime.combine(d, st), datetime.combine(d, et)))

            for st, et in self.date_blackouts.get(d, []):
                blocks.append((datetime.combine(d, st), datetime.combine(d, et)))

            # Subtract all blocks
            for bs, be in blocks:
                new_intervals = []
                for a,b in intervals:
                    if be <= a or bs >= b:
                        new_intervals.append((a,b))
                    else:
                        if a < bs:
                            new_intervals.append((a, bs))
                        if be < b:
                            new_intervals.append((be, b))
                new_intervals.sort()
                # merge
                merged = []
                for iv in new_intervals:
                    if not merged or merged[-1][1] < iv[0]:
                        merged.append(iv)
                    else:
                        merged[-1] = (merged[-1][0], max(merged[-1][1], iv[1]))
                intervals = merged

            day_windows[d] = intervals

# ----------------------------------------------------------------------
# Scheduler
# ----------------------------------------------------------------------

@dataclass
class ScheduleOptions:
    work_start_hour: int = 6   # 6 AM
    work_end_hour: int = 23    # 11 PM

@dataclass
class Assignment:
    task_id: int
    duration_min: int
    day: date
    start: datetime
    end: datetime

def schedule_ordered_with_constraints(
    tasks_min: List[int],
    raw_slots: List[Tuple[str, str]],
    deadline_iso: str,
    constraints: Optional[ConstraintAdder] = None,
    options: ScheduleOptions = ScheduleOptions(),
) -> Tuple[List[Assignment], Dict[date, int]]:
    """
    Schedule ordered tasks into free slots, respecting:
      - tasks in given order
      - no crossing midnight
      - daily work window (default: 6 AM–11 PM)
      - optional: weekly/date blackouts, min_gap_minutes, max_tasks_per_day
      - anti-bunching via even-spread targets + fewest-tasks/day tie-break.

    Returns (assignments, per_day_counts).
    Raises RuntimeError with a clear message if infeasible.
    """
    constraints = constraints or ConstraintAdder()
    deadline = datetime.fromisoformat(deadline_iso)
    slots = [(datetime.fromisoformat(a), datetime.fromisoformat(b)) for a,b in raw_slots]

    # 1) Build per-day availability from slots:
    pieces: List[Tuple[datetime, datetime]] = []
    for a,b in slots:
        if a >= b:
            continue
        pieces.extend(split_interval_by_midnight(a, b))

    # Cap to deadline
    capped: List[Tuple[datetime, datetime]] = []
    for a,b in pieces:
        if a >= deadline:
            continue
        capped.append((a, min(b, deadline)))

    # Intersect with daily work window
    workday_windows: Dict[date, List[Tuple[datetime, datetime]]] = defaultdict(list)
    for a,b in capped:
        d0 = day_start(a)
        work_window = (d0 + timedelta(hours=options.work_start_hour),
                       d0 + timedelta(hours=options.work_end_hour))
        inter = intersect((a,b), work_window)
        if inter:
            workday_windows[d0.date()].append(inter)

    # Clean empty days & sort daily intervals
    for k in list(workday_windows.keys()):
        workday_windows[k].sort()
        if not workday_windows[k]:
            del workday_windows[k]

    # 2) Apply extra blackouts (weekly/date)
    constraints.apply_blackouts(workday_windows)

    eligible_days = sorted(workday_windows.keys())
    if not eligible_days:
        raise RuntimeError("No eligible working-day intervals before deadline after applying constraints.")

    # 3) Feasibility check
    total_avail_min = sum(int((b-a).total_seconds()//60) for d in eligible_days for a,b in workday_windows[d])
    total_need_min = sum(tasks_min)
    if total_avail_min < total_need_min:
        raise RuntimeError(f"Infeasible: need {total_need_min} min but only {total_avail_min} min available.")

    # 4) Even-spread target days
    targets = choose_even_spread_targets(len(tasks_min), len(eligible_days))

    # 5) Greedy placement in order
    assignments: List[Assignment] = []
    per_day_count: Dict[date, int] = {d: 0 for d in eligible_days}

    for idx, (dur, target_idx) in enumerate(zip(tasks_min, targets)):
        placed = False

        # Rank candidate days
        ranked_days = sorted(
            eligible_days,
            key=lambda d: (abs(eligible_days.index(d) - target_idx), per_day_count[d])
        )

        for day_key in ranked_days:
            # Max per day
            if constraints.max_tasks_per_day is not None and per_day_count[day_key] >= constraints.max_tasks_per_day:
                continue

            block = find_earliest_block(workday_windows[day_key], dur)
            if not block:
                continue

            s, e = block
            assignments.append(Assignment(task_id=idx, duration_min=dur, day=day_key, start=s, end=e))
            # subtract
            workday_windows[day_key] = subtract_block(workday_windows[day_key], s, e)

            # cooldown
            if constraints.min_gap_minutes > 0:
                cool_s, cool_e = e, e + timedelta(minutes=constraints.min_gap_minutes)
                workday_windows[day_key] = subtract_block(workday_windows[day_key], cool_s, cool_e)

            per_day_count[day_key] += 1
            placed = True
            break

        if not placed:
            raise RuntimeError(f"Could not place task index {idx} ({dur} min) before deadline with current constraints.")

    assignments.sort(key=lambda a: (a.start, a.task_id))
    return assignments, per_day_count

# ----------------------------------------------------------------------
# Pretty printing
# ----------------------------------------------------------------------

def print_schedule(assignments: List[Assignment], per_day_count: Dict[date, int]) -> None:
    def fmt(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %a %I:%M %p")
    print("Schedule:")
    for a in assignments:
        print(f"- Task {a.task_id:>2} | {a.duration_min:>3} min | {fmt(a.start)} → {fmt(a.end)}")
    print("\nPer-day counts:")
    for d in sorted(per_day_count):
        if per_day_count[d] > 0:
            print(f"  {d}: {per_day_count[d]}")

# ----------------------------------------------------------------------
# Test Scenarios (all cases discussed)
# ----------------------------------------------------------------------

def run_case(title, tasks, slots, deadline, constraints: Optional[ConstraintAdder]=None):
    print(f"\n\n=== {title} ===")
    try:
        assignments, counts = schedule_ordered_with_constraints(tasks, slots, deadline, constraints)
        print_schedule(assignments, counts)
    except RuntimeError as e:
        print("Scheduling failed:", e)

# 1) Original wide horizon
deadline1 = "2025-11-01T23:59:00"
slots1 = [
    ("2025-10-13T20:45:35","2025-10-14T15:55:00"),
    ("2025-10-14T18:00:00","2025-10-15T18:15:00"),
    ("2025-10-15T20:30:00","2025-10-20T11:45:00"),
    ("2025-10-20T13:00:00","2025-10-21T15:55:00"),
    ("2025-10-21T18:00:00","2025-10-27T11:45:00"),
    ("2025-10-27T13:00:00","2025-10-28T15:55:00"),
    ("2025-10-28T18:00:00","2025-11-01T20:45:35"),
]
tasks_common = [180, 150, 120, 180, 90]

# 2) Tighter slots across horizon
deadline2 = "2025-11-01T23:59:00"
slots2 = [
    ("2025-10-14T06:30:00","2025-10-14T10:00:00"),
    ("2025-10-16T07:00:00","2025-10-16T09:45:00"),
    ("2025-10-20T18:00:00","2025-10-20T21:30:00"),
    ("2025-10-24T06:00:00","2025-10-24T08:00:00"),
    ("2025-10-28T19:00:00","2025-10-28T22:30:00"),
]

# 3A) Stress tight deadline (feasible) with different task list
deadline3A = "2025-10-21T23:59:00"
slots3A = [
    ("2025-10-14T06:30:00","2025-10-14T09:30:00"),
    ("2025-10-15T08:00:00","2025-10-15T09:30:00"),
    ("2025-10-16T07:00:00","2025-10-16T08:30:00"),
    ("2025-10-17T19:00:00","2025-10-17T21:00:00"),
    ("2025-10-20T06:00:00","2025-10-20T07:30:00"),
    ("2025-10-21T20:00:00","2025-10-21T23:00:00"),
]
tasks3A = [180, 150, 120, 90, 60]

# 3B) Stress tight deadline (infeasible)
deadline3B = "2025-10-21T23:59:00"
slots3B = [
    ("2025-10-14T07:00:00","2025-10-14T09:00:00"),
    ("2025-10-15T08:00:00","2025-10-15T09:00:00"),
    ("2025-10-16T07:00:00","2025-10-16T08:00:00"),
    ("2025-10-17T19:00:00","2025-10-17T20:30:00"),
    ("2025-10-20T06:30:00","2025-10-20T07:30:00"),
    ("2025-10-21T20:00:00","2025-10-21T22:00:00"),
]
tasks3B = [180, 150, 120, 180, 90]

# 4) Forced two tasks in a day (3-day horizon with multiple windows)
deadline4 = "2025-10-16T23:59:00"
slots4 = [
    ("2025-10-14T07:00:00","2025-10-14T11:00:00"),
    ("2025-10-14T14:00:00","2025-10-14T17:00:00"),
    ("2025-10-15T07:00:00","2025-10-15T08:30:00"),
    ("2025-10-15T18:00:00","2025-10-15T20:00:00"),
    ("2025-10-16T07:00:00","2025-10-16T08:00:00"),
    ("2025-10-16T19:00:00","2025-10-16T22:00:00"),
]

# 5) Three-day simple slots from last test
deadline5 = "2025-10-16T23:59:00"
slots5 = [
    ("2025-10-14T07:00:00","2025-10-14T14:00:00"), 
    ("2025-10-15T07:00:00","2025-10-15T10:30:00"),
    ("2025-10-16T07:00:00","2025-10-16T11:00:00")
]

if __name__ == "__main__":
    # Run all cases
    run_case("Case 1: Original wide horizon (ORDERED)", tasks_common, slots1, deadline1)
    run_case("Case 2: Tighter slots across horizon (ORDERED)", tasks_common, slots2, deadline2)
    run_case("Case 3A: Stress (tight, ORDERED & FEASIBLE)", tasks3A, slots3A, deadline3A)
    run_case("Case 3B: Stress (tighter, ORDERED & INFEASIBLE)", tasks3B, slots3B, deadline3B)
    run_case("Case 4: Forced two tasks/day (ORDERED)", tasks_common, slots4, deadline4)
    run_case("Case 5: Three-day simple slots (ORDERED)", tasks_common, slots5, deadline5)

    # Constraint adder demos for the last case
    def run_constraints_demo():
        print("\n\n=== Constraint demos on Case 5 ===")
        # Baseline
        try:
            base_assign, base_counts = schedule_ordered_with_constraints(tasks_common, slots5, deadline5)
            print("\nBaseline:")
            print_schedule(base_assign, base_counts)
        except RuntimeError as e:
            print("Baseline failed:", e)

        # Weekly blackout (Monday 12-1)
        try:
            cx_week = ConstraintAdder()
            cx_week.add_weekly_blackout(weekday=0, start_t=time(12,0), end_t=time(13,0))
            w_assign, w_counts = schedule_ordered_with_constraints(tasks_common, slots5, deadline5, constraints=cx_week)
            print("\nWeekly blackout (Mon 12–1):")
            print_schedule(w_assign, w_counts)
        except RuntimeError as e:
            print("Weekly blackout failed:", e)

        # Date-specific blackout: 2025-10-15 09:00–09:30
        try:
            cx_date = ConstraintAdder()
            cx_date.add_date_blackout(date(2025,10,15), start_t=time(9,0), end_t=time(9,30))
            d_assign, d_counts = schedule_ordered_with_constraints(tasks_common, slots5, deadline5, constraints=cx_date)
            print("\nDate blackout (2025-10-15 09:00–09:30):")
            print_schedule(d_assign, d_counts)
        except RuntimeError as e:
            print("Date blackout failed:", e)

        # Min gap 30 + max 2/day
        try:
            cx_gap = ConstraintAdder()
            cx_gap.set_min_gap_minutes(30)
            cx_gap.set_max_tasks_per_day(2)
            g_assign, g_counts = schedule_ordered_with_constraints(tasks_common, slots5, deadline5, constraints=cx_gap)
            print("\nMin gap 30m + max 2/day:")
            print_schedule(g_assign, g_counts)
        except RuntimeError as e:
            print("\nMin gap 30m + max 2/day failed:", e)

    run_constraints_demo()
