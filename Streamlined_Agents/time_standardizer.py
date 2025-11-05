"""
Time Standardizer Component - Convert Absolute Resolver output to ISO formats
"""
import re
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
import pytz


class TimeStandardization(BaseModel):
    """Time standardization result model"""
    start: str  # ISO format
    end: str    # ISO format
    duration: Optional[str] = None  # ISO-8601 duration or null
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "start": self.start,
            "end": self.end,
            "duration": self.duration
        }
    
    def __str__(self) -> str:
        return f"TimeStandardization(start='{self.start}', end='{self.end}', duration='{self.duration}')"


class TimeStandardizer:
    """Time Standardizer for converting absolute text to ISO formats"""
    
    def __init__(self):
        # Canonical format regex: "Month DD, YYYY HH:MM am/pm"
        self.canonical_regex = re.compile(
            r'^([A-Za-z]+)\s+(\d{2}),\s+(\d{4})\s+(\d{2}):(\d{2})\s+(am|pm)$',
            re.IGNORECASE
        )
        
        # Extended format regex: "Weekday, Month DD, YYYY HH:MM am/pm"
        self.extended_regex = re.compile(
            r'^[A-Za-z]+,\s+([A-Za-z]+)\s+(\d{2}),\s+(\d{4})\s+(\d{2}):(\d{2})\s+(am|pm)$',
            re.IGNORECASE
        )
        
        # ISO format regex (fallback for faulty AR output)
        self.iso_regex = re.compile(
            r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})([+-]\d{2}:\d{2}|Z)$'
        )
        
        # Month name mapping
        self.month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
    
    def _parse_canonical_format(self, text: str) -> Optional[datetime]:
        """
        Parse canonical format: "Month DD, YYYY HH:MM am/pm"
        Returns None if format doesn't match
        """
        match = self.canonical_regex.match(text.strip())
        if not match:
            return None
        
        month_name, day, year, hour, minute, ampm = match.groups()
        
        try:
            month = self.month_map[month_name.lower()]
            day = int(day)
            year = int(year)
            hour = int(hour)
            minute = int(minute)
            
            # Convert to 24-hour format
            if ampm.lower() == 'pm' and hour != 12:
                hour += 12
            elif ampm.lower() == 'am' and hour == 12:
                hour = 0
            
            return datetime(year, month, day, hour, minute)
        except (ValueError, KeyError):
            return None
    
    def _parse_extended_format(self, text: str) -> Optional[datetime]:
        """
        Parse extended format: "Weekday, Month DD, YYYY HH:MM am/pm"
        Returns None if format doesn't match
        """
        match = self.extended_regex.match(text.strip())
        if not match:
            return None
        
        month_name, day, year, hour, minute, ampm = match.groups()
        
        try:
            month = self.month_map[month_name.lower()]
            day = int(day)
            year = int(year)
            hour = int(hour)
            minute = int(minute)
            
            # Convert to 24-hour format
            if ampm.lower() == 'pm' and hour != 12:
                hour += 12
            elif ampm.lower() == 'am' and hour == 12:
                hour = 0
            
            return datetime(year, month, day, hour, minute)
        except (ValueError, KeyError):
            return None
    
    def _parse_iso_format(self, text: str) -> Optional[datetime]:
        """
        Parse ISO format as fallback for faulty AR output
        """
        match = self.iso_regex.match(text.strip())
        if not match:
            return None
        
        year, month, day, hour, minute, second, tz_offset = match.groups()
        
        try:
            return datetime(
                int(year), int(month), int(day),
                int(hour), int(minute), int(second)
            )
        except ValueError:
            return None
    
    def _apply_timezone(self, dt: datetime, timezone: str) -> datetime:
        """
        Apply timezone to datetime and return timezone-aware datetime
        """
        tz = pytz.timezone(timezone)
        
        # If datetime is naive, localize it
        if dt.tzinfo is None:
            return tz.localize(dt)
        else:
            # If already timezone-aware, convert to target timezone
            return dt.astimezone(tz)
    
    def _determine_seconds(self, dt: datetime, is_eod: bool = False) -> datetime:
        """
        Determine seconds based on EOD semantics
        If 11:59 pm and EOD, set seconds to 59, otherwise 00
        """
        if is_eod and dt.hour == 23 and dt.minute == 59:
            return dt.replace(second=59, microsecond=0)
        else:
            return dt.replace(second=0, microsecond=0)
    
    def _adjust_past_times(self, start_dt: datetime, end_dt: datetime, now: datetime) -> Tuple[datetime, datetime, str]:
        """
        Adjust times that are in the past according to the rules:
        - if only start < now: set start = now
        - if both start and end < now: set +1 day on both
        - if only end < now: set end date = date(start) [HHMM remain the same]
        
        Returns (start, end, adjustment_note)
        """
        start_is_past = start_dt < now
        end_is_past = end_dt < now
        
        if not start_is_past and not end_is_past:
            # No adjustments needed
            return start_dt, end_dt, ""
        
        if start_is_past and end_is_past:
            # Both start and end < now: set +1 day on both
            adjusted_start = start_dt + timedelta(days=1)
            adjusted_end = end_dt + timedelta(days=1)
            note = f"both start and end < now → moved +1 day"
            return adjusted_start, adjusted_end, note
        
        elif start_is_past and not end_is_past:
            # Only start < now: set start = now
            adjusted_start = now
            note = f"start < now → set start = now"
            return adjusted_start, end_dt, note
        
        elif not start_is_past and end_is_past:
            # Only end < now: set end date = date(start), HHMM remain the same
            adjusted_end = start_dt.replace(
                hour=end_dt.hour,
                minute=end_dt.minute,
                second=end_dt.second,
                microsecond=end_dt.microsecond
            )
            note = f"end < now → set end date = date(start), time preserved"
            return start_dt, adjusted_end, note
        
        # This should never happen, but just in case
        return start_dt, end_dt, ""
    
    def _enforce_invariant(self, start_dt: datetime, end_dt: datetime) -> Tuple[datetime, datetime, str]:
        """
        Enforce start <= end invariant
        If violated, repair by setting end to 23:59:59 on start's date
        Returns (start, end, repair_note)
        """
        if start_dt <= end_dt:
            return start_dt, end_dt, ""
        
        # Repair: set end to end of day on start's date
        repaired_end = start_dt.replace(hour=23, minute=59, second=59, microsecond=0)
        repair_note = f"repaired end < start → set to end_of_day(start)"
        
        return start_dt, repaired_end, repair_note
    
    def _normalize_duration(self, duration: Optional[str]) -> Optional[str]:
        """
        Convert duration to ISO-8601 format
        """
        if not duration:
            return None
        
        duration = duration.strip().lower()
        
        # Minutes
        if re.match(r'^\d+\s*(m|min|mins|minute|minutes)$', duration):
            minutes = int(re.search(r'\d+', duration).group())
            return f"PT{minutes}M"
        
        # Hours
        if re.match(r'^\d+\s*(h|hr|hrs|hour|hours)$', duration):
            hours = int(re.search(r'\d+', duration).group())
            return f"PT{hours}H"
        
        # Hour + minute compounds (2h30m, 2 h 30 m, etc.)
        compound_match = re.match(r'^(\d+)\s*(h|hr|hrs|hour|hours)\s*(\d+)\s*(m|min|mins|minute|minutes)$', duration)
        if compound_match:
            hours = int(compound_match.group(1))
            minutes = int(compound_match.group(3))
            return f"PT{hours}H{minutes}M"
        
        # Decimals (1.5h)
        decimal_match = re.match(r'^(\d+\.\d+)\s*(h|hr|hrs|hour|hours)$', duration)
        if decimal_match:
            hours_float = float(decimal_match.group(1))
            hours = int(hours_float)
            minutes = int((hours_float - hours) * 60)
            return f"PT{hours}H{minutes}M"
        
        # Half/An hour phrases
        if duration in ['half an hour', 'half hour']:
            return "PT30M"
        if duration in ['an hour', 'one hour']:
            return "PT1H"
        
        # Anything else - return null (be strict)
        return None
    
    def standardize(self, ar_output: Dict[str, Any], timezone: str) -> TimeStandardization:
        """
        Standardize Absolute Resolver output to ISO formats
        
        Args:
            ar_output: Dictionary with start_text, end_text, duration from AR
            timezone: IANA timezone (e.g., America/New_York)
            
        Returns:
            TimeStandardization object with ISO formats
        """
        if not ar_output:
            raise ValueError("AR output cannot be empty")
        
        start_text = ar_output.get('start_text')
        end_text = ar_output.get('end_text')
        duration = ar_output.get('duration')
        
        if not start_text or not end_text:
            raise ValueError("Both start_text and end_text are required")
        
        print(f"🔄 Time Standardizer: Processing AR output")
        print(f"   • Start: {start_text}")
        print(f"   • End: {end_text}")
        print(f"   • Duration: {duration}")
        print(f"   • Timezone: {timezone}")
        
        # Parse start_text
        start_dt = self._parse_canonical_format(start_text)
        if not start_dt:
            # Try extended format (with weekday)
            start_dt = self._parse_extended_format(start_text)
        if not start_dt:
            # Try ISO format as fallback
            start_dt = self._parse_iso_format(start_text)
            if not start_dt:
                raise ValueError(f"Could not parse start_text: {start_text}")
        
        # Parse end_text
        end_dt = self._parse_canonical_format(end_text)
        if not end_dt:
            # Try extended format (with weekday)
            end_dt = self._parse_extended_format(end_text)
        if not end_dt:
            # Try ISO format as fallback
            end_dt = self._parse_iso_format(end_text)
            if not end_dt:
                raise ValueError(f"Could not parse end_text: {end_text}")
        
        print(f"   • Parsed start: {start_dt}")
        print(f"   • Parsed end: {end_dt}")
        
        # Apply timezone
        start_dt = self._apply_timezone(start_dt, timezone)
        end_dt = self._apply_timezone(end_dt, timezone)
        
        print(f"   • With timezone: {start_dt} -> {end_dt}")
        
        # Determine seconds (EOD semantics)
        is_eod = end_text.strip().endswith('11:59 pm')
        start_dt = self._determine_seconds(start_dt, False)
        end_dt = self._determine_seconds(end_dt, is_eod)
        
        print(f"   • With seconds: {start_dt} -> {end_dt}")
        
        # Time validation and adjustment for past times
        now = datetime.now(pytz.timezone(timezone))
        start_dt, end_dt, time_adjustment_note = self._adjust_past_times(start_dt, end_dt, now)
        if time_adjustment_note:
            print(f"   • ⚠️  {time_adjustment_note}")
        
        # Enforce invariant (start <= end)
        start_dt, end_dt, repair_note = self._enforce_invariant(start_dt, end_dt)
        if repair_note:
            print(f"   • ⚠️  {repair_note}")
        
        # Convert to ISO format
        start_iso = start_dt.isoformat()
        end_iso = end_dt.isoformat()
        
        print(f"   • ISO start: {start_iso}")
        print(f"   • ISO end: {end_iso}")
        
        # Normalize duration
        duration_iso = self._normalize_duration(duration)
        print(f"   • Duration ISO: {duration_iso}")
        
        return TimeStandardization(
            start=start_iso,
            end=end_iso,
            duration=duration_iso
        )
    
    def standardize_safe(self, ar_output: Dict[str, Any], timezone: str) -> TimeStandardization:
        """
        Safe version of standardize that returns default values on failure
        
        Args:
            ar_output: Dictionary with start_text, end_text, duration from AR
            timezone: IANA timezone
            
        Returns:
            TimeStandardization object (with defaults if standardization fails)
        """
        try:
            return self.standardize(ar_output, timezone)
        except Exception as e:
            print(f"Warning: Time standardization failed: {e}")
            # Return default resolution based on current time
            now = datetime.now(pytz.timezone(timezone))
            end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=0)
            return TimeStandardization(
                start=now.isoformat(),
                end=end_of_today.isoformat(),
                duration=ar_output.get('duration')
            )


