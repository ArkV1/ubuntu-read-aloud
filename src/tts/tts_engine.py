import pyttsx3
import threading
import logging
import time
import subprocess
import shlex
import os
import tempfile
import wave

class TTSEngine:
    """Text-to-Speech engine interface with multiple backends:
    1. Piper TTS - high quality neural TTS (preferred)
    2. Direct Speech - system commands like espeak (fallback)
    3. pyttsx3 - basic TTS (last resort)
    """
    
    # Engine types
    ENGINE_PIPER = "piper"
    ENGINE_DIRECT = "direct"
    ENGINE_PYTTSX3 = "pyttsx3"
    
    def __init__(self):
        self._initialize_engine()
        self.speaking_thread = None
        self.is_speaking = False
        self.paused = False
        self._current_text = None
        self._current_position = 0
        self._current_callback = None
        self._saved_settings = {}
        
        # Track the active engine and voice
        self.active_engine = None
        self.active_voice = None
        
        # Check if piper is available first as it provides better quality
        self.use_piper = self._check_piper_available()
        if self.use_piper:
            logging.debug("Piper TTS is available, using as primary TTS method")
            # Cache available voices
            self.piper_voices = self._get_piper_voices()
            # Select default voice
            if self.piper_voices:
                self.active_engine = self.ENGINE_PIPER
                self.active_voice = self.piper_voices[0].get('name')
                logging.debug(f"Set default voice to Piper: {self.active_voice}")
            logging.debug(f"Found {len(self.piper_voices)} Piper voices")
        else:
            logging.debug("Piper TTS not available")
            self.piper_voices = []
            
        # Check if direct speech is available as fallback
        self.use_direct_speech = self._check_direct_speech_available()
        if self.use_direct_speech:
            logging.debug("Direct speech is available, using as secondary TTS method")
            # Set as active engine if Piper isn't available
            if not self.active_engine:
                self.active_engine = self.ENGINE_DIRECT
                logging.debug("Set default engine to direct speech")
        else:
            logging.debug("Direct speech is not available")
            
        self.direct_speech_process = None
        
        # Set pyttsx3 as last resort if others aren't available
        if not self.active_engine and hasattr(self, 'engine') and self.engine:
            self.active_engine = self.ENGINE_PYTTSX3
            # Try to get a default voice
            try:
                voices = self.engine.getProperty('voices')
                if voices:
                    self.active_voice = voices[0].id
                    logging.debug(f"Set default voice to pyttsx3: {self.active_voice}")
            except Exception as e:
                logging.error(f"Error getting default pyttsx3 voice: {e}")
            
        logging.debug(f"Initialized with active engine: {self.active_engine}, voice: {self.active_voice}")
        
    def _initialize_engine(self):
        """Initialize or reinitialize the pyttsx3 engine (last resort)"""
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
            logging.debug("pyttsx3 engine initialized")
            return True
        except Exception as e:
            logging.error(f"Error initializing pyttsx3 engine: {e}")
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
                # Convert from our rate scale (50-300) to pyttsx3's expected range
                # pyttsx3 default is 200 words per minute, with higher = faster
                # We'll map:
                # 50 (our slowest) -> 50 (pyttsx3 very slow)
                # 150 (our normal) -> 170 (pyttsx3 normal-ish)
                # 300 (our fastest) -> 350 (pyttsx3 very fast)
                pyttsx3_rate = int(rate * 1.2)
                self.engine.setProperty('rate', pyttsx3_rate)
                logging.debug(f"TTS engine rate set to {rate} (pyttsx3: {pyttsx3_rate})")
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
    
    def set_engine(self, engine_type):
        """Set the active TTS engine"""
        if engine_type not in [self.ENGINE_PIPER, self.ENGINE_DIRECT, self.ENGINE_PYTTSX3]:
            logging.error(f"Unknown engine type: {engine_type}")
            return False
            
        # Check if requested engine is available
        if engine_type == self.ENGINE_PIPER and not self.use_piper:
            logging.error("Piper TTS not available")
            return False
        elif engine_type == self.ENGINE_DIRECT and not self.use_direct_speech:
            logging.error("Direct speech not available")
            return False
        elif engine_type == self.ENGINE_PYTTSX3 and not (hasattr(self, 'engine') and self.engine):
            logging.error("pyttsx3 not available")
            return False
            
        # Set the active engine
        self.active_engine = engine_type
        logging.debug(f"Set active engine to {engine_type}")
        
        # Reset the active voice based on the new engine
        if engine_type == self.ENGINE_PIPER and self.piper_voices:
            self.active_voice = self.piper_voices[0].get('name')
        elif engine_type == self.ENGINE_PYTTSX3:
            try:
                voices = self.engine.getProperty('voices')
                if voices:
                    self.active_voice = voices[0].id
            except Exception:
                self.active_voice = None
        else:
            # Direct speech doesn't have selectable voices
            self.active_voice = None
            
        logging.debug(f"Set default voice for {engine_type} to {self.active_voice}")
        return True
    
    def set_voice(self, voice_id=None, engine_type=None):
        """Set the voice to use, optionally specifying the engine"""
        if not voice_id:
            return False
            
        # If engine is specified, use that engine
        if engine_type:
            success = self.set_engine(engine_type)
            if not success:
                return False
        
        # Handle voice selection based on active engine
        if self.active_engine == self.ENGINE_PIPER:
            # For Piper, voice_id should be a voice name like 'en_US-lessac-medium'
            for voice in self.piper_voices:
                if voice.get('name') == voice_id:
                    self.active_voice = voice_id
                    logging.debug(f"Set Piper voice to {voice_id}")
                    return True
            logging.error(f"Piper voice not found: {voice_id}")
            return False
        
        # For pyttsx3
        elif self.active_engine == self.ENGINE_PYTTSX3:
            try:
                self.engine.setProperty('voice', voice_id)
                self.active_voice = voice_id
                logging.debug(f"Set pyttsx3 voice to {voice_id}")
                return True
            except Exception as e:
                logging.error(f"Error setting pyttsx3 voice: {e}")
                return False
                
        # Direct speech doesn't support voice selection
        elif self.active_engine == self.ENGINE_DIRECT:
            logging.warning("Direct speech doesn't support voice selection")
            return False
            
        return False
    
    def get_available_engines(self):
        """Get list of available engines"""
        engines = []
        
        if self.use_piper:
            engines.append((self.ENGINE_PIPER, "Piper TTS (High Quality)"))
            
        if self.use_direct_speech:
            engines.append((self.ENGINE_DIRECT, "Direct Speech (System)"))
            
        if hasattr(self, 'engine') and self.engine:
            engines.append((self.ENGINE_PYTTSX3, "pyttsx3 (Basic)"))
            
        return engines
    
    def get_voices_for_engine(self, engine_type):
        """Get list of available voices for a specific engine"""
        if engine_type == self.ENGINE_PIPER:
            return [(voice.get('name'), voice.get('name')) for voice in self.piper_voices]
        elif engine_type == self.ENGINE_PYTTSX3:
            try:
                if hasattr(self, 'engine') and self.engine:
                    pyttsx3_voices = self.engine.getProperty('voices')
                    return [(voice.id, voice.name) for voice in pyttsx3_voices]
            except Exception as e:
                logging.error(f"Error getting pyttsx3 voices: {e}")
        
        # Direct speech doesn't have selectable voices
        return []
    
    def get_available_voices(self):
        """Get list of available voices for all engines (for backward compatibility)"""
        voices = []
        
        # Add Piper voices if available
        if self.use_piper:
            for voice in self.piper_voices:
                voices.append((voice.get('name'), f"Piper: {voice.get('name')}"))
                
        # Add pyttsx3 voices
        try:
            if hasattr(self, 'engine') and self.engine:
                pyttsx3_voices = self.engine.getProperty('voices')
                for voice in pyttsx3_voices:
                    voices.append((voice.id, f"pyttsx3: {voice.name}"))
        except Exception as e:
            logging.error(f"Error getting pyttsx3 voices: {e}")
            
        return voices
        
    def speak(self, text, callback=None):
        """Speak the given text in a separate thread"""
        logging.debug(f"Speak method called with {len(text)} characters of text")
        
        # Always stop any ongoing speech first
        if self.is_speaking:
            logging.debug("Engine was speaking, stopping first")
            self.stop()
            # Give a moment for the engine to fully stop
            time.sleep(0.1)
        
        # If the engine seems stuck, reset state
        if self.is_speaking:
            logging.warning("Engine still marked as speaking after stop, resetting state")
            self.is_speaking = False
        
        # Track our state regardless of which method we use
        self.is_speaking = True
        self.paused = False
        self._current_text = text
        self._current_position = 0
        self._current_callback = callback
        
        # Update saved settings for possible direct speech use
        try:
            if hasattr(self, 'engine') and self.engine:
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
        
        # Use the active engine
        if self.active_engine == self.ENGINE_PIPER:
            logging.debug("Using Piper TTS for speech synthesis")
            success = self._piper_speech(text, callback)
            if success:
                return
            
            # If Piper failed, try other methods
            logging.debug("Piper speech failed, falling back to alternative methods")
            
        # Try direct speech as second option
        if self.active_engine == self.ENGINE_DIRECT or (self.active_engine == self.ENGINE_PIPER and self.use_direct_speech):
            logging.debug("Using direct speech mode")
            success = self._direct_speech(text, callback)
            if success:
                return
            
            # If direct speech failed, try to recover with pyttsx3
            logging.debug("Direct speech failed, trying to recover with pyttsx3")
            
        # Last resort: pyttsx3
        if not self._initialize_engine():
            logging.error("All TTS methods failed")
            self.is_speaking = False
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
                        # Engine reinitialization failed, try direct speech again
                        logging.debug("Engine reinitialization failed, trying direct speech again")
                        success = self._direct_speech(text, callback)
                        if success:
                            return
                        else:
                            # All methods failed, call callback and exit
                            logging.error("All speech methods failed")
                            if callback and not finish_callback_called:
                                finish_callback_called = True
                                callback()
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
                
                # Add the text to the speech queue
                logging.debug("Adding text to speech queue")
                self.engine.say(text)
                
                # Start the speech
                logging.debug("Running speech engine")
                self.engine.runAndWait()
                logging.debug("Engine finished running")
                
                # Check if callback was called
                if not finish_callback_called and callback:
                    finish_callback_called = True
                    self.is_speaking = False
                    logging.debug("Calling callback manually because finished-utterance didn't trigger")
                    callback()
                    
            except Exception as e:
                logging.error(f"Error in speech thread: {e}")
                if callback and not finish_callback_called:
                    finish_callback_called = True
                    callback()
                self.is_speaking = False
        
        # Start the speech thread
        self.speaking_thread = threading.Thread(target=speak_thread)
        self.speaking_thread.daemon = True
        self.speaking_thread.start()
        
    def stop(self):
        """Stop speaking"""
        logging.debug("Stop method called")
        
        if not self.is_speaking:
            logging.debug("Not speaking, nothing to stop")
            return
            
        try:
            # Stop direct speech or Piper process if it exists
            if self.direct_speech_process:
                logging.debug("Stopping speech process")
                self._kill_speech_process()
                
            # Stop pyttsx3 engine if it exists
            if hasattr(self, 'engine') and self.engine:
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
            if hasattr(self, 'engine') and self.engine:
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
            return False
        except Exception as e:
            logging.error(f"Error restarting engine: {e}")
            return False
            
    def debug_engine_info(self):
        """Return debug information about the engine"""
        info = {
            'is_speaking': self.is_speaking,
            'paused': self.paused,
            'use_piper': self.use_piper,
            'use_direct_speech': self.use_direct_speech,
            'active_engine': self.active_engine,
            'active_voice': self.active_voice
        }
        
        if self.use_piper:
            info['piper_voices_count'] = len(self.piper_voices)
        
        try:
            if hasattr(self, 'engine') and self.engine:
                info['volume'] = self.engine.getProperty('volume')
                info['rate'] = self.engine.getProperty('rate')
                
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
            
    def _piper_speech(self, text, callback=None):
        """Use Piper TTS for high-quality speech synthesis"""
        if not self.use_piper or not self.active_voice:
            return False
            
        try:
            # Get current settings
            volume = 1.0
            if self._saved_settings and 'volume' in self._saved_settings:
                volume = self._saved_settings['volume']
            
            rate = 1.0
            if self._saved_settings and 'rate' in self._saved_settings:
                # Convert pyttsx3 rate (50-300) to piper scale (0.5-1.5)
                # IMPORTANT: For Piper, smaller values = faster speech, opposite of pyttsx3
                # So we need to invert the calculation
                pyttsx_rate = self._saved_settings['rate']
                # Map from pyttsx3 range (50-300) to Piper's range (1.5-0.5)
                # 50 -> 1.5 (slowest)
                # 300 -> 0.5 (fastest)
                rate = 1.5 - ((pyttsx_rate - 50) / 250.0)
                # Clamp to reasonable range
                rate = max(0.5, min(1.5, rate))
                logging.debug(f"Converted pyttsx3 rate {pyttsx_rate} to Piper length-scale {rate}")
            
            # Option 1: Stream directly to audio device if possible
            try:
                import sounddevice as sd
                import numpy as np
                
                # Try to import Piper voice
                try:
                    from piper.voice import PiperVoice
                except ImportError:
                    logging.error("Failed to import PiperVoice, trying command line approach")
                    raise ImportError("PiperVoice not available")
                
                # Determine model path - try to use voice name directly
                model_path = self.active_voice
                # If it doesn't look like a path, assume it's just a voice name
                if not os.path.exists(model_path) and not model_path.endswith(".onnx"):
                    # Look in standard locations
                    locations = [
                        os.path.expanduser("~/.local/share/piper-tts/piper-voices"),
                        "/usr/local/share/piper-voices",
                        "/usr/share/piper-voices"
                    ]
                    
                    for location in locations:
                        test_path = os.path.join(location, f"{model_path}.onnx")
                        if os.path.exists(test_path):
                            model_path = test_path
                            break
                            
                    if not os.path.exists(model_path):
                        # If model not found, try downloading
                        logging.debug(f"Model not found locally, will let Piper try to download {model_path}")
                
                # Load model and create voice
                voice = PiperVoice.load(model_path)
                
                # Set up audio stream
                stream = sd.OutputStream(
                    samplerate=voice.config.sample_rate,
                    channels=1,
                    dtype='int16'
                )
                stream.start()
                
                def stream_audio():
                    try:
                        for audio_bytes in voice.synthesize_stream_raw(text):
                            if not self.is_speaking:
                                break  # Allow stopping
                            int_data = np.frombuffer(audio_bytes, dtype=np.int16)
                            # Apply volume scaling
                            int_data = (int_data * volume).astype(np.int16)
                            stream.write(int_data)
                        
                        stream.stop()
                        stream.close()
                        
                        self.is_speaking = False
                        if callback:
                            callback()
                    except Exception as e:
                        logging.error(f"Error in Piper audio streaming: {e}")
                        self.is_speaking = False
                        if callback:
                            callback()
                
                # Start streaming in thread
                thread = threading.Thread(target=stream_audio)
                thread.daemon = True
                thread.start()
                
                return True
                
            except (ImportError, Exception) as e:
                logging.debug(f"Couldn't use Piper Python API: {e}")
                logging.debug("Falling back to command-line Piper")
                
                # Option 2: Use command-line piper
                cmd = ["piper"]
                
                # Add voice model parameter
                cmd.extend(["--model", self.active_voice])
                
                # Set rate if available
                if rate:
                    cmd.extend(["--length-scale", str(rate)])
                    
                # Set output to raw for streaming
                cmd.append("--output-raw")
                
                # Create process with pipe for input
                self.direct_speech_process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Write text to stdin and close
                self.direct_speech_process.stdin.write(text)
                self.direct_speech_process.stdin.close()
                
                # Feed audio to aplay for playback
                aplay_cmd = ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw"]
                aplay_process = subprocess.Popen(aplay_cmd, stdin=self.direct_speech_process.stdout)
                
                # Monitor process for completion
                def monitor_process():
                    aplay_process.wait()
                    if self.direct_speech_process:
                        self.direct_speech_process.wait()
                    self.is_speaking = False
                    if callback:
                        callback()
                
                monitor_thread = threading.Thread(target=monitor_process)
                monitor_thread.daemon = True
                monitor_thread.start()
                
                return True
                
        except Exception as e:
            logging.error(f"Error in Piper speech: {e}")
            self.is_speaking = False
            if callback:
                callback()
            return False

    def _direct_speech(self, text, callback=None):
        """Use direct system speech synthesis as fallback"""
        try:
            # Get current settings
            volume = self._saved_settings.get('volume', 0.15)  # Default if not set
            
            if self._check_command_exists("espeak"):  # Linux
                # Convert volume to espeak scale (0-100)
                # We scale from 0.3-1.0 to 30-100 to ensure audibility
                espeak_volume = int(max(30, min(100, volume * 100)))
                
                # Convert rate to espeak scale
                # For espeak, higher values = faster speech (80-450 words per minute)
                # Our slider range is 50-300, but we want a narrower espeak range 
                # for better intelligibility
                espeak_rate = 160  # Default
                if 'rate' in self._saved_settings:
                    pyttsx_rate = self._saved_settings.get('rate', 150)
                    # Map from our range (50-300) to espeak range (120-220)
                    # This provides a more natural range for espeak
                    espeak_rate = int(120 + (pyttsx_rate - 50) * 0.4)
                    
                logging.debug(f"Using espeak with volume={espeak_volume}, rate={espeak_rate} (from {pyttsx_rate})")
                
                # Build espeak command
                cmd = ["espeak", f"-a{espeak_volume}", f"-s{espeak_rate}", text]
                self.direct_speech_process = subprocess.Popen(cmd)
                
                def monitor_process():
                    self.direct_speech_process.wait()
                    self.is_speaking = False
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
                    self.is_speaking = False
                    if callback:
                        callback()
                
                threading.Thread(target=monitor_process, daemon=True).start()
                return True
                
            elif self._check_command_exists("powershell"):  # Windows
                # Need to carefully escape quotes for PowerShell
                safe_text = text.replace('"', '`"')
                ps_script = f'Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak("{safe_text}")'
                cmd = ["powershell", "-Command", ps_script]
                self.direct_speech_process = subprocess.Popen(cmd)
                
                # Similar monitoring
                def monitor_process():
                    self.direct_speech_process.wait()
                    self.is_speaking = False
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

    def _check_piper_available(self):
        """Check if Piper TTS is available"""
        # First check if the Python API is available
        try:
            from piper.voice import PiperVoice
            logging.debug("Found Piper Python API")
            return True
        except ImportError:
            # Check if the command-line tool is available
            if self._check_command_exists("piper"):
                logging.debug("Found Piper command-line tool")
                return True
            logging.debug("Piper TTS not found")
            return False
    
    def _get_piper_voices(self):
        """Get available Piper voices"""
        voices = []
        
        # Look in standard voice directories
        voice_dirs = [
            os.path.expanduser("~/.local/share/piper-tts/piper-voices"),
            "/usr/local/share/piper-voices",
            "/usr/share/piper-voices"
        ]
        
        # Check if command-line piper is installed
        if self._check_command_exists("piper"):
            try:
                # Try to get voice list using pip-installed piper
                result = subprocess.run(
                    ["piper", "--list-models"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode == 0:
                    # Parse voice list
                    for line in result.stdout.splitlines():
                        line = line.strip()
                        if line and not line.startswith("Available"):
                            voices.append({"name": line})
                    return voices
            except Exception as e:
                logging.error(f"Error getting Piper voice list: {e}")
        
        # Manually look for voice models in directories
        for voice_dir in voice_dirs:
            if os.path.exists(voice_dir):
                for root, dirs, files in os.walk(voice_dir):
                    for file in files:
                        if file.endswith(".onnx"):
                            # Extract voice name from file path
                            voice_name = os.path.splitext(file)[0]
                            voices.append({
                                "name": voice_name,
                                "path": os.path.join(root, file)
                            })
        
        # If no voices found, add a few default ones that will be downloaded automatically by Piper
        if not voices:
            for voice_name in ["en_US-lessac-medium", "en_GB-vctk-medium"]:
                voices.append({"name": voice_name})
                
        return voices 