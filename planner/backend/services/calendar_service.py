import requests
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from models import CalendarEvent, FreeSlotRequest, FreeSlotResponse, CalendarTarget

class CalendarService:
    """Service for communicating with CalBridge API."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8765"):
        self.base_url = base_url
        self.timeout = 10
    
    async def check_status(self) -> Dict[str, Any]:
        """Check if CalBridge is running and authorized."""
        try:
            response = requests.get(f"{self.base_url}/status", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"CalBridge connection failed: {e}")
    
    async def get_calendars(self) -> List[Dict[str, Any]]:
        """Get list of available calendars."""
        try:
            response = requests.get(f"{self.base_url}/calendars", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get calendars: {e}")
    
    async def get_events(
        self, 
        days: int = 7,
        calendar_id: Optional[str] = None,
        calendar_title: Optional[str] = None,
        exclude_holidays: bool = False
    ) -> List[CalendarEvent]:
        """Get calendar events."""
        try:
            params = {"days": days}
            if calendar_id:
                params["calendar_id"] = calendar_id
            if calendar_title:
                params["calendar_title"] = calendar_title
            if exclude_holidays:
                params["exclude_holidays"] = True
            
            response = requests.get(f"{self.base_url}/events", params=params, timeout=self.timeout)
            response.raise_for_status()
            
            events_data = response.json()
            events = []
            for event_data in events_data:
                events.append(CalendarEvent(
                    id=event_data["id"],
                    title=event_data["title"],
                    start_iso=event_data["start_iso"],
                    end_iso=event_data["end_iso"],
                    calendar=event_data["calendar"],
                    notes=event_data.get("notes")
                ))
            
            return events
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get events: {e}")
    
    async def create_event(
        self,
        title: str,
        start_iso: str,
        end_iso: str,
        notes: Optional[str] = None,
        calendar_id: Optional[str] = None,
        calendar_title: Optional[str] = None
    ) -> CalendarEvent:
        """Create a new calendar event."""
        try:
            payload = {
                "title": title,
                "start_iso": start_iso,
                "end_iso": end_iso
            }
            
            if notes:
                payload["notes"] = notes
            if calendar_id:
                payload["calendar_id"] = calendar_id
            elif calendar_title:
                payload["calendar_title"] = calendar_title
            
            response = requests.post(f"{self.base_url}/add", json=payload, timeout=self.timeout)
            response.raise_for_status()
            
            event_data = response.json()
            return CalendarEvent(
                id=event_data["id"],
                title=event_data["title"],
                start_iso=event_data["start_iso"],
                end_iso=event_data["end_iso"],
                calendar=event_data["calendar"],
                notes=notes
            )
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create event: {e}")
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        try:
            response = requests.post(f"{self.base_url}/delete", params={"event_id": event_id}, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result.get("deleted", False)
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to delete event: {e}")
    
    async def create_events_batch(self, events: List[Dict[str, Any]]) -> List[CalendarEvent]:
        """Create multiple events atomically."""
        created_events = []
        failed_events = []
        
        for event_data in events:
            try:
                event = await self.create_event(
                    title=event_data["title"],
                    start_iso=event_data["start_iso"],
                    end_iso=event_data["end_iso"],
                    notes=event_data.get("notes"),
                    calendar_id=event_data.get("calendar_id"),
                    calendar_title=event_data.get("calendar_title")
                )
                created_events.append(event)
            except Exception as e:
                failed_events.append({"event": event_data, "error": str(e)})
        
        if failed_events:
            # If any events failed, clean up the successful ones
            for event in created_events:
                try:
                    await self.delete_event(event.id)
                except:
                    pass  # Best effort cleanup
            raise Exception(f"Batch creation failed: {failed_events}")
        
        return created_events
    
    async def delete_events_batch(self, event_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple events."""
        results = {"deleted": [], "failed": []}
        
        for event_id in event_ids:
            try:
                success = await self.delete_event(event_id)
                if success:
                    results["deleted"].append(event_id)
                else:
                    results["failed"].append({"id": event_id, "error": "Event not found"})
            except Exception as e:
                results["failed"].append({"id": event_id, "error": str(e)})
        
        return results
    
    async def find_free_slots(
        self,
        start: datetime,
        end: datetime,
        duration_minutes: int,
        calendar_target: Optional[CalendarTarget] = None
    ) -> List[FreeSlotResponse]:
        """Find available time slots in calendar."""
        try:
            # Get events in the time range
            days = (end - start).days + 1
            events = await self.get_events(days=days)
            
            # Filter events by calendar if specified
            if calendar_target:
                events = [e for e in events if e.calendar == calendar_target.value]
            
            # Convert events to datetime objects
            event_blocks = []
            for event in events:
                event_start = datetime.fromisoformat(event.start_iso)
                event_end = datetime.fromisoformat(event.end_iso)
                
                # Convert to timezone-naive if needed for comparison
                if event_start.tzinfo is not None:
                    event_start = event_start.replace(tzinfo=None)
                if event_end.tzinfo is not None:
                    event_end = event_end.replace(tzinfo=None)
                
                # Only include events that overlap with our search window
                if event_start < end and event_end > start:
                    event_blocks.append((event_start, event_end))
            
            # Sort events by start time
            event_blocks.sort(key=lambda x: x[0])
            
            # Find gaps between events
            free_slots = []
            current_time = start
            
            for event_start, event_end in event_blocks:
                # Check if there's a gap before this event
                if current_time < event_start:
                    gap_duration = (event_start - current_time).total_seconds() / 60
                    if gap_duration >= duration_minutes:
                        free_slots.append(FreeSlotResponse(
                            start=current_time,
                            end=event_start,
                            duration_minutes=int(gap_duration),
                            score=1.0,  # Basic score, will be improved by scheduler
                            reason="Available gap between events"
                        ))
                
                # Move current time to end of this event
                current_time = max(current_time, event_end)
            
            # Check for gap after last event
            if current_time < end:
                gap_duration = (end - current_time).total_seconds() / 60
                if gap_duration >= duration_minutes:
                    free_slots.append(FreeSlotResponse(
                        start=current_time,
                        end=end,
                        duration_minutes=int(gap_duration),
                        score=1.0,
                        reason="Available time after last event"
                    ))
            
            return free_slots
            
        except Exception as e:
            raise Exception(f"Failed to find free slots: {e}")
    
    async def get_calendar_id_by_title(self, title: str) -> Optional[str]:
        """Get calendar ID by title."""
        try:
            calendars = await self.get_calendars()
            for calendar in calendars:
                if calendar["title"] == title:
                    return calendar["id"]
            return None
        except Exception as e:
            raise Exception(f"Failed to get calendar ID: {e}")
    
    async def is_calendar_writable(self, calendar_id: str) -> bool:
        """Check if a calendar is writable."""
        try:
            calendars = await self.get_calendars()
            for calendar in calendars:
                if calendar["id"] == calendar_id:
                    return calendar["allows_modifications"]
            return False
        except Exception as e:
            raise Exception(f"Failed to check calendar writability: {e}")
