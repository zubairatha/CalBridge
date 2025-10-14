"""
Comprehensive Tests for Smart Task Scheduling Components
Tests each component individually and integration tests.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from user_memory import UserMemory
from task_decomposer import TaskDecomposer
from time_allotter import TimeAllotter
from task_scheduler import TaskScheduler
from smart_scheduler import SmartScheduler


class TestUserMemory(unittest.TestCase):
    """Test UserMemory component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.memory = UserMemory(self.temp_file.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_file.name)
    
    def test_default_memory_structure(self):
        """Test that default memory has correct structure."""
        memory = self.memory.memory
        
        self.assertIn('preferences', memory)
        self.assertIn('recurring_events', memory)
        self.assertIn('calendar_preferences', memory)
        self.assertIn('scheduling_rules', memory)
        self.assertIn('last_updated', memory)
        
        # Check preferences structure
        prefs = memory['preferences']
        self.assertIn('wake_up_time', prefs)
        self.assertIn('sleep_time', prefs)
        self.assertIn('work_hours', prefs)
    
    def test_preference_operations(self):
        """Test getting and setting preferences."""
        # Test getting preference
        wake_time = self.memory.get_preference('preferences.wake_up_time')
        self.assertEqual(wake_time, '06:00')
        
        # Test setting preference
        self.memory.set_preference('preferences.wake_up_time', '07:00')
        self.assertEqual(self.memory.get_preference('preferences.wake_up_time'), '07:00')
        
        # Test nested preference
        self.memory.set_preference('preferences.work_hours.start', '08:00')
        self.assertEqual(self.memory.get_preference('preferences.work_hours.start'), '08:00')
    
    def test_save_and_load_memory(self):
        """Test saving and loading memory from file."""
        # Modify memory
        self.memory.set_preference('preferences.wake_up_time', '08:00')
        
        # Save memory
        self.assertTrue(self.memory.save_memory())
        
        # Create new memory instance (should load from file)
        new_memory = UserMemory(self.temp_file.name)
        self.assertEqual(new_memory.get_preference('preferences.wake_up_time'), '08:00')
    
    def test_get_available_time_slots(self):
        """Test getting available time slots."""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=1)
        
        # Test with no existing events
        events = []
        slots = self.memory.get_available_time_slots(start_date, end_date, events)
        
        # Should have one large slot (minus constraints)
        self.assertGreater(len(slots), 0)
        
        # Test with existing events
        events = [
            {
                'start_iso': (start_date + timedelta(hours=10)).isoformat(),
                'end_iso': (start_date + timedelta(hours=12)).isoformat(),
                'title': 'Test Event'
            }
        ]
        slots = self.memory.get_available_time_slots(start_date, end_date, events)
        
        # Should have slots before and after the event
        self.assertGreater(len(slots), 0)
    
    def test_get_scheduling_constraints(self):
        """Test getting scheduling constraints."""
        constraints = self.memory.get_scheduling_constraints()
        
        self.assertIn('wake_up_time', constraints)
        self.assertIn('sleep_time', constraints)
        self.assertIn('work_hours', constraints)
        self.assertIn('buffer_time_minutes', constraints)


