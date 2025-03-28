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
        # Create dialog as a separate window (not modal)
        dialog = Gtk.Window(title="Settings")
        dialog.set_transient_for(self)  # Set parent but not modal
        dialog.set_default_size(350, 400)
        dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        dialog.set_destroy_with_parent(True)
        
        # Main box for content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_border_width(10)
        dialog.add(main_box)
        
        # Create notebook for tabs
        notebook = Gtk.Notebook()
        main_box.pack_start(notebook, True, True, 0)
        
        # Voice settings tab
        voice_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        voice_box.set_border_width(10)
        notebook.append_page(voice_box, Gtk.Label(label="Voice"))
        
        # Voice selection
        voice_label = Gtk.Label(label="Voice:", halign=Gtk.Align.START)
        voice_box.pack_start(voice_label, False, False, 0)
        
        # Voice combo box
        voice_combo = Gtk.ComboBoxText()
        
        # Populate voice combo
        voices = self.tts_engine.get_available_voices()
        selected_idx = 0
        current_voice_id = self.settings.get("voice_id")
        for i, (voice_id, voice_name) in enumerate(voices):
            voice_combo.append(voice_id, voice_name)
            if voice_id == current_voice_id:
                selected_idx = i
                
        # Set the active voice
        voice_combo.set_active(selected_idx)
        voice_box.pack_start(voice_combo, False, False, 0)
        
        # Separator
        separator1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        voice_box.pack_start(separator1, False, False, 5)
        
        # Rate control
        rate_label = Gtk.Label(label="Rate:", halign=Gtk.Align.START)
        voice_box.pack_start(rate_label, False, False, 0)
        
        rate_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 50, 300, 10)
        rate_scale.set_value(self.settings.get("rate", 150))
        voice_box.pack_start(rate_scale, False, False, 0)
        
        # Volume control
        volume_label = Gtk.Label(label="Volume:", halign=Gtk.Align.START)
        voice_box.pack_start(volume_label, False, False, 0)
        
        volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        volume_scale.set_value(self.settings.get("volume", 100))
        voice_box.pack_start(volume_scale, False, False, 0)
        
        # Sample text to test voice
        sample_label = Gtk.Label(label="Sample text:", halign=Gtk.Align.START)
        voice_box.pack_start(sample_label, False, False, 0)
        
        sample_entry = Gtk.Entry()
        sample_entry.set_text("This is a longer sample of the selected voice. You can adjust the volume and rate while this text is being spoken to hear the changes in real-time.")
        voice_box.pack_start(sample_entry, False, False, 0)
        
        # Help text for volume adjustment
        volume_help = Gtk.Label()
        volume_help.set_markup("<i>Adjust volume slider during playback to hear immediate changes</i>")
        volume_help.set_halign(Gtk.Align.START)
        voice_box.pack_start(volume_help, False, False, 0)
        
        # Sample buttons container
        sample_buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        voice_box.pack_start(sample_buttons_box, False, False, 0)
        
        # Play Sample button
        sample_button = Gtk.Button(label="Play Sample")
        sample_button.connect("clicked", lambda w: self._play_sample_text(sample_entry.get_text()))
        sample_buttons_box.pack_start(sample_button, False, False, 0)
        
        # Stop Sample button
        stop_sample_button = Gtk.Button(label="Stop")
        stop_sample_button.connect("clicked", lambda w: self.tts_engine.stop())
        sample_buttons_box.pack_start(stop_sample_button, False, False, 0)
        
        # Advanced options container
        advanced_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        voice_box.pack_start(advanced_box, False, False, 10)
        
        # Restart Engine button - can help with volume control on some systems
        restart_engine_button = Gtk.Button(label="Restart Engine")
        restart_engine_button.set_tooltip_text("Restart TTS engine - can help fix volume control issues")
        restart_engine_button.connect("clicked", self.on_restart_engine_clicked)
        advanced_box.pack_start(restart_engine_button, False, False, 0)
        
        # Debug Engine button
        debug_button = Gtk.Button(label="Debug Engine")
        debug_button.set_tooltip_text("Show TTS engine debug information")
        debug_button.connect("clicked", self.on_debug_engine_clicked)
        advanced_box.pack_start(debug_button, False, False, 0)
        
        # Shortcuts tab
        shortcuts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        shortcuts_box.set_border_width(10)
        notebook.append_page(shortcuts_box, Gtk.Label(label="Shortcuts"))
        
        # Read Selection shortcut
        read_shortcut_label = Gtk.Label(label="Read Selection:", halign=Gtk.Align.START)
        shortcuts_box.pack_start(read_shortcut_label, False, False, 0)
        
        read_shortcut_entry = Gtk.Entry()
        read_shortcut_entry.set_text(self.settings.get("shortcut_read_selection", "<Primary><Alt>r"))
        shortcuts_box.pack_start(read_shortcut_entry, False, False, 0)
        
        # Capture Selection shortcut
        capture_shortcut_label = Gtk.Label(label="Capture Selection:", halign=Gtk.Align.START)
        shortcuts_box.pack_start(capture_shortcut_label, False, False, 0)
        
        capture_shortcut_entry = Gtk.Entry()
        capture_shortcut_entry.set_text(self.settings.get("shortcut_capture_selection", "<Primary><Alt>s"))
        shortcuts_box.pack_start(capture_shortcut_entry, False, False, 0)
        
        # Play/Pause shortcut
        play_shortcut_label = Gtk.Label(label="Play/Pause:", halign=Gtk.Align.START)
        shortcuts_box.pack_start(play_shortcut_label, False, False, 0)
        
        play_shortcut_entry = Gtk.Entry()
        play_shortcut_entry.set_text(self.settings.get("shortcut_play_pause", "<Primary><Alt>p"))
        shortcuts_box.pack_start(play_shortcut_entry, False, False, 0)
        
        # Behavior tab
        behavior_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        behavior_box.set_border_width(10)
        notebook.append_page(behavior_box, Gtk.Label(label="Behavior"))
        
        # Highlight text while reading
        highlight_check = Gtk.CheckButton(label="Highlight text while reading")
        highlight_check.set_active(self.settings.get("highlight_text", True))
        behavior_box.pack_start(highlight_check, False, False, 0)
        
        # Minimize to tray when closed
        minimize_check = Gtk.CheckButton(label="Minimize to system tray when closed")
        minimize_check.set_active(self.settings.get("minimize_to_tray", True))
        behavior_box.pack_start(minimize_check, False, False, 0)
        
        # Read immediately after capturing
        read_immediately_check = Gtk.CheckButton(label="Read immediately after capturing text")
        read_immediately_check.set_active(self.settings.get("read_immediately", False))
        behavior_box.pack_start(read_immediately_check, False, False, 0)
        
        # Show mini controller
        mini_controller_check = Gtk.CheckButton(label="Show mini controller for direct reading")
        mini_controller_check.set_active(self.settings.get("show_mini_controller", True))
        behavior_box.pack_start(mini_controller_check, False, False, 0)
        
        # About tab (moved from hamburger menu)
        about_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        about_box.set_border_width(10)
        notebook.append_page(about_box, Gtk.Label(label="About"))
        
        # Logo
        logo = Gtk.Image.new_from_icon_name("accessories-text-editor", Gtk.IconSize.DIALOG)
        about_box.pack_start(logo, False, False, 10)
        
        # App name
        app_name = Gtk.Label()
        app_name.set_markup("<b><span size='x-large'>Read Aloud</span></b>")
        about_box.pack_start(app_name, False, False, 5)
        
        # Version
        version_label = Gtk.Label(label="Version 0.2.0")
        about_box.pack_start(version_label, False, False, 5)
        
        # Description
        desc_label = Gtk.Label(label="A Linux application that provides text-to-speech\nfunctionality similar to MacOS's Read Aloud feature.")
        desc_label.set_justify(Gtk.Justification.CENTER)
        about_box.pack_start(desc_label, False, False, 5)
        
        # Authors
        authors_label = Gtk.Label()
        authors_label.set_markup("<b>Read Aloud Team</b>")
        about_box.pack_start(authors_label, False, False, 5)
        
        # Button area
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.FILL)  # Make the box fill the width
        main_box.pack_start(button_box, False, False, 0)
        
        # Quit button (moved from hamburger menu)
        quit_button = Gtk.Button(label="Quit Application")
        quit_button.connect("clicked", self.on_quit_clicked)
        button_box.pack_start(quit_button, False, False, 0)  # Pack at start (left)
        
        # Spacer to push buttons to opposite sides
        spacer = Gtk.Label("")
        spacer.set_hexpand(True)
        button_box.pack_start(spacer, True, True, 0)
        
        # Close button
        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda w: dialog.destroy())
        button_box.pack_end(close_button, False, False, 0)
        
        # Apply button
        apply_button = Gtk.Button(label="Apply")
        apply_button.connect("clicked", lambda w: self._apply_settings(dialog, voice_combo, rate_scale, volume_scale, 
                                                                      read_shortcut_entry, capture_shortcut_entry, 
                                                                      play_shortcut_entry, highlight_check, 
                                                                      minimize_check, read_immediately_check, 
                                                                      mini_controller_check))
        button_box.pack_end(apply_button, False, False, 0)
        
        # Setup voice change handler
        def on_voice_changed(combo):
            voice_id = combo.get_active_id()
            if voice_id:
                self.tts_engine.set_voice(voice_id)
                self.settings["voice_id"] = voice_id
                self._save_settings()
        
        # Connect signals
        voice_combo.connect("changed", on_voice_changed)
        rate_scale.connect("value-changed", self.on_rate_changed)
        volume_scale.connect("value-changed", self.on_volume_changed)
        
        # Ensure window can be closed with escape key
        dialog.connect("key-press-event", lambda w, e: w.destroy() if e.keyval == Gdk.KEY_Escape else None)
        
        # Show all
        dialog.show_all()
        
    def _apply_settings(self, dialog, voice_combo, rate_scale, volume_scale, 
                       read_shortcut_entry, capture_shortcut_entry, 
                       play_shortcut_entry, highlight_check, 
                       minimize_check, read_immediately_check, 
                       mini_controller_check):
        """Apply settings from the dialog"""
        # Save voice setting
        voice_id = voice_combo.get_active_id()
        if voice_id:
            self.settings["voice_id"] = voice_id
            self.tts_engine.set_voice(voice_id)
        
        # Save shortcut settings
        self.settings["shortcut_read_selection"] = read_shortcut_entry.get_text()
        self.settings["shortcut_capture_selection"] = capture_shortcut_entry.get_text()
        self.settings["shortcut_play_pause"] = play_shortcut_entry.get_text()
        
        # Save behavior settings
        self.settings["highlight_text"] = highlight_check.get_active()
        self.settings["minimize_to_tray"] = minimize_check.get_active()
        self.settings["read_immediately"] = read_immediately_check.get_active()
        self.settings["show_mini_controller"] = mini_controller_check.get_active()
        
        # Save settings to file
        self._save_settings()
        
        # Update direct reader settings
        self.direct_reader.update_settings(self.settings)
        
        # Update accelerators
        self._setup_global_hotkeys()
        
        # Give feedback that settings were applied
        dialog.set_title("Settings (Applied)")
        # Reset title after a short delay
        GLib.timeout_add(1500, lambda: dialog.set_title("Settings"))
        
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
        voice_id = self.settings.get("voice_id")
        if voice_id:
            self.tts_engine.set_voice(voice_id)
            
        rate = self.settings.get("rate", 150)
        self.tts_engine.set_rate(rate)
        
        volume = self.settings.get("volume", 100) / 100.0
        self.tts_engine.set_volume(volume)
        
        # Log that we're about to play sample
        logging.debug(f"Playing sample with voice={voice_id}, rate={rate}, volume={volume}")
        
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