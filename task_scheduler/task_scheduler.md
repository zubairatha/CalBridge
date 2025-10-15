# README — Ordered Even-Spread Scheduler

A lightweight Python module to schedule **ordered tasks** into **free time slots** before a deadline while:

* enforcing **baseline constraints** (no midnight crossing, **6:00 AM–11:00 PM** work window),
* **spreading tasks out** to avoid clumping (anti-bunching),
* and supporting **extra user constraints** (weekly/date blackouts, min gap, max tasks/day).

It’s a fast, practical **greedy heuristic** that produces human-sensible plans and clear errors when infeasible.

---

## ✨ What it does

* Takes a **deadline**, a list of **free time slots**, and an **ordered list of task durations** (each ≤ 180 minutes).
* Splits slots by midnight and clips to the **work window** (default 06:00–23:00).
* **Applies user constraints** (e.g., “Mondays 12–1 busy”, “2025-10-15 9:00–9:30 blocked”, “≤2 tasks/day”, “≥30 min gap”).
* Schedules tasks **in order** using an **even-spread + least-loaded-day** heuristic, placing each at the **earliest feasible** time in the chosen day.
* Returns a **structured schedule** and **per-day counts**, or a **clear error** if not possible.

---

## 📦 Installation

Just drop the single Python file into your project (the module you received in chat).
Requires only the standard library (`datetime`, `dataclasses`, etc.). No third-party deps.

---

## 🧩 Inputs

### 1) Deadline

* **Type:** ISO 8601 string
* **Example:** `"2025-11-01T23:59:00"`

### 2) Free time slots

* **Type:** `List[Tuple[str, str]]` (start_iso, end_iso)
* **Rules:** start < end; local naive datetimes are fine
* **Example:**

```python
slots = [
  ("2025-10-14T07:00:00","2025-10-14T14:00:00"),
  ("2025-10-15T07:00:00","2025-10-15T10:30:00"),
  ("2025-10-16T07:00:00","2025-10-16T11:00:00"),
]
```

### 3) Tasks (ordered)

* **Type:** `List[int]` (minutes)
* **Rules:** each duration ≤ **180** (3h); the **list order = execution order**
* **Example:** `tasks = [180, 150, 120, 180, 90]`

### 4) Baseline options (optional)

* **Type:** `ScheduleOptions`
* **Defaults:** `work_start_hour=6`, `work_end_hour=23`
* **Example:** `ScheduleOptions(work_start_hour=8, work_end_hour=20)`

### 5) Extra constraints (optional)

* **Type:** `ConstraintAdder`
* **Capabilities:**

  * `add_weekly_blackout(weekday, start_time, end_time)`

    * `weekday`: `0..6` (Mon=0)
    * `start_time`, `end_time`: `datetime.time`
  * `add_date_blackout(date_obj, start_time, end_time)`

    * `date_obj`: `datetime.date`
  * `set_max_tasks_per_day(cap: int)`
  * `set_min_gap_minutes(gap: int)`

**Examples:**

```python
from datetime import date, time

cx = ConstraintAdder()
cx.add_weekly_blackout(weekday=0, start_t=time(12,0), end_t=time(13,0))     # Mondays 12–1
cx.add_date_blackout(date(2025,10,15), start_t=time(9,0), end_t=time(9,30)) # Oct 15 9:00–9:30
cx.set_min_gap_minutes(30)   # ≥30 min between tasks on same day
cx.set_max_tasks_per_day(2)  # cap daily tasks
```

---

## 📤 Outputs

### Primary return value

`assignments, per_day_count = schedule_ordered_with_constraints(...)`

* **`assignments`: `List[Assignment]`**
  Each `Assignment` has:

  * `task_id: int` — index in the original task list
  * `duration_min: int`
  * `day: datetime.date`
  * `start: datetime.datetime`
  * `end: datetime.datetime`

* **`per_day_count`: `Dict[date, int]`**
  Maps each scheduled date to the number of tasks placed on that date.

### Pretty printing (optional)

The module includes:

```python
print_schedule(assignments, per_day_count)
```