class TestTaskDecomposer(unittest.TestCase):
    """Test TaskDecomposer component."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock calendar cache
        self.mock_calendars = {
            'work': 'work-calendar-id',
            'home': 'home-calendar-id'
        }
    
    @patch('smart_task_scheduling.task_decomposer.TaskDecomposer._load_calendar_cache')
    @patch('smart_task_scheduling.task_decomposer.requests.post')
    def test_decompose_task(self, mock_post, mock_load_cache):
        """Test task decomposition."""
        mock_load_cache.return_value = self.mock_calendars
        
        # Mock Ollama response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'message': {
                'content': json.dumps({
                    'calendar_assignment': 'work',
                    'task_complexity': 'medium',
                    'estimated_total_hours': 2.0,
                    'subtasks': [
                        {
                            'id': 'subtask_1',
                            'title': 'Research requirements',
                            'description': 'Research user requirements',
                            'estimated_hours': 1.0,
                            'difficulty': 'low',
                            'priority': 1,
                            'dependencies': []
                        },
                        {
                            'id': 'subtask_2',
                            'title': 'Design system',
                            'description': 'Design system architecture',
                            'estimated_hours': 1.0,
                            'difficulty': 'high',
                            'priority': 2,
                            'dependencies': ['subtask_1']
                        }
                    ],
                    'notes': 'Test task'
                })
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        decomposer = TaskDecomposer()
        result = decomposer.decompose_task("Build a mobile app")
        
        self.assertEqual(result['calendar_assignment'], 'work')
        self.assertEqual(result['task_complexity'], 'medium')
        self.assertEqual(len(result['subtasks']), 2)
        self.assertEqual(result['calendar_id'], 'work-calendar-id')
    
    @patch('smart_task_scheduling.task_decomposer.TaskDecomposer._load_calendar_cache')
    def test_calendar_assignment_validation(self, mock_load_cache):
        """Test calendar assignment validation."""
        mock_load_cache.return_value = self.mock_calendars
        
        decomposer = TaskDecomposer()
        
        # Test valid calendar IDs
        self.assertEqual(decomposer.get_calendar_id('work'), 'work-calendar-id')
        self.assertEqual(decomposer.get_calendar_id('home'), 'home-calendar-id')
        
        # Test invalid calendar ID
        self.assertIsNone(decomposer.get_calendar_id('nonexistent'))


class TestTimeAllotter(unittest.TestCase):
    """Test TimeAllotter component."""
    
    @patch('smart_task_scheduling.time_allotter.requests.post')
    def test_allot_time_slots(self, mock_post):
        """Test time slot allocation."""
        # Mock Ollama response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'message': {
                'content': json.dumps({
                    'allocations': [
                        {
                            'subtask_id': 'subtask_1',
                            'scheduled_start': '2025-01-15T09:00:00',
                            'scheduled_end': '2025-01-15T11:00:00',
                            'duration_minutes': 120,
                            'slot_used': 0,
                            'reasoning': 'High priority task'
                        }
                    ],
                    'total_scheduled_time': 120,
                    'unscheduled_subtasks': [],
                    'notes': 'All tasks scheduled successfully'
                })
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        allotter = TimeAllotter()
        
        # Mock decomposed task
        decomposed_task = {
            'calendar_assignment': 'work',
            'task_complexity': 'medium',
            'estimated_total_hours': 2.0,
            'subtasks': [
                {
                    'id': 'subtask_1',
                    'title': 'Research requirements',
                    'estimated_hours': 1.0,
                    'priority': 1,
                    'difficulty': 'low'
                }
            ]
        }
        
        # Mock available slots
        available_slots = [
            {
                'start': datetime(2025, 1, 15, 9, 0),
                'end': datetime(2025, 1, 15, 12, 0),
                'duration_minutes': 180
            }
        ]
        
        result = allotter.allot_time_slots(decomposed_task, available_slots)
        
        self.assertIn('allocations', result)
        self.assertEqual(len(result['allocations']), 1)
        self.assertEqual(result['allocations'][0]['subtask_id'], 'subtask_1')


class TestTaskScheduler(unittest.TestCase):
    """Test TaskScheduler component."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.scheduler = TaskScheduler(self.temp_db.name)
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)
    
    def test_database_initialization(self):
        """Test database initialization."""
        # Database should be created with proper tables
        with self.scheduler.db_path.open('rb') as f:
            # Check that file exists and has content
            self.assertGreater(len(f.read()), 0)
    
    def test_create_task(self):
        """Test creating a task with subtasks."""
        decomposed_task = {
            'title': 'Test Task',
            'calendar_assignment': 'work',
            'calendar_id': 'test-calendar-id',
            'task_complexity': 'medium',
            'estimated_total_hours': 2.0,
            'subtasks': [
                {
                    'id': 'subtask_1',
                    'title': 'Subtask 1',
                    'description': 'First subtask',
                    'estimated_hours': 1.0,
                    'priority': 1,
                    'difficulty': 'low'
                },
                {
                    'id': 'subtask_2',
                    'title': 'Subtask 2',
                    'description': 'Second subtask',
                    'estimated_hours': 1.0,
                    'priority': 2,
                    'difficulty': 'medium'
                }
            ],
            'notes': 'Test task notes'
        }
        
        task_id, subtask_ids = self.scheduler.create_task(decomposed_task)
        
        self.assertIsNotNone(task_id)
        self.assertEqual(len(subtask_ids), 2)
        
        # Verify task was created
        task = self.scheduler.get_task(task_id)
        self.assertIsNotNone(task)
        self.assertEqual(task['title'], 'Test Task')
        self.assertEqual(len(task['subtasks']), 2)
    
    def test_get_all_tasks(self):
        """Test getting all tasks."""
        # Create a test task
        decomposed_task = {
            'title': 'Test Task for List',
            'calendar_assignment': 'work',
            'subtasks': []
        }
        
        self.scheduler.create_task(decomposed_task)
        
        # Get all tasks
        tasks = self.scheduler.get_all_tasks()
        self.assertGreater(len(tasks), 0)
    
    def test_update_subtask_status(self):
        """Test updating subtask status."""
        # Create a task with subtask
        decomposed_task = {
            'title': 'Test Task for Update',
            'calendar_assignment': 'work',
            'subtasks': [
                {
                    'id': 'subtask_1',
                    'title': 'Subtask for Update',
                    'estimated_hours': 1.0,
                    'priority': 1,
                    'difficulty': 'low'
                }
            ]
        }
        
        task_id, subtask_ids = self.scheduler.create_task(decomposed_task)
        subtask_id = subtask_ids[0]
        
        # Update status
        success = self.scheduler.update_subtask_status(
            subtask_id, 'completed', 
            datetime.now(), datetime.now()
        )
        
        self.assertTrue(success)
        
        # Verify update
        task = self.scheduler.get_task(task_id)
        self.assertEqual(task['subtasks'][0]['status'], 'completed')
    
    def test_delete_task(self):
        """Test deleting a task."""
        # Create a task
        decomposed_task = {
            'title': 'Task to Delete',
            'calendar_assignment': 'work',
            'subtasks': []
        }
        
        task_id, _ = self.scheduler.create_task(decomposed_task)
        
        # Delete task
        success = self.scheduler.delete_task(task_id)
        self.assertTrue(success)
        
        # Verify deletion
        task = self.scheduler.get_task(task_id)
        self.assertIsNone(task)


