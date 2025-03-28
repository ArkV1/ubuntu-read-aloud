import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import logging
import threading
import time

from ..tts.tts_engine import TTSEngine
from .text_selection import TextSelector

class DirectReader:
    """Utility for reading text directly from selection without GUI"""
    
    def __init__(self, settings=None):
        self.tts_engine = TTSEngine()
        self.text_selector = TextSelector()
        self.settings = settings or {}
        self.controller = None
        
        # Configure engine based on settings
        self._apply_settings()
    
    def _apply_settings(self):
        """Apply settings to the TTS engine"""
        if self.settings:
            if self.settings.get("engine_id"):
                self.tts_engine.set_engine(self.settings["engine_id"])
            if self.settings.get("voice_id"):
                self.tts_engine.set_voice(self.settings["voice_id"], self.settings.get("engine_id"))
            if self.settings.get("rate"):
                self.tts_engine.set_rate(self.settings["rate"])
            if self.settings.get("volume"):
                # Convert percentage to decimal
                volume = self.settings.get("volume", 100) / 100.0
                self.tts_engine.set_volume(volume)
    
    def read_selection(self):
        """Read the currently selected text directly"""
        threading.Thread(target=self._read_selection_thread, daemon=True).start()
        
    def _read_selection_thread(self):
        """Get selected text and read it in a separate thread"""
        try:
            # Get selected text
            logging.debug("Attempting to get selected text from screen")
            selected_text = None
            
            # First try to get directly from screen selection
            selected_text = self.text_selector.get_selected_text()
            
            if not selected_text or not selected_text.strip():
                logging.debug("No text found in screen selection, trying clipboard")
                # As a last resort, just use clipboard directly
                import pyperclip
                clipboard_text = pyperclip.paste()
                if clipboard_text and clipboard_text.strip():
                    selected_text = clipboard_text
                    logging.debug("Using text from clipboard as fallback")
                
            if selected_text and selected_text.strip():
                # Trim text to reasonable length for logging
                preview = selected_text[:30].replace('\n', ' ')
                if len(selected_text) > 30:
                    preview += "..."
                logging.debug(f"Reading selected text: {preview}")
                
                # Make sure TTS engine is in a good state
                if hasattr(self.tts_engine, 'is_speaking') and self.tts_engine.is_speaking:
                    logging.debug("TTS engine is busy, stopping previous speech")
                    self.tts_engine.stop()
                    # Allow some time for engine to reset
                    time.sleep(0.2)
                
                # If engine seems stuck, try restarting it
                if hasattr(self.tts_engine, 'is_speaking') and self.tts_engine.is_speaking:
                    logging.warning("TTS engine still marked as speaking, attempting restart")
                    self.tts_engine.restart_engine()
                    # Re-apply settings after restart
                    self._apply_settings()
                
                # If a mini controller is desired, show it
                if self.settings.get("show_mini_controller", True):
                    # If controller already exists but isn't visible, destroy it so we can create a new one
                    if self.controller and not self.controller.get_visible():
                        GLib.idle_add(self._destroy_controller)
                        self.controller = None
                    
                    GLib.idle_add(self._show_controller, selected_text)
                else:
                    # Just read the text directly
                    self.tts_engine.speak(selected_text)
            else:
                logging.warning("No text selected or found in clipboard")
                # Show a notification using GTK
                GLib.idle_add(self._show_no_text_notification)
        except Exception as e:
            logging.error(f"Error in direct reader: {e}")
            # Try to recover from errors
            try:
                self.tts_engine.restart_engine()
                self._apply_settings()
                logging.debug("TTS engine restarted after error")
            except Exception as restart_error:
                logging.error(f"Failed to restart TTS engine: {restart_error}")
    
    def _destroy_controller(self):
        """Safely destroy the controller window"""
        if self.controller:
            logging.debug("Destroying existing controller")
            self.controller.destroy()
            self.controller = None
    
    def _show_controller(self, text):
        """Show a mini floating controller for the reading"""
        try:
            if self.controller is None:
                logging.debug("Creating new controller")
                self.controller = ReaderController(text, self.tts_engine)
            else:
                logging.debug("Updating existing controller")
                self.controller.update_text(text)
                
            self.controller.present()
        except Exception as e:
            logging.error(f"Error showing controller: {e}")
            # Fallback to direct reading if controller fails
            self.tts_engine.speak(text)
        
    def stop(self):
        """Stop reading"""
        self.tts_engine.stop()
        
    def update_settings(self, settings):
        """Update settings"""
        self.settings = settings
        self._apply_settings()

    def _show_no_text_notification(self):
        """Show a notification that no text was selected"""
        dialog = Gtk.MessageDialog(
            transient_for=None,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="No Text Selected"
        )
        dialog.format_secondary_text(
            "Please select text in any application before using the read selection shortcut."
        )
        dialog.connect("response", lambda dialog, response: dialog.destroy())
        dialog.show()