# Example usage
if __name__ == "__main__":
    standardizer = TimeStandardizer()
    
    # Test cases from the spec
    test_cases = [
        {
            "name": "Deadline only case",
            "ar_output": {
                "start_text": "October 18, 2025 03:00 pm",
                "end_text": "November 15, 2025 11:59 pm",
                "duration": "2h"
            },
            "timezone": "America/New_York"
        },
        {
            "name": "Range on same day",
            "ar_output": {
                "start_text": "October 24, 2025 02:00 pm",
                "end_text": "October 24, 2025 04:00 pm",
                "duration": "30m"
            },
            "timezone": "America/New_York"
        },
        {
            "name": "Start-only case",
            "ar_output": {
                "start_text": "October 19, 2025 09:00 am",
                "end_text": "October 19, 2025 11:59 pm",
                "duration": None
            },
            "timezone": "America/New_York"
        },
        {
            "name": "Bad ordering (should be repaired)",
            "ar_output": {
                "start_text": "October 24, 2025 08:00 pm",
                "end_text": "October 24, 2025 06:00 pm",
                "duration": None
            },
            "timezone": "America/New_York"
        },
        {
            "name": "Decimal hours",
            "ar_output": {
                "start_text": "October 20, 2025 09:00 am",
                "end_text": "October 20, 2025 11:59 pm",
                "duration": "1.5h"
            },
            "timezone": "America/New_York"
        }
    ]
    
    print("Testing Time Standardizer:")
    print("=" * 80)
    
    for test_case in test_cases:
        print(f"\n🧪 Test: {test_case['name']}")
        print("-" * 40)
        try:
            result = standardizer.standardize(test_case['ar_output'], test_case['timezone'])
            print(f"✅ Result: {result}")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
