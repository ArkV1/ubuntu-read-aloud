import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import logging
import json
import os

from ..tts.tts_engine import TTSEngine

class SettingsDialog(Gtk.Dialog):
    """Settings dialog for Read Aloud application"""
    
    def __init__(self, parent, config_path=None):
        super().__init__(
            title="Read Aloud Settings",
            parent=parent,
            flags=Gtk.DialogFlags.MODAL,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )
        )
        
        self.set_default_size(400, 350)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        
        # Default config path
        if config_path is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".config", "read-aloud")
            os.makedirs(config_dir, exist_ok=True)
            self.config_path = os.path.join(config_dir, "settings.json")
        else:
            self.config_path = config_path
            
        # Initialize TTS engine to get available voices
        self.tts_engine = TTSEngine()
        
        # Load current settings
        self.settings = self._load_settings()
        
        # Create UI
        self._build_ui()
        
    def _load_settings(self):
        """Load settings from file"""
        default_settings = {
            "voice_id": None,
            "rate": 150,
            "shortcut_read_selection": "<Primary><Alt>r",
            "shortcut_capture_selection": "<Primary><Alt>s",
            "shortcut_play_pause": "<Primary><Alt>p",
            "highlight_text": True,
            "minimize_to_tray": True,
            "read_immediately": False
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
            
    def _build_ui(self):
        """Build the settings dialog UI"""
        content_area = self.get_content_area()
        content_area.set_spacing(10)
        content_area.set_margin_top(10)
        content_area.set_margin_bottom(10)
        content_area.set_margin_start(10)
        content_area.set_margin_end(10)
        
        # Create notebook (tabbed interface)
        notebook = Gtk.Notebook()
        content_area.pack_start(notebook, True, True, 0)
        
        # Voice settings tab
        voice_grid = Gtk.Grid()
        voice_grid.set_row_spacing(10)
        voice_grid.set_column_spacing(10)
        voice_grid.set_margin_top(10)
        voice_grid.set_margin_bottom(10)
        voice_grid.set_margin_start(10)
        voice_grid.set_margin_end(10)
        
        # Voice selection
        voice_label = Gtk.Label(label="Voice:")
        voice_label.set_halign(Gtk.Align.START)
        voice_grid.attach(voice_label, 0, 0, 1, 1)
        
        self.voice_combo = Gtk.ComboBoxText()
        # Populate voices
        voices = self.tts_engine.get_available_voices()
        active_idx = 0
        for idx, (voice_id, voice_name) in enumerate(voices):
            self.voice_combo.append(voice_id, voice_name)
            if voice_id == self.settings["voice_id"]:
                active_idx = idx
                
        if voices:
            self.voice_combo.set_active(active_idx)
            
        voice_grid.attach(self.voice_combo, 1, 0, 1, 1)
        
        # Rate control
        rate_label = Gtk.Label(label="Rate:")
        rate_label.set_halign(Gtk.Align.START)
        voice_grid.attach(rate_label, 0, 1, 1, 1)
        
        rate_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.rate_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 50, 300, 10)
        self.rate_scale.set_value(self.settings["rate"])
        self.rate_scale.set_hexpand(True)
        
        # Add value labels
        self.rate_scale.add_mark(50, Gtk.PositionType.BOTTOM, "Slow")
        self.rate_scale.add_mark(150, Gtk.PositionType.BOTTOM, "Normal")
        self.rate_scale.add_mark(300, Gtk.PositionType.BOTTOM, "Fast")
        
        rate_box.pack_start(self.rate_scale, True, True, 0)
        voice_grid.attach(rate_box, 1, 1, 1, 1)
        
        # Sample button
        sample_button = Gtk.Button(label="Play Sample")
        sample_button.connect("clicked", self._on_sample_clicked)
        voice_grid.attach(sample_button, 0, 2, 2, 1)
        
        # Add the Voice tab
        notebook.append_page(voice_grid, Gtk.Label(label="Voice"))
        
        # Keyboard shortcuts tab
        shortcuts_grid = Gtk.Grid()
        shortcuts_grid.set_row_spacing(10)
        shortcuts_grid.set_column_spacing(10)
        shortcuts_grid.set_margin_top(10)
        shortcuts_grid.set_margin_bottom(10)
        shortcuts_grid.set_margin_start(10)
        shortcuts_grid.set_margin_end(10)
        
        # Read selection shortcut
        read_shortcut_label = Gtk.Label(label="Read selected text:")
        read_shortcut_label.set_halign(Gtk.Align.START)
        shortcuts_grid.attach(read_shortcut_label, 0, 0, 1, 1)
        
        self.read_shortcut_entry = Gtk.Entry()
        self.read_shortcut_entry.set_text(self.settings["shortcut_read_selection"])
        self.read_shortcut_entry.set_hexpand(True)
        shortcuts_grid.attach(self.read_shortcut_entry, 1, 0, 1, 1)
        
        # Capture selection shortcut
        capture_shortcut_label = Gtk.Label(label="Capture selected text:")
        capture_shortcut_label.set_halign(Gtk.Align.START)
        shortcuts_grid.attach(capture_shortcut_label, 0, 1, 1, 1)
        
        self.capture_shortcut_entry = Gtk.Entry()
        self.capture_shortcut_entry.set_text(self.settings["shortcut_capture_selection"])
        shortcuts_grid.attach(self.capture_shortcut_entry, 1, 1, 1, 1)
        
        # Play/pause shortcut
        play_shortcut_label = Gtk.Label(label="Play/pause:")
        play_shortcut_label.set_halign(Gtk.Align.START)
        shortcuts_grid.attach(play_shortcut_label, 0, 2, 1, 1)
        
        self.play_shortcut_entry = Gtk.Entry()
        self.play_shortcut_entry.set_text(self.settings["shortcut_play_pause"])
        shortcuts_grid.attach(self.play_shortcut_entry, 1, 2, 1, 1)
        
        # Shortcut format help
        format_label = Gtk.Label()
        format_label.set_markup("<small>Format: &lt;Primary&gt; = Ctrl, &lt;Alt&gt;, &lt;Shift&gt;, etc.</small>")
        format_label.set_halign(Gtk.Align.START)
        shortcuts_grid.attach(format_label, 0, 3, 2, 1)
        
        # Add the Shortcuts tab
        notebook.append_page(shortcuts_grid, Gtk.Label(label="Shortcuts"))
        
        # Behavior tab
        behavior_grid = Gtk.Grid()
        behavior_grid.set_row_spacing(10)
        behavior_grid.set_column_spacing(10)
        behavior_grid.set_margin_top(10)
        behavior_grid.set_margin_bottom(10)
        behavior_grid.set_margin_start(10)
        behavior_grid.set_margin_end(10)
        
        # Highlight text
        self.highlight_check = Gtk.CheckButton(label="Highlight text as it is spoken")
        self.highlight_check.set_active(self.settings["highlight_text"])
        behavior_grid.attach(self.highlight_check, 0, 0, 2, 1)
        
        # Minimize to tray
        self.tray_check = Gtk.CheckButton(label="Minimize to system tray when closed")
        self.tray_check.set_active(self.settings["minimize_to_tray"])
        behavior_grid.attach(self.tray_check, 0, 1, 2, 1)
        
        # Read immediately
        self.read_immediately_check = Gtk.CheckButton(
            label="Read text immediately when selected (with shortcut)"
        )
        self.read_immediately_check.set_active(self.settings["read_immediately"])
        behavior_grid.attach(self.read_immediately_check, 0, 2, 2, 1)
        
        notebook.append_page(behavior_grid, Gtk.Label(label="Behavior"))
        
        # Show all widgets
        self.show_all()
        
    def _on_sample_clicked(self, button):
        """Play a sample of the selected voice"""
        voice_id = self.voice_combo.get_active_id()
        rate = int(self.rate_scale.get_value())
        
        if voice_id:
            # Create a temporary engine for the sample
            temp_engine = TTSEngine()
            temp_engine.set_voice(voice_id)
            temp_engine.set_rate(rate)
            temp_engine.speak("This is a sample of the selected voice.")
            
    def get_settings(self):
        """Get current settings from dialog"""
        self.settings["voice_id"] = self.voice_combo.get_active_id()
        self.settings["rate"] = int(self.rate_scale.get_value())
        self.settings["shortcut_read_selection"] = self.read_shortcut_entry.get_text()
        self.settings["shortcut_capture_selection"] = self.capture_shortcut_entry.get_text()
        self.settings["shortcut_play_pause"] = self.play_shortcut_entry.get_text()
        self.settings["highlight_text"] = self.highlight_check.get_active()
        self.settings["minimize_to_tray"] = self.tray_check.get_active()
        self.settings["read_immediately"] = self.read_immediately_check.get_active()
        
        return self.settings
        
    def save(self):
        """Save settings"""
        self.get_settings()
        return self._save_settings() 