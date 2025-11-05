"""
Context Provider - Generates context information for Absolute Resolver
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz


class ContextProvider:
    """Provides context information for Absolute Resolver"""
    
    def __init__(self, timezone: str = "America/New_York"):
        self.timezone = timezone
        self.tz = pytz.timezone(timezone)
    
    def get_context(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate context information for Absolute Resolver
        
        Args:
            now: Current datetime (defaults to now)
            
        Returns:
            Dictionary with context information
        """
        if now is None:
            now = datetime.now(self.tz)
        elif now.tzinfo is None:
            now = self.tz.localize(now)
        
        # Convert to ISO format with timezone offset
        now_iso = now.isoformat()
        
        # Today's date in human format
        today_human = now.strftime("%A, %B %d, %Y")
        
        # End of today (11:59 pm)
        end_of_today = now.replace(hour=23, minute=59, second=0, microsecond=0)
        end_of_today_str = end_of_today.strftime("%B %d, %Y %I:%M %p").lower()
        
        # End of week (Sunday 11:59 pm)
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0 and now.hour >= 23 and now.minute >= 59:
            # If it's already end of week, use next Sunday
            days_until_sunday = 7
        end_of_week = now + timedelta(days=days_until_sunday)
        end_of_week = end_of_week.replace(hour=23, minute=59, second=0, microsecond=0)
        end_of_week_str = end_of_week.strftime("%B %d, %Y %I:%M %p").lower()
        
        # End of month (EOM 11:59 pm)
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1)
        else:
            next_month = now.replace(month=now.month + 1, day=1)
        end_of_month = next_month - timedelta(days=1)
        end_of_month = end_of_month.replace(hour=23, minute=59, second=0, microsecond=0)
        end_of_month_str = end_of_month.strftime("%B %d, %Y %I:%M %p").lower()
        
        # Next Monday 09:00 am
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7  # Next Monday
        next_monday = now + timedelta(days=days_until_monday)
        next_monday = next_monday.replace(hour=9, minute=0, second=0, microsecond=0)
        next_monday_str = next_monday.strftime("%B %d, %Y %I:%M %p").lower()
        
        # Next occurrences of weekdays
        next_occurrences = {}
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for i, day_name in enumerate(weekday_names):
            days_until_day = (i - now.weekday()) % 7
            if days_until_day == 0:
                days_until_day = 7  # Next occurrence
            next_day = now + timedelta(days=days_until_day)
            next_occurrences[day_name] = next_day.strftime("%B %d, %Y")
        
        return {
            'NOW_ISO': now_iso,
            'TIMEZONE': self.timezone,
            'TODAY_HUMAN': today_human,
            'END_OF_TODAY': end_of_today_str,
            'END_OF_WEEK': end_of_week_str,
            'END_OF_MONTH': end_of_month_str,
            'NEXT_MONDAY': next_monday_str,
            'NEXT_OCCURRENCES': next_occurrences
        }
    
    def get_context_for_testing(self, year: int = 2025, month: int = 10, day: int = 18, hour: int = 15, minute: int = 0) -> Dict[str, Any]:
        """
        Generate context for testing with specific date/time
        
        Args:
            year, month, day, hour, minute: Specific date/time for testing
            
        Returns:
            Dictionary with context information
        """
        test_datetime = datetime(year, month, day, hour, minute)
        return self.get_context(test_datetime)


# Example usage
if __name__ == "__main__":
    provider = ContextProvider()
    
    # Get current context
    context = provider.get_context()
    print("Current Context:")
    for key, value in context.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*50)
    
    # Get test context (October 18, 2025 3:00 PM)
    test_context = provider.get_context_for_testing(2025, 10, 18, 15, 0)
    print("Test Context (Oct 18, 2025 3:00 PM):")
    for key, value in test_context.items():
        print(f"  {key}: {value}")
