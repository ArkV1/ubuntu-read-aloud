"""
Main module for the tests package.
This allows running the tests with: python -m tests
"""
import sys
from .run_tests import main

if __name__ == '__main__':
    sys.exit(main()) 