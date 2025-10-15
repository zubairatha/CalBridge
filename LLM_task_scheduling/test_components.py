"""
Comprehensive Tests for LLM Task Scheduling Components

This module provides tests for each component of the LLM task scheduling system:
1. LLM Decomposer tests
2. Time Allotment Agent tests  
3. Event Creator tests
4. Main Scheduler integration tests
"""

import unittest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

# Import the components to test
from .llm_decomposer import LLMTaskDecomposer, TaskDecomposition, Subtask
from .time_allotment import TimeAllotmentAgent, TimeSlot, ScheduledTask
from .event_creator import EventCreator, EventData, CreatedEvent, EventCreationResult
from .main_scheduler import LLMTaskScheduler, SchedulingRequest, SchedulingResult


class TestLLMTaskDecomposer(unittest.TestCase):
    """Test cases for LLM Task Decomposer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.decomposer = LLMTaskDecomposer()
        
        # Mock calendar config
        self.mock_config = {
            "default_work_title": "Work",
            "default_home_title": "Home",
            "calendars": [
                {"id": "work_id", "title": "Work", "writable": True},
                {"id": "home_id", "title": "Home", "writable": True}
            ]
        }
    
    def test_calendar_config_loading(self):
        """Test calendar configuration loading"""
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(self.mock_config)
            
            decomposer = LLMTaskDecomposer()
            self.assertEqual(decomposer.calendar_config, self.mock_config)
    
    def test_get_calendar_id(self):
        """Test getting calendar ID by type"""
        self.decomposer.calendar_config = self.mock_config
        
        work_id = self.decomposer.get_calendar_id("Work")
        home_id = self.decomposer.get_calendar_id("Home")
        invalid_id = self.decomposer.get_calendar_id("Invalid")
        
        self.assertEqual(work_id, "work_id")
        self.assertEqual(home_id, "home_id")
        self.assertIsNone(invalid_id)
    
    def test_extract_json(self):
        """Test JSON extraction from LLM response"""
        # Test pure JSON
        json_text = '{"calendar_type": "Work", "subtasks": null}'
        result = self.decomposer._extract_json(json_text)
        self.assertEqual(result, json_text)
        
        # Test JSON with code fence
        fenced_text = '```json\n{"calendar_type": "Home"}\n```'
        result = self.decomposer._extract_json(fenced_text)
        self.assertEqual(result, '{"calendar_type": "Home"}')
        
        # Test JSON with extra text
        mixed_text = 'Here is the result: {"calendar_type": "Work"}'
        result = self.decomposer._extract_json(mixed_text)
        self.assertEqual(result, '{"calendar_type": "Work"}')
    
    def test_validate_decomposition(self):
        """Test decomposition validation"""
        # Valid decomposition with subtasks
        valid_with_subtasks = {
            "calendar_type": "Work",
            "subtasks": [
                {"title": "Research", "duration_minutes": 60},
                {"title": "Write", "duration_minutes": 120}
            ],
            "total_duration_minutes": 180
        }
        self.decomposer._validate_decomposition(valid_with_subtasks)
        
        # Valid decomposition without subtasks
        valid_simple = {
            "calendar_type": "Home",
            "subtasks": None,
            "total_duration_minutes": 30
        }
        self.decomposer._validate_decomposition(valid_simple)
        
        # Invalid calendar type
        invalid_calendar = {"calendar_type": "Invalid"}
        with self.assertRaises(ValueError):
            self.decomposer._validate_decomposition(invalid_calendar)
        
        # Invalid subtask duration
        invalid_duration = {
            "calendar_type": "Work",
            "subtasks": [{"title": "Task", "duration_minutes": 200}]  # > 180
        }
        with self.assertRaises(ValueError):
            self.decomposer._validate_decomposition(invalid_duration)
    
    @patch('requests.post')
    def test_decompose_task_success(self, mock_post):
        """Test successful task decomposition"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {
                "content": '{"calendar_type": "Work", "subtasks": [{"title": "Research", "duration_minutes": 60}], "total_duration_minutes": 60}'
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.decomposer.decompose_task("Write a paper", "2025-11-01T23:59:00")
        
        self.assertEqual(result.calendar_type, "Work")
        self.assertEqual(len(result.subtasks), 1)
        self.assertEqual(result.subtasks[0].title, "Research")
        self.assertEqual(result.subtasks[0].duration_minutes, 60)


