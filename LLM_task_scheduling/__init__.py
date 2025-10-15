# LLM Task Scheduling Module
"""
A smart task scheduling system that uses LLM to decompose tasks and schedule them
into calendar events with proper time management.
"""

__version__ = "1.0.0"
__author__ = "LLM Task Scheduler"

from .llm_decomposer import LLMTaskDecomposer
from .time_allotment import TimeAllotmentAgent
from .event_creator import EventCreator
from .main_scheduler import LLMTaskScheduler

__all__ = [
    "LLMTaskDecomposer",
    "TimeAllotmentAgent", 
    "EventCreator",
    "LLMTaskScheduler"
]
