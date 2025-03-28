#!/usr/bin/env python3
import unittest
from unittest.mock import Mock, patch
import sys
import argparse

from src.main import parse_args, setup_logging, main

class TestCommandLine(unittest.TestCase):
    """Test cases for command line interface"""
    
    def test_parse_args_default(self):
        """Test parsing command line arguments with defaults"""
        # Save original arguments
        original_argv = sys.argv
        
        try:
            # Set test arguments
            sys.argv = ['readaloud']
            
            # Parse arguments
            args = parse_args()
            
            # Verify defaults
            self.assertFalse(args.verbose)
        finally:
            # Restore original arguments
            sys.argv = original_argv
    
    def test_parse_args_verbose(self):
        """Test parsing command line arguments with verbose flag"""
        # Save original arguments
        original_argv = sys.argv
        
        try:
            # Set test arguments
            sys.argv = ['readaloud', '--verbose']
            
            # Parse arguments
            args = parse_args()
            
            # Verify verbose flag
            self.assertTrue(args.verbose)
        finally:
            # Restore original arguments
            sys.argv = original_argv
    
    @patch('logging.basicConfig')
    def test_setup_logging_default(self, mock_basic_config):
        """Test setting up logging with default values"""
        # Call setup_logging with default verbose=False
        setup_logging()
        
        # Verify logging was configured
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        self.assertEqual(kwargs['level'], unittest.mock.ANY)
        
    @patch('logging.basicConfig')
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test setting up logging with verbose=True"""
        # Call setup_logging with verbose=True
        setup_logging(verbose=True)
        
        # Verify logging was configured with DEBUG level
        mock_basic_config.assert_called_once()
        args, kwargs = mock_basic_config.call_args
        self.assertEqual(kwargs['level'], unittest.mock.ANY)
    
    @patch('src.main.parse_args')
    @patch('src.main.setup_logging')
    @patch('src.main.ReadAloudApp')
    def test_main(self, MockApp, mock_setup_logging, mock_parse_args):
        """Test main function"""
        # Setup mocks
        mock_args = Mock()
        mock_args.verbose = True
        mock_parse_args.return_value = mock_args
        
        mock_app = Mock()
        mock_app.run.return_value = 0
        MockApp.return_value = mock_app
        
        # Call main
        result = main()
        
        # Verify behavior
        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with(True)
        MockApp.assert_called_once()
        mock_app.run.assert_called_once_with(sys.argv)
        self.assertEqual(result, 0)
        
if __name__ == '__main__':
    unittest.main() 