class TestTimeAllotmentAgent(unittest.TestCase):
    """Test cases for Time Allotment Agent"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.agent = TimeAllotmentAgent()
    
    def test_is_holiday(self):
        """Test holiday detection"""
        # Holiday events
        holiday_event1 = {"calendar": "US Holidays"}
        holiday_event2 = {"calendar": "Birthdays"}
        holiday_event3 = {"calendar": "Holiday Calendar"}
        
        # Non-holiday events
        work_event = {"calendar": "Work"}
        home_event = {"calendar": "Home"}
        no_calendar = {}
        
        self.assertTrue(self.agent._is_holiday(holiday_event1))
        self.assertTrue(self.agent._is_holiday(holiday_event2))
        self.assertTrue(self.agent._is_holiday(holiday_event3))
        self.assertFalse(self.agent._is_holiday(work_event))
        self.assertFalse(self.agent._is_holiday(home_event))
        self.assertFalse(self.agent._is_holiday(no_calendar))
    
    @patch('requests.get')
    def test_fetch_events_until_deadline(self, mock_get):
        """Test fetching events until deadline"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "start_iso": "2025-10-15T10:00:00",
                "end_iso": "2025-10-15T11:00:00",
                "calendar": "Work"
            },
            {
                "start_iso": "2025-10-15T12:00:00",
                "end_iso": "2025-10-15T13:00:00",
                "calendar": "US Holidays"
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        events = self.agent._fetch_events_until_deadline("2025-10-20T23:59:00")
        
        # Should exclude holiday event
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["calendar"], "Work")
    
    def test_calculate_free_slots(self):
        """Test free slot calculation"""
        events = [
            {
                "start_iso": "2025-10-15T10:00:00",
                "end_iso": "2025-10-15T11:00:00",
                "calendar": "Work"
            },
            {
                "start_iso": "2025-10-15T14:00:00",
                "end_iso": "2025-10-15T15:00:00",
                "calendar": "Home"
            }
        ]
        
        # Mock current time
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 15, 9, 0)
            mock_datetime.fromisoformat.side_effect = lambda x: datetime.fromisoformat(x)
            
            slots = self.agent._calculate_free_slots(events, "2025-10-15T16:00:00")
            
            # Should have 3 free slots: 9-10, 11-14, 15-16
            self.assertEqual(len(slots), 3)
    
    def test_schedule_tasks_validation(self):
        """Test task scheduling input validation"""
        with self.assertRaises(ValueError):
            self.agent.schedule_tasks(
                task_titles=["Task 1", "Task 2"],
                task_durations=[30],  # Mismatch
                deadline="2025-11-01T23:59:00",
                calendar_type="Work"
            )


class TestEventCreator(unittest.TestCase):
    """Test cases for Event Creator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.creator = EventCreator()
        
        # Mock calendar config
        self.mock_config = {
            "calendars": [
                {"id": "work_id", "title": "Work", "writable": True},
                {"id": "home_id", "title": "Home", "writable": True}
            ]
        }
        self.creator.calendar_config = self.mock_config
    
    def test_generate_event_id(self):
        """Test event ID generation"""
        id1 = self.creator._generate_event_id()
        id2 = self.creator._generate_event_id()
        
        self.assertIsInstance(id1, str)
        self.assertIsInstance(id2, str)
        self.assertNotEqual(id1, id2)
        self.assertTrue(len(id1) > 0)
    
    def test_get_calendar_id(self):
        """Test getting calendar ID"""
        work_id = self.creator._get_calendar_id("Work")
        home_id = self.creator._get_calendar_id("Home")
        invalid_id = self.creator._get_calendar_id("Invalid")
        
        self.assertEqual(work_id, "work_id")
        self.assertEqual(home_id, "home_id")
        self.assertIsNone(invalid_id)
    
    @patch('requests.post')
    def test_create_event_via_api(self, mock_post):
        """Test event creation via API"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "test_event_id",
            "title": "Test Event",
            "start_iso": "2025-10-15T10:00:00",
            "end_iso": "2025-10-15T11:00:00",
            "calendar": "Work"
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        event_data = EventData(
            title="Test Event",
            start_iso="2025-10-15T10:00:00",
            end_iso="2025-10-15T11:00:00",
            notes="Test notes",
            calendar_id="work_id"
        )
        
        result = self.creator._create_event_via_api(event_data)
        
        self.assertEqual(result.event_id, "test_event_id")
        self.assertEqual(result.title, "Test Event")
        self.assertEqual(result.calendar, "Work")
    
    def test_create_main_event(self):
        """Test creating main event"""
        scheduled_task = ScheduledTask(
            task_id=0,
            title="Test Task",
            duration_minutes=30,
            start_iso="2025-10-15T10:00:00",
            end_iso="2025-10-15T10:30:00",
            day="2025-10-15",
            calendar_type="Work"
        )
        
        with patch.object(self.creator, '_create_event_via_api') as mock_create:
            mock_create.return_value = CreatedEvent(
                event_id="test_id",
                title="Test Task",
                start_iso="2025-10-15T10:00:00",
                end_iso="2025-10-15T10:30:00",
                calendar="Work",
                notes="parent_id: NULL; source: LLM_task_scheduling"
            )
            
            result = self.creator.create_main_event("Test Task", scheduled_task)
            
            self.assertEqual(result.event_id, "test_id")
            self.assertIsNone(result.parent_id)
            self.assertIn("parent_id: NULL", result.notes)