which prints a readable plan and per-day counts.

---

## 🚀 Quick start

```python
deadline = "2025-10-16T23:59:00"
slots = [
  ("2025-10-14T07:00:00","2025-10-14T14:00:00"),
  ("2025-10-15T07:00:00","2025-10-15T10:30:00"),
  ("2025-10-16T07:00:00","2025-10-16T11:00:00"),
]
tasks = [180, 150, 120, 180, 90]  # ordered

# Baseline (6AM–11PM, no midnight)
assignments, counts = schedule_ordered_with_constraints(tasks, slots, deadline)
print_schedule(assignments, counts)

# With extra constraints
cx = ConstraintAdder()
cx.add_weekly_blackout(weekday=0, start_t=time(12,0), end_t=time(13,0))     # Monday lunch
cx.add_date_blackout(date(2025,10,15), start_t=time(9,0), end_t=time(9,30)) # specific date
cx.set_min_gap_minutes(15)
# cx.set_max_tasks_per_day(2)

assignments2, counts2 = schedule_ordered_with_constraints(tasks, slots, deadline, constraints=cx)
print_schedule(assignments2, counts2)
```

---

## 🔧 How it works (algorithm)

1. **Normalize availability**

   * Split each free slot at midnight → no task can cross days.
   * Clip each daily piece to the **work window** (default 06:00–23:00).
   * Apply **blackouts** (weekly & date) by subtracting them from the daily intervals.

2. **Coarse feasibility check**

   * Sum available minutes vs. sum of task minutes; fail early if impossible.

3. **Even-spread targets**

   * Compute target day indices:
     [
     \text{target}_i = \text{round}\left(\frac{i,(D-1)}{N-1}\right)
     ]
     where *N* = number of tasks, *D* = number of available days.

4. **Ordered greedy placement**

   * For task *i*, rank days by:

     1. closeness to its target index, then
     2. **fewest tasks already on that day** (anti-bunching).
   * Pick the **earliest feasible interval** on the chosen day.
   * Subtract the interval (and optional **cooldown gap**) from day availability.
   * Respect **max_tasks_per_day** if set.
   * Repeat in **original task order**.

5. **Return structured schedule**

   * Or raise a clear `RuntimeError` if any task can’t be placed.

**Complexity:** ~O(N × D × K), where *N* = tasks, *D* = days, *K* = intervals/day — tiny for personal calendars.

---

## ⚠️ Failure modes (clear errors)

* **Infeasible (total time):**
  `"Infeasible: need {total_need} min but only {total_avail} min available."`
* **Infeasible (local placement):**
  `"Could not place task index {i} ({dur} min) before deadline with current constraints."`

Common causes: too many long tasks, tight windows, restrictive blackouts, large min-gap, or small max-per-day.

---

## 🧱 Edge cases & tips

* **Back-to-back limit:** If you want to avoid same-day stacking, set `max_tasks_per_day=1`.
* **Encourage spacing:** Keep `min_gap_minutes` > 0 (e.g., 30) to reduce clustering within a day.
* **Partial days:** The work window (06:00–23:00) is configurable via `ScheduleOptions`.
* **Timezone:** Inputs are treated as naive local times. For TZ-aware behavior, wrap parsing with `zoneinfo`/`pytz` and normalize to a chosen zone.

---

## 🧭 Extending further

* **Exact optimal spacing**: swap heuristic for an OR-Tools CP-SAT model (minimize max per-day load, variance, etc.).
* **Multiple resources**: extend daily windows per resource and use `max_tasks_per_day` per resource or a CP model.
* **Task attributes**: add priorities/weights, skills, or prerequisites (beyond simple order).

---

## ✅ Summary

* **Inputs:** deadline (ISO), free slots (ISO pairs), ordered task durations (minutes), optional constraints & options.
* **Outputs:** a list of **Assignments** (task_id, duration, day, start, end) + **per_day_count** summary.
* **Guarantees:** respects 6AM–11PM, no midnight crossing, task order, and user constraints; spreads tasks sensibly; fails clearly when infeasible.
