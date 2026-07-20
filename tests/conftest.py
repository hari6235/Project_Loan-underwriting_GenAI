"""
Pytest configuration file - Sets up Python path and shared fixtures.

This file is automatically loaded by pytest and ensures all project modules
can be imported correctly.
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