class TestMainScheduler(unittest.TestCase):
    """Test cases for Main Scheduler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scheduler = LLMTaskScheduler()
    
    def test_scheduling_request_creation(self):
        """Test scheduling request creation"""
        request = SchedulingRequest(
            task_description="Test task",
            deadline="2025-11-01T23:59:00",
            constraints={"max_tasks_per_day": 2}
        )
        
        self.assertEqual(request.task_description, "Test task")
        self.assertEqual(request.deadline, "2025-11-01T23:59:00")
        self.assertEqual(request.constraints["max_tasks_per_day"], 2)
    
    def test_scheduling_result_creation(self):
        """Test scheduling result creation"""
        result = SchedulingResult(
            success=True,
            main_event=None,
            subtask_events=[],
            total_events_created=0,
            decomposition=None,
            scheduled_tasks=[],
            errors=[],
            warnings=[]
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.total_events_created, 0)
        self.assertEqual(len(result.errors), 0)
    
    @patch.object(LLMTaskScheduler, 'schedule_task')
    def test_simple_task_scheduling(self, mock_schedule):
        """Test simple task scheduling"""
        # Mock the main schedule_task method
        mock_result = SchedulingResult(
            success=True,
            main_event=CreatedEvent(
                event_id="test_id",
                title="Simple Task",
                start_iso="2025-10-15T10:00:00",
                end_iso="2025-10-15T10:30:00",
                calendar="Home",
                notes="parent_id: NULL"
            ),
            subtask_events=[],
            total_events_created=1,
            decomposition=None,
            scheduled_tasks=[],
            errors=[],
            warnings=[]
        )
        mock_schedule.return_value = mock_result
        
        result = self.scheduler.schedule_simple_task(
            "Simple Task",
            "2025-10-15T23:59:00",
            30,
            "Home"
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.total_events_created, 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scheduler = LLMTaskScheduler()
    
    @patch('requests.get')
    @patch('requests.post')
    def test_end_to_end_simple_task(self, mock_post, mock_get):
        """Test end-to-end simple task scheduling"""
        # Mock calendar events API
        mock_events_response = Mock()
        mock_events_response.json.return_value = []
        mock_events_response.raise_for_status.return_value = None
        mock_get.return_value = mock_events_response
        
        # Mock event creation API
        mock_create_response = Mock()
        mock_create_response.json.return_value = {
            "id": "test_event_id",
            "title": "Simple Task",
            "start_iso": "2025-10-15T10:00:00",
            "end_iso": "2025-10-15T10:30:00",
            "calendar": "Home"
        }
        mock_create_response.raise_for_status.return_value = None
        mock_post.return_value = mock_create_response
        
        # Mock current time
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 15, 9, 0)
            mock_datetime.fromisoformat.side_effect = lambda x: datetime.fromisoformat(x)
            
            result = self.scheduler.schedule_simple_task(
                "Simple Task",
                "2025-10-15T23:59:00",
                30,
                "Home"
            )
            
            self.assertTrue(result.success)
            self.assertEqual(result.total_events_created, 1)


def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestLLMTaskDecomposer,
        TestTimeAllotmentAgent,
        TestEventCreator,
        TestMainScheduler,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


def main():
    """Main test runner"""
    print("Running LLM Task Scheduling Component Tests")
    print("=" * 60)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    return success


if __name__ == "__main__":
    main()
