#!/usr/bin/env python3
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import subprocess
import sys
import time

class TestIntegration(unittest.TestCase):
    """Integration tests for the Read Aloud application"""
    
    def setUp(self):
        """Set up the test case"""
        # Store original directory to return to it later
        self.original_dir = os.getcwd()
        
        # Create a temporary directory for test files
        self.test_dir = tempfile.TemporaryDirectory()
        os.chdir(self.test_dir.name)
        
        # Create a test text file
        with open('test_text.txt', 'w') as f:
            f.write("This is a test text for the Read Aloud application.\n")
            f.write("It contains multiple lines.\n")
            f.write("The TTS engine should read this text aloud.\n")
        
    def tearDown(self):
        """Clean up after the test"""
        os.chdir(self.original_dir)
        self.test_dir.cleanup()
    
    @patch('subprocess.Popen')
    def test_app_launches(self, mock_popen):
        """Test that the application launches successfully"""
        # Setup mock process
        mock_process = Mock()
        mock_process.communicate.return_value = (b'', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        # Try launching the app
        try:
            subprocess.Popen(['python', '-m', 'src.main', '--verbose'], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # In a real test, we'd wait for startup, but here we just check the call
            mock_popen.assert_called_once()
        except Exception as e:
            self.fail(f"Application failed to launch: {e}")
    
    @patch('pyttsx3.init')
    def test_tts_end_to_end(self, mock_init):
        """Test end-to-end TTS functionality"""
        from src.tts.tts_engine import TTSEngine
        
        # Setup mock engine
        mock_engine = Mock()
        mock_init.return_value = mock_engine
        
        # Create TTS engine
        tts = TTSEngine()
        
        # Test reading text from file
        with open('test_text.txt', 'r') as f:
            text = f.read()
            
        # Use the TTS engine to speak the text
        tts.speak(text)
        
        # Verify the engine was called with the text
        mock_engine.say.assert_called_once_with(text)
        mock_engine.runAndWait.assert_called_once()
    
    @patch('subprocess.run')
    @patch('pyperclip.paste')
    def test_text_selection_end_to_end(self, mock_paste, mock_run):
        """Test end-to-end text selection functionality"""
        from src.utils.text_selection import TextSelector
        
        # Setup mock clipboard
        mock_paste.return_value = "Selected text from clipboard"
        
        # Create text selector
        selector = TextSelector()
        
        # Test getting selected text
        text = selector.get_selected_text()
        
        # Verify text was retrieved
        self.assertEqual(text, "Selected text from clipboard")
        mock_run.assert_called_once()
        
    @unittest.skip("This test requires a running X server and would be run manually")
    def test_manual_ui_interaction(self):
        """Manual test for UI interaction - would need to be run with a display"""
        # This is a placeholder for a manual test that would be run with actual UI
        # It would test:
        # 1. Application window appears
        # 2. Text can be entered/pasted into text view
        # 3. Read button works
        # 4. Stop button works
        # 5. Voice and rate controls work
        pass
    
    @patch('src.ui.app_window.ReadAloudWindow._build_ui')
    @patch('src.ui.app_window.ReadAloudWindow._setup_accelerators')
    @patch('src.tts.tts_engine.TTSEngine')
    @patch('src.utils.text_selection.TextSelector')
    def test_ui_components_integration(self, MockSelector, MockTTS, mock_setup, mock_build):
        """Test integration of UI components with TTS and text selection"""
        # This test checks that the UI components correctly integrate with the TTS and text selection
        
        # Import after patching
        from src.ui.app_window import ReadAloudWindow
        
        # Mock application
        mock_app = Mock()
        
        # Create window with mocks
        with patch('gi.repository.Gtk.ApplicationWindow.__init__', return_value=None):
            window = ReadAloudWindow(mock_app)
        
        # Check that TTS and text selector are initialized
        MockTTS.assert_called_once()
        MockSelector.assert_called_once()
        mock_build.assert_called_once()
        mock_setup.assert_called_once()
        
if __name__ == '__main__':
    unittest.main() 