"""
Configuration file for pytest
"""
import os
import sys
import pytest

# Add the parent directory to the path to import src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Skip tests requiring display if DISPLAY isn't available
def pytest_configure(config):
    """Configure pytest environment"""
    # Check if display is available
    if 'DISPLAY' not in os.environ:
        # Add marker for tests requiring a display
        config.addinivalue_line("markers", "requires_display: mark test as requiring a display")

def pytest_collection_modifyitems(items):
    """Skip tests that require display if DISPLAY isn't available"""
    if 'DISPLAY' not in os.environ:
        skip_display = pytest.mark.skip(reason="Test requires a display")
        for item in items:
            if "requires_display" in item.keywords:
                item.add_marker(skip_display) 