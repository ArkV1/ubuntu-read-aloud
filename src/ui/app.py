import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

import signal
import logging

from .app_window import ReadAloudWindow

class ReadAloudApp(Gtk.Application):
    """Main Read Aloud application class"""
    
    def __init__(self):
        logging.debug("Initializing ReadAloudApp")
        Gtk.Application.__init__(
            self,
            application_id="com.github.readaloud",
            flags=0
        )
        
        # Initialize system tray indicator
        self.indicator = None
        logging.debug("ReadAloudApp initialized")
        
    def do_activate(self):
        """Called when the application is activated"""
        logging.debug("Activating application")
        # Get the current window or create one if necessary
        window = self.get_window()
        window.present()
        
        # Initialize system tray indicator
        self._init_indicator()
        logging.debug("Application activated")
        
    def do_startup(self):
        """Called when application starts"""
        logging.debug("Application starting up")
        Gtk.Application.do_startup(self)
        
        # Handle Ctrl+C gracefully
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        logging.debug("Application startup complete")
        
    def get_window(self):
        """Get the current window or create a new one"""
        window = self.get_active_window()
        if not window:
            logging.debug("Creating new application window")
            window = ReadAloudWindow(self)
            logging.debug("Window created")
        else:
            logging.debug("Reusing existing window")
        return window
        
    def _init_indicator(self):
        """Initialize system tray indicator"""
        try:
            gi.require_version('AppIndicator3', '0.1')
            from gi.repository import AppIndicator3
            
            self.indicator = AppIndicator3.Indicator.new(
                "read-aloud",
                "accessories-text-editor",
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS
            )
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            
            # Create indicator menu
            menu = Gtk.Menu()
            
            # Read selected text item
            read_item = Gtk.MenuItem(label="Read Selected Text")
            read_item.connect("activate", self._on_read_selected)
            menu.append(read_item)
            
            # Separator
            menu.append(Gtk.SeparatorMenuItem())
            
            # Show window item
            show_item = Gtk.MenuItem(label="Show Window")
            show_item.connect("activate", self._on_show_window)
            menu.append(show_item)
            
            # Quit item
            quit_item = Gtk.MenuItem(label="Quit")
            quit_item.connect("activate", self._on_quit)
            menu.append(quit_item)
            
            menu.show_all()
            self.indicator.set_menu(menu)
            
        except (ImportError, ValueError):
            logging.warning("AppIndicator3 not available, system tray icon disabled")
            self.indicator = None
            
    def _on_read_selected(self, widget):
        """Read selected text from indicator menu"""
        window = self.get_window()
        window.on_get_text_clicked(None)
        GLib.timeout_add(500, window.on_read_clicked, None)
        
    def _on_show_window(self, widget):
        """Show main window from indicator menu"""
        window = self.get_window()
        window.present()
        
    def _on_quit(self, widget):
        """Quit application from indicator menu"""
        # Clean up TTS engine resources
        window = self.get_active_window()
        if window and hasattr(window, 'tts_engine'):
            logging.debug("TTS engine resources cleaned up")
            
        self.quit()
        
    def do_shutdown(self):
        """Called when the application is shutting down"""
        logging.debug("Application shutting down")
        
        # If we have a window, clean up its resources
        window = self.get_active_window()
        if window:
            if hasattr(window, 'global_hotkeys'):
                window.global_hotkeys.stop()
                logging.debug("Global hotkeys stopped")
                
            if hasattr(window, 'tts_engine'):
                window.tts_engine.cleanup()
                logging.debug("TTS engine resources cleaned up")
            
        Gtk.Application.do_shutdown(self)
        logging.debug("Application shutdown complete") 