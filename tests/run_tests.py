#!/usr/bin/env python3
"""
Test runner for Read Aloud application
"""
import unittest
import sys
import os
import logging

def main():
    """Run all tests and return exit code"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add parent directory to path to import src modules correctly
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Discover and run tests
    test_suite = unittest.defaultTestLoader.discover(
        start_dir=os.path.dirname(__file__),
        pattern='test_*.py'
    )
    
    # Create test runner
    test_runner = unittest.TextTestRunner(verbosity=2)
    
    # Run tests
    result = test_runner.run(test_suite)
    
    # Return exit code (0 if successful, 1 if failed)
    return not result.wasSuccessful()

if __name__ == '__main__':
    sys.exit(main()) 