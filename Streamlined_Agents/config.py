"""
Configuration for Streamlined Agents Application
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ollama Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = "qwen2.5:14b-instruct-q4_K_M"

# Application Configuration
APP_NAME = "Streamlined Agents"
VERSION = "1.0.0"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
