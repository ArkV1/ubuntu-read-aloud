import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Gio

import logging
import threading
import os
import json

from ..tts.tts_engine import TTSEngine
from ..utils.text_selection import TextSelector
from ..utils.direct_reader import DirectReader
from .settings_dialog import SettingsDialog

class ReadAloudWindow(Gtk.ApplicationWindow):
    """Main application window for Read Aloud"""
    
    def __init__(self, application):
        Gtk.ApplicationWindow.__init__(self, application=application)
        
        self.set_title("Read Aloud")
        self.set_default_size(400, 300)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Load settings
        self.config_dir = os.path.join(os.path.expanduser("~"), ".config", "read-aloud")
        os.makedirs(self.config_dir, exist_ok=True)
        self.config_path = os.path.join(self.config_dir, "settings.json")
        self.settings = self._load_settings()
        
        # Initialize TTS engine and text selector
        self.tts_engine = TTSEngine()
        self.text_selector = TextSelector()
        
        # Set default voice to English (America) if no voice is selected
        if not self.settings.get("voice_id"):
            # Get all available voices
            voices = self.tts_engine.get_available_voices()
            logging.debug(f"Available voices: {[f'{voice_id}: {voice_name}' for voice_id, voice_name in voices]}")
            
            # Look for English (America) voice
            for voice_id, voice_name in voices:
                voice_id_lower = voice_id.lower() if voice_id else ""
                voice_name_lower = voice_name.lower() if voice_name else ""
                
                # Check if the voice is an American English voice
                if (('en-us' in voice_id_lower or 'english' in voice_name_lower) and 
                    ('america' in voice_id_lower or 'america' in voice_name_lower or 'us' in voice_id_lower)):
                    self.settings["voice_id"] = voice_id
                    logging.debug(f"Set default voice to English (America): {voice_name}")
                    self._save_settings()  # Save this default to the settings file
                    break
            
            # If no English (America) voice found, try to find any English voice
            if not self.settings.get("voice_id"):
                for voice_id, voice_name in voices:
                    voice_id_lower = voice_id.lower() if voice_id else ""
                    voice_name_lower = voice_name.lower() if voice_name else ""
                    
                    if 'en' in voice_id_lower or 'english' in voice_name_lower:
                        self.settings["voice_id"] = voice_id
                        logging.debug(f"Set default voice to English: {voice_name}")
                        self._save_settings()  # Save this default to the settings file
                        break
        
        self.direct_reader = DirectReader(self.settings)
        
        # Apply settings to TTS engine
        if self.settings.get("engine_id"):
            self.tts_engine.set_engine(self.settings["engine_id"])
        if self.settings.get("voice_id"):
            self.tts_engine.set_voice(self.settings["voice_id"])
        if self.settings.get("rate"):
            self.tts_engine.set_rate(self.settings["rate"])
        if self.settings.get("volume"):
            # Convert percentage (0-100) to float (0.0-1.0)
            volume = self.settings.get("volume", 100) / 100.0
            self.tts_engine.set_volume(volume)
        
        # Setup headerbar
        self._setup_headerbar()
        
        # Build UI
        self._build_ui()
        
        # Initialize global hotkey listener
        from ..utils.global_hotkeys import GlobalHotkeys
        self.global_hotkeys = GlobalHotkeys()
        
        # Set up global keyboard shortcuts
        self._setup_global_hotkeys()
        
        # Show all UI elements
        self.show_all()
        logging.debug("Window UI initialized and shown")
        
        # Connect to window destroy signal to clean up resources
        self.connect("destroy", self.on_window_destroy)
    
    def on_window_destroy(self, window):
        """Clean up resources when window is destroyed"""
        # Stop the global hotkey listener
        if hasattr(self, 'global_hotkeys'):
            self.global_hotkeys.stop()
            
        # Clean up TTS engine
        if hasattr(self, 'tts_engine'):
            self.tts_engine.cleanup()
        
    def _load_settings(self):
        """Load settings from file"""
        default_settings = {
            "voice_id": None,
            "rate": 150,
            "volume": 100,
            "shortcut_read_selection": "<Primary><Alt>r",
            "shortcut_capture_selection": "<Primary><Alt>s",
            "shortcut_play_pause": "<Primary><Alt>p",
            "highlight_text": True,
            "minimize_to_tray": True,
            "read_immediately": False,
            "show_mini_controller": True
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    settings = json.load(f)
                    # Update defaults with loaded settings
                    default_settings.update(settings)
        except Exception as e:
            logging.error(f"Error loading settings: {e}")
            
        return default_settings
        
    def _save_settings(self):
        """Save settings to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logging.debug(f"Settings saved to {self.config_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving settings: {e}")
            return False
        
    def _setup_headerbar(self):
        """Setup the window header bar with menus"""
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.set_title("Read Aloud")
        self.set_titlebar(headerbar)
        
        # Create settings button with gear icon
        settings_button = Gtk.Button()
        settings_button.set_tooltip_text("Settings")
        icon = Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.MENU)
        settings_button.set_image(icon)
        settings_button.connect("clicked", self.on_settings_button_clicked)
        headerbar.pack_start(settings_button)
        
    def on_settings_button_clicked(self, button):
        """Open settings dialog when settings button is clicked"""
        # Create settings dialog using the SettingsDialog class
        dialog = SettingsDialog(self, self.config_path)
        
        # Connect response signal to handle settings changes
        def on_response(dialog, response_id):
            if response_id in (Gtk.ResponseType.OK, Gtk.ResponseType.APPLY):
                # Get settings from dialog
                new_settings = dialog.get_settings()
                
                # Update our settings
                self.settings.update(new_settings)
                
                # Apply TTS settings
                if self.settings.get("engine_id"):
                    self.tts_engine.set_engine(self.settings["engine_id"])
                if self.settings.get("voice_id"):
                    self.tts_engine.set_voice(self.settings["voice_id"], self.settings.get("engine_id"))
                if self.settings.get("rate"):
                    self.tts_engine.set_rate(self.settings["rate"])
                    
                # Save settings
                self._save_settings()
                
                # Update direct reader settings
                self.direct_reader.update_settings(self.settings)
                
                # Update accelerators for shortcuts
                self._setup_global_hotkeys()
        
        # Connect the signal
        dialog.connect("response", on_response)
        
        # Show the dialog
        dialog.run()
        
    def _build_ui(self):
        """Build the main user interface"""
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        main_box.set_margin_start(10)
        main_box.set_margin_end(10)
        
        self.add(main_box)
        
        # Text view for displaying and editing selected text
        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_buffer = self.text_view.get_buffer()
        
        # Set a default welcome message
        self.text_buffer.set_text("Welcome to Read Aloud!\n\nSelect text in any application and press Ctrl+Alt+S to capture it.\nThen press the play button to have it read aloud.\n\nYou can also use Ctrl+Alt+R to read selected text directly.")
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(self.text_view)
        main_box.pack_start(scrolled_window, True, True, 0)
        
        # Controls
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        main_box.pack_start(controls_box, False, False, 0)
        
        # Read button
        self.read_button = Gtk.Button.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
        self.read_button.set_tooltip_text("Read text")
        self.read_button.connect("clicked", self.on_read_clicked)
        controls_box.pack_start(self.read_button, False, False, 0)
        
        # Stop button
        stop_button = Gtk.Button.new_from_icon_name("media-playback-stop", Gtk.IconSize.BUTTON)
        stop_button.set_tooltip_text("Stop reading")
        stop_button.connect("clicked", self.on_stop_clicked)
        controls_box.pack_start(stop_button, False, False, 0)
        
        # Get text button
        get_text_button = Gtk.Button.new_from_icon_name("edit-paste", Gtk.IconSize.BUTTON)
        get_text_button.set_tooltip_text("Get selected text")
        get_text_button.connect("clicked", self.on_get_text_clicked)
        controls_box.pack_start(get_text_button, False, False, 0)
        
        # Status bar
        self.statusbar = Gtk.Statusbar()
        self.statusbar.push(0, "Ready")
        main_box.pack_start(self.statusbar, False, False, 0)
        
    def _setup_global_hotkeys(self):
        """Set up global keyboard shortcuts"""
        # Map of hotkey -> callback function
        hotkeys = {
            self.settings.get("shortcut_capture_selection", "<Primary><Alt>s"): 
                self.on_get_text_action,
                
            self.settings.get("shortcut_play_pause", "<Primary><Alt>p"): 
                self.on_play_pause_action,
                
            self.settings.get("shortcut_read_selection", "<Primary><Alt>r"): 
                self.on_read_selection_action
        }
        
        # Register all hotkeys
        self.global_hotkeys.update_hotkeys(hotkeys)
        
        # Start the global hotkey listener
        self.global_hotkeys.start()
        logging.debug("Global hotkeys registered and activated")
        
    def on_get_text_action(self):
        """Handle get-text keyboard shortcut"""
        self.on_get_text_clicked(None)
        
    def on_play_pause_action(self):
        """Handle play-pause keyboard shortcut"""
        if self.tts_engine.is_busy():
            self.on_stop_clicked(None)
        else:
            self.on_read_clicked(None)
            
    def on_read_selection_action(self):
        """Handle read-selection keyboard shortcut"""
        self.direct_reader.read_selection()
        
    def on_get_text_clicked(self, button):
        """Get selected text from screen"""
        def get_text_thread():
            selected_text = self.text_selector.get_selected_text()
            if not selected_text:
                # Try alternative method
                selected_text = self.text_selector.get_primary_selection()
                
            GLib.idle_add(self.update_text_view, selected_text)
            
        threading.Thread(target=get_text_thread, daemon=True).start()
        
    def update_text_view(self, text):
        """Update text view with selected text"""
        if text:
            self.text_buffer.set_text(text)
            self.statusbar.push(0, f"Got {len(text)} characters")
        else:
            self.statusbar.push(0, "No text selected")
            
    def on_read_clicked(self, button):
        """Read the text in the text view"""
        start_iter, end_iter = self.text_buffer.get_bounds()
        text = self.text_buffer.get_text(start_iter, end_iter, False)
        
        if text:
            self.read_button.set_sensitive(False)
            self.statusbar.push(0, "Reading...")
            self.tts_engine.speak(text, callback=self.on_reading_finished)
        else:
            self.statusbar.push(0, "No text to read")
            
    def on_reading_finished(self):
        """Called when reading is finished"""
        GLib.idle_add(self.update_ui_after_reading)
        
    def update_ui_after_reading(self):
        """Update UI after reading is finished"""
        self.read_button.set_sensitive(True)
        self.statusbar.push(0, "Finished reading")
        
    def on_stop_clicked(self, button):
        """Stop reading"""
        self.tts_engine.stop()
        self.read_button.set_sensitive(True)
        self.statusbar.push(0, "Stopped reading")
        
    def on_rate_changed(self, scale):
        """Change TTS rate"""
        rate = int(scale.get_value())
        
        # Apply rate change immediately to the engine
        # This will affect any ongoing speech without restarting
        self.tts_engine.set_rate(rate)
        logging.debug(f"Rate changed to {rate}")
        
        # Update the setting in memory
        self.settings["rate"] = rate
        
        # Use a delayed save to avoid excessive file writes
        # Cancel any existing delayed save
        if hasattr(self, '_rate_save_timeout') and self._rate_save_timeout:
            GLib.source_remove(self._rate_save_timeout)
            
        # Schedule a new save after 500ms of no rate changes
        self._rate_save_timeout = GLib.timeout_add(500, self._delayed_save_rate_setting)
    
    def _delayed_save_rate_setting(self):
        """Save rate setting after a delay to reduce disk writes"""
        self._save_settings()
        self._rate_save_timeout = None
        return False  # Don't repeat the timeout
        
    def on_volume_changed(self, scale):
        """Change TTS volume"""
        volume_percent = scale.get_value()
        # Convert from percentage (0-100) to float (0.0-1.0)
        volume = volume_percent / 100.0
        
        # Apply volume change immediately to the engine
        # This will affect any ongoing speech without restarting
        self.tts_engine.set_volume(volume)
        logging.debug(f"Volume changed to {volume_percent}%")
        
        # Update the setting in memory
        self.settings["volume"] = volume_percent
        
        # Use a delayed save to avoid excessive file writes
        # Cancel any existing delayed save
        if hasattr(self, '_volume_save_timeout') and self._volume_save_timeout:
            GLib.source_remove(self._volume_save_timeout)
            
        # Schedule a new save after 500ms of no volume changes
        self._volume_save_timeout = GLib.timeout_add(500, self._delayed_save_volume_setting)
    
    def _delayed_save_volume_setting(self):
        """Save volume setting after a delay to reduce disk writes"""
        self._save_settings()
        self._volume_save_timeout = None
        return False  # Don't repeat the timeout
        
    def _update_accelerators(self):
        """Update keyboard accelerators based on settings"""
        # Update global hotkeys
        self._setup_global_hotkeys()
        
    def on_quit_clicked(self, menu_item):
        """Quit the application"""
        self.get_application().quit()

    def _play_sample_text(self, text):
        """Play sample text with current voice, rate and volume settings"""
        # Make sure we're using the latest settings
        engine_id = self.settings.get("engine_id")
        voice_id = self.settings.get("voice_id")
        
        if engine_id:
            self.tts_engine.set_engine(engine_id)
            
        if voice_id:
            self.tts_engine.set_voice(voice_id, engine_id)
            
        rate = self.settings.get("rate", 150)
        self.tts_engine.set_rate(rate)
        
        volume = self.settings.get("volume", 100) / 100.0
        self.tts_engine.set_volume(volume)
        
        # Log that we're about to play sample
        logging.debug(f"Playing sample with engine={engine_id}, voice={voice_id}, rate={rate}, volume={volume}")
        
        # Speak the text
        self.tts_engine.speak(text)
        
    def on_restart_engine_clicked(self, button):
        """Restart the TTS engine"""
        if self.tts_engine.restart_engine():
            # Show success message
            dialog = Gtk.MessageDialog(
                transient_for=button.get_toplevel(),
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="TTS Engine Restarted"
            )
            dialog.format_secondary_text("The TTS engine has been restarted. This may help with volume control issues.")
            dialog.run()
            dialog.destroy()
        else:
            # Show error message
            dialog = Gtk.MessageDialog(
                transient_for=button.get_toplevel(),
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Failed to Restart Engine"
            )
            dialog.format_secondary_text("There was an error restarting the TTS engine.")
            dialog.run()
            dialog.destroy()
            
    def on_debug_engine_clicked(self, button):
        """Show debug information about the TTS engine"""
        info = self.tts_engine.debug_engine_info()
        
        # Create a formatted text representation
        text = "TTS Engine Debug Information\n\n"
        for key, value in info.items():
            text += f"{key}: {value}\n"
            
        # Show in a dialog
        dialog = Gtk.MessageDialog(
            transient_for=button.get_toplevel(),
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="TTS Engine Information"
        )
        dialog.format_secondary_text(text)
        dialog.run()
        dialog.destroy() 