import pyttsx3
import threading
import logging
import time
import subprocess
import shlex
import os

class TTSEngine:
    """Text-to-Speech engine interface using pyttsx3"""
    
    def __init__(self):
        self._initialize_engine()
        self.speaking_thread = None
        self.is_speaking = False
        self.paused = False
        self._current_text = None
        self._current_position = 0
        self._current_callback = None
        self._saved_settings = {}
        
        # Check if direct speech is available and use it by default
        self.use_direct_speech = self._check_direct_speech_available()
        if self.use_direct_speech:
            logging.debug("Direct speech is available, using as primary TTS method")
        else:
            logging.debug("Direct speech is not available, using pyttsx3")
            
        self.direct_speech_process = None
        
    def _initialize_engine(self):
        """Initialize or reinitialize the TTS engine"""
        try:
            # Force cleanup of any existing engines
            if hasattr(self, 'engine'):
                # Try to disconnect any callbacks to avoid memory leaks
                try:
                    self.engine.stop()
                    # Sleep just a tiny bit to ensure the engine has stopped
                    time.sleep(0.1)
                except Exception as e:
                    logging.debug(f"Ignorable error during engine stop: {e}")
                    
                # Set to None to help garbage collection
                self.engine = None
                
            # Initialize a fresh engine
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 150)
            self.engine.setProperty('volume', 1.0)
            logging.debug("TTS engine initialized")
            return True
        except Exception as e:
            logging.error(f"Error initializing TTS engine: {e}")
            self.use_direct_speech = True  # Fall back to direct speech
            logging.debug("Falling back to direct speech synthesis")
            return False
        
    def set_rate(self, rate):
        """Set the speech rate (words per minute)"""
        try:
            # Store the rate setting regardless of engine state
            if not hasattr(self, '_saved_settings') or self._saved_settings is None:
                self._saved_settings = {}
            self._saved_settings['rate'] = rate
            
            # Set pyttsx3 rate if engine is available
            if hasattr(self, 'engine') and self.engine:
                self.engine.setProperty('rate', rate)
                logging.debug(f"TTS engine rate set to {rate}")
        except Exception as e:
            logging.error(f"Error setting TTS rate: {e}")
            # Still save the setting even if engine failed
            if not hasattr(self, '_saved_settings') or self._saved_settings is None:
                self._saved_settings = {}
            self._saved_settings['rate'] = rate
        
    def set_volume(self, volume):
        """Set the speech volume (0.0 to 1.0)"""
        try:
            # Store the volume setting regardless of engine state
            if not hasattr(self, '_saved_settings') or self._saved_settings is None:
                self._saved_settings = {}
            self._saved_settings['volume'] = volume
            
            # Set pyttsx3 volume if engine is available
            if hasattr(self, 'engine') and self.engine:
                self.engine.setProperty('volume', volume)
                logging.debug(f"TTS engine volume set to {volume}")
        except Exception as e:
            logging.error(f"Error setting volume: {e}")
            # Still save the setting even if engine failed
            if not hasattr(self, '_saved_settings') or self._saved_settings is None:
                self._saved_settings = {}
            self._saved_settings['volume'] = volume
    
    def set_voice(self, voice_id=None):
        """Set the voice to use"""
        if voice_id:
            self.engine.setProperty('voice', voice_id)
    
    def get_available_voices(self):
        """Get list of available voices"""
        try:
            voices = self.engine.getProperty('voices')
            return [(voice.id, voice.name) for voice in voices]
        except Exception as e:
            logging.error(f"Error getting voices: {e}")
            # Try to reinitialize engine and try again
            if self._initialize_engine():
                try:
                    voices = self.engine.getProperty('voices')
                    return [(voice.id, voice.name) for voice in voices]
                except Exception as e2:
                    logging.error(f"Error getting voices after reinitialization: {e2}")
            return []
        
    def speak(self, text, callback=None):
        """Speak the given text in a separate thread"""
        logging.debug(f"Speak method called with {len(text)} characters of text")
        
        # Always stop any ongoing speech first
        if self.is_speaking:
            logging.debug("Engine was speaking, stopping first")
            self.stop()
            # Give a moment for the engine to fully stop
            time.sleep(0.1)
        
        # If the engine seems stuck, reinitialize it
        if self.is_speaking:
            logging.warning("Engine still marked as speaking after stop, reinitializing")
            self._initialize_engine()
            self.is_speaking = False
        
        # Track our state regardless of which method we use
        self.is_speaking = True
        self.paused = False
        self._current_text = text
        self._current_position = 0
        self._current_callback = callback
        
        # Update saved settings for possible direct speech use
        try:
            if self.engine:
                self._saved_settings = {
                    'rate': self.engine.getProperty('rate'),
                    'volume': self.engine.getProperty('volume'),
                    'voice': self.engine.getProperty('voice')
                }
                logging.debug(f"Saved settings: rate={self._saved_settings.get('rate')}, volume={self._saved_settings.get('volume')}")
        except Exception as e:
            logging.error(f"Failed to save engine settings: {e}")
            # Initialize default settings if we couldn't get them from the engine
            if not self._saved_settings:
                self._saved_settings = {
                    'rate': 150,
                    'volume': 0.15  # Default to 15% volume
                }
                logging.debug(f"Using default settings: {self._saved_settings}")
        
        # If direct speech mode is enabled, use that instead of pyttsx3
        if self.use_direct_speech:
            logging.debug("Using direct speech mode")
            success = self._direct_speech(text, callback)
            if success:
                return
            
            # If direct speech failed, try to recover with pyttsx3
            logging.debug("Direct speech failed, trying to recover with pyttsx3")
            self.use_direct_speech = False
            self._initialize_engine()
        
        # Try a quick diagnostic test of the engine
        try:
            current_volume = self.engine.getProperty('volume')
            current_rate = self.engine.getProperty('rate')
            logging.debug(f"Current engine settings - volume: {current_volume}, rate: {current_rate}")
        except Exception as e:
            logging.error(f"Engine properties check failed: {e}")
            logging.debug("Engine failed property check, switching to direct speech")
            self.use_direct_speech = True
            success = self._direct_speech(text, callback)
            if success:
                return
            
            # If we get here, both methods failed
            logging.error("Both pyttsx3 and direct speech failed")
            if callback:
                callback()  # Ensure callback happens
            return
        
        def speak_thread():
            """Thread function for speaking text"""
            finish_callback_called = False
            speech_started = False
            
            try:
                logging.debug("Speech thread started")
                
                # Attempt to detect bad engine state and reinitialize if needed
                if not hasattr(self.engine, 'proxy') or getattr(self.engine.proxy, '_driver', None) is None:
                    logging.warning("TTS engine seems to be in bad state, reinitializing")
                    if not self._initialize_engine():
                        # Engine reinitialization failed, switch to direct speech
                        logging.debug("Engine reinitialization failed, switching to direct speech")
                        self.use_direct_speech = True
                        success = self._direct_speech(text, callback)
                        if success:
                            return
                    
                    # Restore settings
                    if self._saved_settings:
                        for key, value in self._saved_settings.items():
                            if value is not None:
                                self.engine.setProperty(key, value)
                
                def on_word(name, location, length):
                    """Keep track of position in text for pause/resume"""
                    nonlocal speech_started
                    speech_started = True
                    if not self.paused:
                        self._current_position = location
                
                def on_started():
                    """Called when speech starts"""
                    nonlocal speech_started
                    speech_started = True
                    logging.debug("Speech started")
                
                def on_finished():
                    """Called when speech is finished"""
                    nonlocal finish_callback_called
                    if not finish_callback_called:
                        finish_callback_called = True
                        self.is_speaking = False
                        self.paused = False
                        logging.debug("Speech finished callback triggered")
                        if callback:
                            callback()
                
                try:
                    # Connect event handlers
                    self.engine.connect('started-word', on_word)
                    self.engine.connect('started-utterance', lambda name: on_started())
                    self.engine.connect('finished-utterance', lambda name, completed: on_finished())
                    logging.debug("Event handlers connected")
                except Exception as e:
                    logging.error(f"Failed to connect event handlers: {e}")
                
                # Make sure settings are applied before speaking
                current_volume = self.engine.getProperty('volume')
                current_rate = self.engine.getProperty('rate')
                
                # Log active settings for debugging
                logging.debug(f"Speaking with volume={current_volume}, rate={current_rate}")
                
                # Try direct espeak as a fallback since pyttsx3 fails after first use
                if not self.use_direct_speech:
                    logging.debug("Using direct speech as more reliable method")
                    success = self._direct_speech(text, callback)
                    if success:
                        finish_callback_called = True
                        return
                    
                # Add the text to the speech queue
                logging.debug("Adding text to speech queue")
                self.engine.say(text)
                
                # Process the speech queue with a timeout
                logging.debug("Starting runAndWait()")
                
                # Set up a watchdog timer to detect if runAndWait hangs
                def watchdog():
                    time.sleep(3)  # Wait 3 seconds for speech to start
                    nonlocal speech_started
                    if not speech_started and self.is_speaking:
                        logging.error("Speech didn't start after 3 seconds, likely engine failure")
                        # Try to kill the engine by making it None
                        # This is drastic but better than a hang
                        self.engine = None
                        self.use_direct_speech = True
                        self._direct_speech(text, callback)
                
                # Start watchdog
                watchdog_thread = threading.Thread(target=watchdog)
                watchdog_thread.daemon = True
                watchdog_thread.start()
                
                # Run speech engine
                self.engine.runAndWait()
                logging.debug("Finished runAndWait()")
                
                # Ensure callback is triggered even if for some reason the finished event doesn't fire
                if not finish_callback_called and callback:
                    finish_callback_called = True
                    self.is_speaking = False
                    logging.debug("Manually calling callback since event didn't fire")
                    callback()
                    
            except Exception as e:
                logging.error(f"Error in TTS: {e}")
                logging.debug("Attempting recovery after speech error")
                
                # Try direct speech as fallback
                if not self.use_direct_speech:
                    logging.debug("Switching to direct speech after pyttsx3 failure")
                    self.use_direct_speech = True
                    speech_success = self._direct_speech(text, callback)
                    
                    if speech_success:
                        # Prevent callback from being called twice
                        finish_callback_called = True
                        return
                
                # Attempt recovery for next time
                self._initialize_engine()
            finally:
                # Ensure speaking state is properly reset unless paused
                if not self.paused:
                    self.is_speaking = False
                    logging.debug("Reset speaking state in finally block")
                    
                # Ensure callback happens even if there was an error
                if not finish_callback_called and callback:
                    finish_callback_called = True
                    logging.debug("Calling callback from finally block")
                    callback()
        
        # Create and start the speaking thread
        self.speaking_thread = threading.Thread(target=speak_thread)
        self.speaking_thread.daemon = True
        self.speaking_thread.start()
        logging.debug("Speaking thread launched")
        
    def pause(self):
        """Pause speaking (if supported)"""
        # pyttsx3 doesn't support direct pausing, so we'll implement
        # a workaround by stopping and saving the position
        if self.is_speaking and not self.paused:
            try:
                # The position might already be tracked by the on_word callback
                self.engine.stop()
                self.paused = True
                logging.debug("Speech paused")
            except Exception as e:
                logging.error(f"Error pausing TTS: {e}")
        
    def resume(self):
        """Resume speaking (if supported)"""
        if self.paused and self._current_text:
            # Resume from approximately where we left off
            remaining_text = self._current_text[self._current_position:]
            self.paused = False
            self.speak(remaining_text, self._current_callback)
            logging.debug("Speech resumed")
        
    def stop(self):
        """Stop speaking"""
        logging.debug("Stop method called")
        
        if not self.is_speaking:
            logging.debug("Not speaking, nothing to stop")
            return
            
        try:
            # Stop direct speech process if it exists
            if self.direct_speech_process:
                logging.debug("Stopping direct speech process")
                self._kill_speech_process()
                
            # Stop pyttsx3 engine if we're not in direct speech mode
            if not self.use_direct_speech:
                logging.debug("Stopping pyttsx3 engine")
                try:
                    self.engine.stop()
                except Exception as e:
                    logging.error(f"Error stopping pyttsx3 engine: {e}")
                    # Try to recover by reinitializing
                    self._initialize_engine()
                    
            logging.debug("Speech stopped")
        except Exception as e:
            logging.error(f"Error stopping speech: {e}")
        finally:
            # Always reset state even if there was an error
            self.is_speaking = False
            self.paused = False
            self._current_position = 0
        
    def is_busy(self):
        """Check if the engine is currently speaking"""
        return self.is_speaking 

    def restart_engine(self):
        """Restart the engine while preserving settings
        This can help with volume control issues on some systems"""
        # Save current settings
        try:
            self._saved_settings = {
                'rate': self.engine.getProperty('rate'),
                'volume': self.engine.getProperty('volume'),
                'voice': self.engine.getProperty('voice')
            }
            
            logging.debug(f"Saving engine settings before restart: {self._saved_settings}")
            
            # Stop any ongoing speech
            if self.is_speaking:
                self.stop()
                
            # Reinitialize the engine
            self._initialize_engine()
            
            # Restore settings
            for key, value in self._saved_settings.items():
                if value is not None:
                    self.engine.setProperty(key, value)
                    
            logging.debug("Engine restarted with saved settings")
            return True
        except Exception as e:
            logging.error(f"Error restarting engine: {e}")
            return False
            
    def debug_engine_info(self):
        """Return debug information about the engine"""
        info = {
            'is_speaking': self.is_speaking,
            'paused': self.paused
        }
        
        try:
            info['volume'] = self.engine.getProperty('volume')
            info['rate'] = self.engine.getProperty('rate')
            info['voice'] = self.engine.getProperty('voice')
            
            # Get driver info if available
            if hasattr(self.engine, 'proxy'):
                info['has_proxy'] = True
                driver = getattr(self.engine.proxy, '_driver', None)
                if driver:
                    info['has_driver'] = True
                    info['driver_type'] = str(type(driver))
                else:
                    info['has_driver'] = False
            else:
                info['has_proxy'] = False
                
        except Exception as e:
            info['error'] = str(e)
            
        return info 

    def cleanup(self):
        """Clean up resources"""
        logging.debug("Cleaning up TTS engine")
        try:
            # Stop any ongoing speech
            self.stop()
            
            # Kill any direct speech process
            if hasattr(self, 'direct_speech_process') and self.direct_speech_process:
                self._kill_speech_process()
                
            # Clean up pyttsx3 engine
            if hasattr(self, 'engine') and self.engine:
                # Give a moment for the engine to fully stop
                time.sleep(0.1)
                
                # Help with garbage collection
                self.engine = None
                
            logging.debug("TTS engine cleanup complete")
        except Exception as e:
            logging.error(f"Error during TTS cleanup: {e}")
            # Force engine to None even if cleanup fails
            self.engine = None
            self.direct_speech_process = None

    def _direct_speech(self, text, callback=None):
        """Use direct system speech synthesis as fallback"""
        try:
            logging.debug("Using direct speech synthesis")
            
            # Kill any existing speech process
            self._kill_speech_process()
            
            # Choose synthesis method based on what's available
            if self._check_command_exists("espeak"):
                # Build the command with appropriate options
                rate = int(self._saved_settings.get('rate', 150))
                # Convert rate: pyttsx3 uses WPM (150-200), espeak uses words per minute but different scale
                espeak_rate = int(rate * 0.8)  # Approximate conversion
                
                # Get volume setting - default to 15% if not set
                volume = float(self._saved_settings.get('volume', 0.15))
                logging.debug(f"Direct speech using volume={volume}, rate={rate}")
                
                # Convert volume: pyttsx3 uses 0-1, espeak uses 0-200
                # Adjust the conversion to respect the user's volume setting
                # We'll scale it between 30-100 to ensure audibility but not too loud
                espeak_volume = int(30 + (volume * 70))
                
                cmd = ["espeak", "-a", str(espeak_volume), "-s", str(espeak_rate), text]
                logging.debug(f"Running espeak command: {cmd}")
                self.direct_speech_process = subprocess.Popen(cmd)
                
                # Monitor process completion to trigger callback
                def monitor_process():
                    try:
                        self.direct_speech_process.wait()
                        logging.debug("Direct speech process completed")
                        if callback:
                            callback()
                    except Exception as e:
                        logging.error(f"Error monitoring speech process: {e}")
                        if callback:
                            callback()
                
                # Start monitoring thread
                monitor_thread = threading.Thread(target=monitor_process)
                monitor_thread.daemon = True
                monitor_thread.start()
                return True
                
            elif self._check_command_exists("say"):  # macOS
                cmd = ["say", text]
                self.direct_speech_process = subprocess.Popen(cmd)
                
                # Similar monitoring as above
                def monitor_process():
                    self.direct_speech_process.wait()
                    if callback:
                        callback()
                
                threading.Thread(target=monitor_process, daemon=True).start()
                return True
                
            elif self._check_command_exists("powershell"):  # Windows
                # Need to carefully escape quotes for PowerShell
                safe_text = text.replace('"', '\\"')
                ps_script = f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak("{safe_text}")'
                cmd = ["powershell", "-Command", ps_script]
                self.direct_speech_process = subprocess.Popen(cmd)
                
                # Similar monitoring
                def monitor_process():
                    self.direct_speech_process.wait()
                    if callback:
                        callback()
                
                threading.Thread(target=monitor_process, daemon=True).start()
                return True
            
            logging.error("No suitable speech synthesis command found")
            return False
            
        except Exception as e:
            logging.error(f"Error in direct speech: {e}")
            if callback:
                callback()
            return False
            
    def _check_command_exists(self, cmd):
        """Check if a command exists in the system path"""
        try:
            subprocess.check_call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            try:
                # Alternative for Windows
                subprocess.check_call(["where", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except subprocess.CalledProcessError:
                return False
                
    def _kill_speech_process(self):
        """Kill the direct speech process if it exists"""
        if self.direct_speech_process:
            try:
                self.direct_speech_process.terminate()
                time.sleep(0.1)
                if self.direct_speech_process.poll() is None:
                    self.direct_speech_process.kill()
                logging.debug("Killed existing speech process")
            except Exception as e:
                logging.error(f"Error killing speech process: {e}")
            self.direct_speech_process = None

    def _check_direct_speech_available(self):
        """Check if direct speech synthesis is available on this system"""
        return (self._check_command_exists("espeak") or 
                self._check_command_exists("say") or 
                self._check_command_exists("powershell")) 