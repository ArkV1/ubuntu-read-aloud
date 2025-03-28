#!/usr/bin/env python3
import unittest
from unittest.mock import Mock, patch, MagicMock
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from src.ui.app_window import ReadAloudWindow
from src.ui.app import ReadAloudApp

class TestReadAloudWindow(unittest.TestCase):
    """Test cases for the main application window"""
    
    @patch('src.ui.app_window.TTSEngine')
    @patch('src.ui.app_window.TextSelector')
    def setUp(self, MockTextSelector, MockTTSEngine):
        """Set up the test case"""
        # Mock the application
        self.mock_app = Mock()
        self.mock_app.add_accelerator = Mock()
        self.mock_app.add_action = Mock()
        
        # Mock TTS engine and text selector
        self.mock_tts = MockTTSEngine.return_value
        self.mock_tts.get_available_voices.return_value = [('voice1', 'Voice 1')]
        self.mock_text_selector = MockTextSelector.return_value
        
        # Create window with mocks
        with patch('gi.repository.Gtk.ApplicationWindow.__init__', return_value=None):
            self.window = ReadAloudWindow(self.mock_app)
            
        # Mock the application access in the window
        self.window.get_application = Mock(return_value=self.mock_app)
        
        # Mock UI elements that may be None in test environment
        self.window.text_buffer = Mock()
        self.window.text_buffer.get_text = Mock(return_value="Test text")
        self.window.text_buffer.get_bounds = Mock(return_value=(Mock(), Mock()))
        self.window.statusbar = Mock()
        self.window.statusbar.push = Mock()
        self.window.read_button = Mock()
        
    def test_initialization(self):
        """Test window initialization"""
        self.assertEqual(self.window.tts_engine, self.mock_tts)
        self.assertEqual(self.window.text_selector, self.mock_text_selector)
        
    @patch('threading.Thread')
    def test_get_text_clicked(self, MockThread):
        """Test getting text button click"""
        # Setup
        mock_thread = Mock()
        MockThread.return_value = mock_thread
        
        # Call the method
        self.window.on_get_text_clicked(None)
        
        # Verify thread was started
        MockThread.assert_called_once()
        mock_thread.start.assert_called_once()
        
    def test_update_text_view_with_text(self):
        """Test updating text view with text"""
        # Call the method
        self.window.update_text_view("Sample text")
        
        # Verify text was set and status updated
        self.window.text_buffer.set_text.assert_called_once_with("Sample text")
        self.window.statusbar.push.assert_called_once()
        
    def test_update_text_view_no_text(self):
        """Test updating text view with no text"""
        # Call the method
        self.window.update_text_view("")
        
        # Verify status updated with error message
        self.window.statusbar.push.assert_called_once_with(0, "No text selected")
        
    def test_read_clicked_with_text(self):
        """Test reading text when text exists"""
        # Call the method
        self.window.on_read_clicked(None)
        
        # Verify behavior
        self.window.read_button.set_sensitive.assert_called_once_with(False)
        self.window.statusbar.push.assert_called_once_with(0, "Reading...")
        self.mock_tts.speak.assert_called_once()
        
    def test_read_clicked_no_text(self):
        """Test reading text when no text exists"""
        # Setup
        self.window.text_buffer.get_text.return_value = ""
        
        # Call the method
        self.window.on_read_clicked(None)
        
        # Verify behavior
        self.window.statusbar.push.assert_called_once_with(0, "No text to read")
        self.mock_tts.speak.assert_not_called()
        
    def test_stop_clicked(self):
        """Test stop button click"""
        # Call the method
        self.window.on_stop_clicked(None)
        
        # Verify behavior
        self.mock_tts.stop.assert_called_once()
        self.window.read_button.set_sensitive.assert_called_once_with(True)
        self.window.statusbar.push.assert_called_once_with(0, "Stopped reading")
        
    def test_voice_changed(self):
        """Test voice selection changed"""
        # Setup
        combo = Mock()
        combo.get_active_id.return_value = 'voice1'
        
        # Call the method
        self.window.on_voice_changed(combo)
        
        # Verify behavior
        self.mock_tts.set_voice.assert_called_once_with('voice1')
        
    def test_rate_changed(self):
        """Test speech rate changed"""
        # Setup
        scale = Mock()
        scale.get_value.return_value = 200
        
        # Call the method
        self.window.on_rate_changed(scale)
        
        # Verify behavior
        self.mock_tts.set_rate.assert_called_once_with(200)
        
class TestReadAloudApp(unittest.TestCase):
    """Test cases for the main application"""
    
    @patch('gi.repository.Gtk.Application.__init__')
    def setUp(self, mock_init):
        """Set up the test case"""
        mock_init.return_value = None
        self.app = ReadAloudApp()
        
    @patch('src.ui.app.ReadAloudWindow')
    def test_get_window_new(self, MockWindow):
        """Test getting a new window"""
        # Setup
        self.app.get_active_window = Mock(return_value=None)
        mock_window = Mock()
        MockWindow.return_value = mock_window
        
        # Call the method
        window = self.app.get_window()
        
        # Verify behavior
        self.assertEqual(window, mock_window)
        MockWindow.assert_called_once_with(self.app)
        
    @patch('src.ui.app.ReadAloudWindow')
    def test_get_window_existing(self, MockWindow):
        """Test getting an existing window"""
        # Setup
        mock_window = Mock()
        self.app.get_active_window = Mock(return_value=mock_window)
        
        # Call the method
        window = self.app.get_window()
        
        # Verify behavior
        self.assertEqual(window, mock_window)
        MockWindow.assert_not_called()
        
    @patch('src.ui.app.ReadAloudApp.get_window')
    def test_on_read_selected(self, mock_get_window):
        """Test reading selected text from indicator menu"""
        # Setup
        mock_window = Mock()
        mock_get_window.return_value = mock_window
        
        # Call the method
        with patch('gi.repository.GLib.timeout_add') as mock_timeout:
            self.app._on_read_selected(None)
        
        # Verify behavior
        mock_window.on_get_text_clicked.assert_called_once_with(None)
        mock_timeout.assert_called_once()
        
    @patch('src.ui.app.ReadAloudApp.get_window')
    def test_on_show_window(self, mock_get_window):
        """Test showing window from indicator menu"""
        # Setup
        mock_window = Mock()
        mock_get_window.return_value = mock_window
        
        # Call the method
        self.app._on_show_window(None)
        
        # Verify behavior
        mock_window.present.assert_called_once()
        
    def test_on_quit(self):
        """Test quitting from indicator menu"""
        # Setup
        self.app.quit = Mock()
        
        # Call the method
        self.app._on_quit(None)
        
        # Verify behavior
        self.app.quit.assert_called_once()
        
if __name__ == '__main__':
    unittest.main() 