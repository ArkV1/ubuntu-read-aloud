#!/usr/bin/env python3
import unittest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import time

from src.utils.text_selection import TextSelector

class TestTextSelector(unittest.TestCase):
    """Test cases for text selection utility"""
    
    def setUp(self):
        """Set up the test case"""
        self.selector = TextSelector()
        
    @patch('pyperclip.paste')
    @patch('pyperclip.copy')
    @patch('src.utils.text_selection.TextSelector._simulate_copy')
    def test_get_selected_text(self, mock_simulate, mock_copy, mock_paste):
        """Test getting selected text"""
        # Mock the clipboard operations
        mock_paste.side_effect = ['previous_content', 'selected text']
        
        # Call the method
        result = self.selector.get_selected_text()
        
        # Verify behavior
        self.assertEqual(result, 'selected text')
        mock_simulate.assert_called_once()
        mock_copy.assert_called_once_with('previous_content')
        self.assertEqual(mock_paste.call_count, 2)
        
    @patch('pyperclip.paste')
    @patch('src.utils.text_selection.TextSelector._simulate_copy')
    def test_get_selected_text_no_previous(self, mock_simulate, mock_paste):
        """Test getting selected text with no previous clipboard content"""
        # Mock the clipboard operations
        mock_paste.side_effect = [None, 'selected text']
        
        # Call the method
        result = self.selector.get_selected_text()
        
        # Verify behavior
        self.assertEqual(result, 'selected text')
        mock_simulate.assert_called_once()
        
    @patch('pyperclip.paste')
    @patch('src.utils.text_selection.TextSelector._simulate_copy')
    def test_get_selected_text_exception(self, mock_simulate, mock_paste):
        """Test getting selected text when an exception occurs"""
        # Make the simulation raise an exception
        mock_simulate.side_effect = Exception("Test error")
        
        # Call the method
        with patch('logging.error') as mock_log:
            result = self.selector.get_selected_text()
        
        # Verify behavior
        self.assertEqual(result, "")
        mock_simulate.assert_called_once()
        mock_log.assert_called_once()
        
    @patch('subprocess.run')
    def test_simulate_copy_xdotool(self, mock_run):
        """Test simulating copy with xdotool"""
        # Call the method
        self.selector._simulate_copy()
        
        # Verify xdotool was called
        mock_run.assert_called_once_with(["xdotool", "key", "ctrl+c"], check=True)
        
    @patch('subprocess.run')
    @patch('src.utils.text_selection.display')
    def test_simulate_copy_fallback_to_x11(self, mock_display, mock_run):
        """Test simulating copy with X11 fallback"""
        # Make subprocess.run raise an exception to force X11 fallback
        mock_run.side_effect = subprocess.SubprocessError()
        
        # Mock X11 objects
        mock_display_instance = MagicMock()
        mock_display.Display.return_value = mock_display_instance
        mock_root = mock_display_instance.screen.return_value.root
        
        # Call the method
        self.selector._simulate_copy()
        
        # Verify X11 was used
        mock_display.Display.assert_called_once()
        self.assertEqual(mock_root.send_event.call_count, 4)  # 4 key events
        mock_display_instance.ungrab_keyboard.assert_called_once()
        mock_display_instance.flush.assert_called_once()
    
    @patch('subprocess.run')
    def test_get_primary_selection(self, mock_run):
        """Test getting text from primary selection"""
        # Mock subprocess.run
        mock_process = MagicMock()
        mock_process.stdout = "primary selection text"
        mock_run.return_value = mock_process
        
        # Call the method
        result = self.selector.get_primary_selection()
        
        # Verify behavior
        self.assertEqual(result, "primary selection text")
        mock_run.assert_called_once_with(
            ["xclip", "-o", "-selection", "primary"],
            capture_output=True,
            text=True,
            check=True
        )
        
    @patch('subprocess.run')
    def test_get_primary_selection_exception(self, mock_run):
        """Test getting primary selection when an exception occurs"""
        # Make subprocess.run raise an exception
        mock_run.side_effect = subprocess.SubprocessError()
        
        # Call the method
        with patch('logging.error') as mock_log:
            result = self.selector.get_primary_selection()
        
        # Verify behavior
        self.assertEqual(result, "")
        mock_log.assert_called_once()
        
if __name__ == '__main__':
    unittest.main() 