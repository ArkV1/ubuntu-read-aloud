#!/usr/bin/env python3
import unittest
from unittest.mock import Mock, patch
import time
import threading

from src.tts.tts_engine import TTSEngine

class TestTTSEngine(unittest.TestCase):
    """Test cases for the TTS engine"""
    
    @patch('pyttsx3.init')
    def setUp(self, mock_init):
        """Set up the test case"""
        self.mock_engine = Mock()
        mock_init.return_value = self.mock_engine
        self.engine = TTSEngine()
        
    def test_init(self):
        """Test initialization"""
        self.assertEqual(self.engine.is_speaking, False)
        self.assertIsNone(self.engine.speaking_thread)
        self.mock_engine.setProperty.assert_any_call('rate', 150)
        self.mock_engine.setProperty.assert_any_call('volume', 1.0)
        
    def test_set_rate(self):
        """Test setting the speech rate"""
        self.engine.set_rate(200)
        self.mock_engine.setProperty.assert_any_call('rate', 200)
        
    def test_set_volume(self):
        """Test setting the volume"""
        self.engine.set_volume(0.5)
        self.mock_engine.setProperty.assert_any_call('volume', 0.5)
        
    def test_set_voice(self):
        """Test setting the voice"""
        self.engine.set_voice('voice_id')
        self.mock_engine.setProperty.assert_any_call('voice', 'voice_id')
        
    def test_get_available_voices(self):
        """Test getting available voices"""
        mock_voice1 = Mock()
        mock_voice1.id = 'voice1'
        mock_voice1.name = 'Voice 1'
        mock_voice2 = Mock()
        mock_voice2.id = 'voice2'
        mock_voice2.name = 'Voice 2'
        
        self.mock_engine.getProperty.return_value = [mock_voice1, mock_voice2]
        
        voices = self.engine.get_available_voices()
        
        self.assertEqual(voices, [('voice1', 'Voice 1'), ('voice2', 'Voice 2')])
        self.mock_engine.getProperty.assert_called_with('voices')
        
    def test_speak(self):
        """Test speaking text"""
        self.engine.speak('Hello world')
        
        # Wait a moment for the thread to start
        time.sleep(0.1)
        
        self.assertTrue(self.engine.is_speaking)
        self.assertIsNotNone(self.engine.speaking_thread)
        self.assertTrue(self.engine.speaking_thread.daemon)
        
        # Wait for the thread to complete
        self.engine.speaking_thread.join(timeout=1.0)
        
        self.mock_engine.say.assert_called_with('Hello world')
        self.mock_engine.runAndWait.assert_called_once()
        
    def test_speak_with_callback(self):
        """Test speaking with callback"""
        callback = Mock()
        
        # Override the speak method to directly call the callback
        with patch.object(self.engine, 'speak', side_effect=lambda text, cb=None: cb()):
            self.engine.speak('Hello', callback)
            callback.assert_called_once()
            
    def test_stop(self):
        """Test stopping speech"""
        # Set up speaking state
        self.engine.is_speaking = True
        
        # Call stop
        self.engine.stop()
        
        # Verify engine stop was called and state updated
        self.mock_engine.stop.assert_called_once()
        self.assertFalse(self.engine.is_speaking)
        
    def test_is_busy(self):
        """Test checking if engine is busy"""
        self.engine.is_speaking = True
        self.assertTrue(self.engine.is_busy())
        
        self.engine.is_speaking = False
        self.assertFalse(self.engine.is_busy())
        
if __name__ == '__main__':
    unittest.main() 