class ReaderController(Gtk.Window):
    """Mini floating controller for direct reading"""
    
    def __init__(self, text, tts_engine):
        Gtk.Window.__init__(self, title="Read Aloud")
        
        self.text = text
        self.tts_engine = tts_engine
        self.is_playing = False
        
        # Set up the UI
        self.set_decorated(False)  # No title bar
        self.set_keep_above(True)  # Stay on top
        self.set_default_size(200, 50)
        
        # Create a box for the UI
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        vbox.set_margin_top(5)
        vbox.set_margin_bottom(5)
        vbox.set_margin_start(5)
        vbox.set_margin_end(5)
        self.add(vbox)
        
        # Create controls box
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        controls_box.set_halign(Gtk.Align.CENTER)
        
        # Play/Pause button
        self.play_button = Gtk.Button.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
        self.play_button.connect("clicked", self.on_play_clicked)
        controls_box.pack_start(self.play_button, False, False, 0)
        
        # Stop button
        stop_button = Gtk.Button.new_from_icon_name("media-playback-stop", Gtk.IconSize.BUTTON)
        stop_button.connect("clicked", self.on_stop_clicked)
        controls_box.pack_start(stop_button, False, False, 0)
        
        # Restart button
        restart_button = Gtk.Button.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON)
        restart_button.set_tooltip_text("Restart TTS engine")
        restart_button.connect("clicked", self.on_restart_clicked)
        controls_box.pack_start(restart_button, False, False, 0)
        
        # Close button
        close_button = Gtk.Button.new_from_icon_name("window-close", Gtk.IconSize.BUTTON)
        close_button.connect("clicked", self.on_close_clicked)
        controls_box.pack_start(close_button, False, False, 0)
        
        vbox.pack_start(controls_box, True, True, 0)
        
        # Show all widgets
        self.show_all()
        
        # Start reading text
        self.start_reading()
        
    def start_reading(self):
        """Start reading the text"""
        try:
            # Make sure engine is not busy before starting
            if hasattr(self.tts_engine, 'is_speaking') and self.tts_engine.is_speaking:
                logging.debug("Engine busy before start_reading, stopping first")
                self.tts_engine.stop()
                time.sleep(0.1)  # Small delay
            
            # Ensure we have text to read    
            if not self.text or not self.text.strip():
                logging.debug("No text to read")
                return
                
            logging.debug("Starting to read text with controller")
            self.is_playing = True
            self.play_button.set_image(
                Gtk.Image.new_from_icon_name("media-playback-pause", Gtk.IconSize.BUTTON)
            )
            
            # Make sure window is visible
            self.present()
            self.show_all()
            
            # Start reading
            self.tts_engine.speak(self.text, callback=self.on_reading_finished)
            logging.debug("Started reading text in controller")
        except Exception as e:
            logging.error(f"Error starting reading: {e}")
            self._update_ui_after_reading()
            self._show_error_message("Could not start text-to-speech. Try restarting the engine.")
        
    def on_play_clicked(self, button):
        """Handle play/pause button click"""
        try:
            if self.is_playing:
                self.tts_engine.pause()
                self.is_playing = False
                self.play_button.set_image(
                    Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
                )
                logging.debug("Paused reading")
            else:
                self.tts_engine.resume()
                self.is_playing = True
                self.play_button.set_image(
                    Gtk.Image.new_from_icon_name("media-playback-pause", Gtk.IconSize.BUTTON)
                )
                logging.debug("Resumed reading")
        except Exception as e:
            logging.error(f"Error toggling play/pause: {e}")
            self._update_ui_after_reading()
            self._show_error_message("Error controlling playback. Try restarting the engine.")
        
    def on_stop_clicked(self, button):
        """Handle stop button click"""
        try:
            self.tts_engine.stop()
            self._update_ui_after_reading()
            logging.debug("Stopped reading")
        except Exception as e:
            logging.error(f"Error stopping: {e}")
            self._update_ui_after_reading()
            
    def on_restart_clicked(self, button):
        """Handle restart engine button click"""
        try:
            logging.debug("Restarting TTS engine from controller")
            success = self.tts_engine.restart_engine()
            if success:
                self._show_info_message("TTS engine restarted successfully")
                # Try reading again
                self.start_reading()
            else:
                self._show_error_message("Failed to restart TTS engine")
        except Exception as e:
            logging.error(f"Error restarting engine: {e}")
            self._show_error_message(f"Error restarting engine: {e}")
        
    def on_close_clicked(self, button):
        """Handle close button click"""
        self.tts_engine.stop()
        self.destroy()
        
    def on_reading_finished(self):
        """Handle reading finished"""
        GLib.idle_add(self._update_ui_after_reading)
        logging.debug("Reading finished")
        
    def _update_ui_after_reading(self):
        """Update UI after reading is finished"""
        self.is_playing = False
        self.play_button.set_image(
            Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
        )
        
    def update_text(self, text):
        """Update the text to read"""
        logging.debug("Updating controller text")
        self.text = text
        
        # Always stop any current speech first
        self.tts_engine.stop()
        self.is_playing = False
        
        # Reset the play button to show "play" icon
        self.play_button.set_image(
            Gtk.Image.new_from_icon_name("media-playback-start", Gtk.IconSize.BUTTON)
        )
        
        # Start reading the new text immediately
        self.start_reading()
        
    def _show_error_message(self, message):
        """Show an error message in a small popup"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="TTS Error"
        )
        dialog.format_secondary_text(message)
        dialog.connect("response", lambda dialog, response: dialog.destroy())
        dialog.show()
        
    def _show_info_message(self, message):
        """Show an info message in a small popup"""
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="TTS Engine"
        )
        dialog.format_secondary_text(message)
        dialog.connect("response", lambda dialog, response: dialog.destroy())
        dialog.show() 