class TestSmartScheduler(unittest.TestCase):
    """Test SmartScheduler integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.temp_memory = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_memory.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        os.unlink(self.temp_db.name)
        os.unlink(self.temp_memory.name)
    
    @patch('smart_task_scheduling.task_decomposer.requests.post')
    @patch('smart_task_scheduling.time_allotter.requests.post')
    @patch('smart_task_scheduling.time_allotter.requests.get')
    def test_complete_scheduling_workflow(self, mock_get, mock_time_post, mock_decomp_post):
        """Test complete scheduling workflow."""
        # Mock calendar events response
        mock_get_response = MagicMock()
        mock_get_response.json.return_value = []
        mock_get_response.raise_for_status.return_value = None
        mock_get.return_value = mock_get_response
        
        # Mock task decomposition response
        mock_decomp_response = MagicMock()
        mock_decomp_response.json.return_value = {
            'message': {
                'content': json.dumps({
                    'calendar_assignment': 'work',
                    'task_complexity': 'medium',
                    'estimated_total_hours': 2.0,
                    'subtasks': [
                        {
                            'id': 'subtask_1',
                            'title': 'Research',
                            'estimated_hours': 1.0,
                            'priority': 1,
                            'difficulty': 'low',
                            'dependencies': []
                        }
                    ],
                    'notes': 'Test task'
                })
            }
        }
        mock_decomp_response.raise_for_status.return_value = None
        mock_decomp_post.return_value = mock_decomp_response
        
        # Mock time allocation response
        mock_time_response = MagicMock()
        mock_time_response.json.return_value = {
            'message': {
                'content': json.dumps({
                    'allocations': [],
                    'total_scheduled_time': 0,
                    'unscheduled_subtasks': ['subtask_1'],
                    'notes': 'No available time slots'
                })
            }
        }
        mock_time_response.raise_for_status.return_value = None
        mock_time_post.return_value = mock_time_response
        
        scheduler = SmartScheduler(self.temp_db.name, self.temp_memory.name)
        
        result = scheduler.schedule_task("Test task", auto_create_events=False)
        
        self.assertTrue(result['success'])
        self.assertIn('task_id', result)
        self.assertIn('decomposed_task', result)
        self.assertIn('time_allocation', result)


if __name__ == '__main__':
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestUserMemory))
    test_suite.addTest(unittest.makeSuite(TestTaskDecomposer))
    test_suite.addTest(unittest.makeSuite(TestTimeAllotter))
    test_suite.addTest(unittest.makeSuite(TestTaskScheduler))
    test_suite.addTest(unittest.makeSuite(TestSmartScheduler))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
