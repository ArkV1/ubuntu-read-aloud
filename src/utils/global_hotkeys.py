import logging
import threading
import time
from Xlib import X, XK, display
from Xlib.protocol import event

class GlobalHotkeys:
    """Implements global keyboard shortcuts using X11"""
    
    def __init__(self):
        """Initialize the global hotkey manager"""
        self.display = display.Display()
        self.screen = self.display.screen()
        self.root = self.screen.root
        self.running = False
        self.thread = None
        self.hotkeys = {}
        self.modifier_masks = {
            'alt': X.Mod1Mask,
            'ctrl': X.ControlMask,
            'shift': X.ShiftMask,
            'super': X.Mod4Mask
        }
        
    def _grab_keyboard(self):
        """Setup global key binding"""
        try:
            # Ensure we have some keys registered
            if not self.hotkeys:
                logging.warning("No hotkeys registered, not grabbing keyboard")
                return False
                
            # Try to grab all registered hotkeys
            for key_combo, callback in self.hotkeys.items():
                keycode, modifiers = key_combo
                
                # Grab the key
                try:
                    self.root.grab_key(keycode, modifiers, 1, X.GrabModeAsync, X.GrabModeAsync)
                    logging.debug(f"Grabbed key {keycode} with modifiers {modifiers}")
                except Exception as e:
                    logging.error(f"Failed to grab key {keycode}: {e}")
                    
            # Make sure X server processes the grab
            self.display.sync()
            return True
            
        except Exception as e:
            logging.error(f"Error grabbing keyboard: {e}")
            return False
            
    def _ungrab_keyboard(self):
        """Release keyboard grab"""
        try:
            # Ungrab all keys
            self.root.ungrab_key(X.AnyKey, X.AnyModifier, self.root)
            self.display.sync()
            logging.debug("Released all keyboard grabs")
        except Exception as e:
            logging.error(f"Error ungrabbing keyboard: {e}")
            
    def _key_combo_to_x11(self, key_combo):
        """Convert a GTK-style key combo to X11 keycode and modifiers"""
        # Parse GTK accelerator string like <Primary><Alt>r
        modifiers = 0
        key = None
        
        # Convert the string into parts
        parts = key_combo.replace("<", " <").replace(">", "> ").split()
        
        # Process each part
        for part in parts:
            part = part.strip("<>")
            if part == "Primary":
                modifiers |= X.ControlMask
            elif part == "Alt":
                modifiers |= X.Mod1Mask
            elif part == "Shift":
                modifiers |= X.ShiftMask
            elif part == "Super":
                modifiers |= X.Mod4Mask
            elif len(part) == 1:  # Single character key
                key = part.lower()
        
        if not key:
            logging.error(f"No key specified in combo: {key_combo}")
            return None, 0
            
        # Convert key string to keycode
        keycode = self.display.keysym_to_keycode(XK.string_to_keysym(key))
        if not keycode:
            logging.error(f"Could not convert key {key} to keycode")
            return None, 0
            
        return keycode, modifiers
        
    def register_hotkey(self, key_combo, callback):
        """Register a hotkey with callback"""
        keycode, modifiers = self._key_combo_to_x11(key_combo)
        if keycode:
            self.hotkeys[(keycode, modifiers)] = callback
            logging.debug(f"Registered hotkey {key_combo} -> {keycode}, {modifiers}")
            return True
        return False
        
    def unregister_hotkey(self, key_combo):
        """Unregister a hotkey"""
        keycode, modifiers = self._key_combo_to_x11(key_combo)
        if keycode and (keycode, modifiers) in self.hotkeys:
            del self.hotkeys[(keycode, modifiers)]
            logging.debug(f"Unregistered hotkey {key_combo}")
            return True
        return False
        
    def update_hotkeys(self, hotkey_map):
        """Update all hotkeys at once"""
        # Stop listening if already running
        was_running = self.running
        if was_running:
            self.stop()
            
        # Clear existing hotkeys
        self.hotkeys = {}
        
        # Register new hotkeys
        for key_combo, callback in hotkey_map.items():
            self.register_hotkey(key_combo, callback)
            
        # Resume if was running
        if was_running:
            self.start()
            
    def _listen_keyboard(self):
        """Listen for keyboard events"""
        self.root.change_attributes(event_mask=X.KeyPressMask)
        
        while self.running:
            try:
                # Check for pending events
                if self.display.pending_events():
                    event = self.display.next_event()
                    
                    # Handle key press event
                    if event.type == X.KeyPress:
                        key_combo = (event.detail, event.state)
                        if key_combo in self.hotkeys:
                            callback = self.hotkeys[key_combo]
                            # Run callback in main thread via GLib if possible
                            logging.debug(f"Hotkey pressed: {key_combo}")
                            try:
                                # Try to use GLib for thread safety
                                from gi.repository import GLib
                                GLib.idle_add(callback)
                            except (ImportError, AttributeError):
                                # Fall back to direct call
                                callback()
                                
                # Avoid busy waiting
                time.sleep(0.01)
                                
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    logging.error(f"Error in keyboard listener: {e}")
                    time.sleep(0.5)  # Avoid spamming logs if there's a persistent error
                
    def start(self):
        """Start listening for hotkeys"""
        if self.running:
            return
            
        self.running = True
        if self._grab_keyboard():
            self.thread = threading.Thread(target=self._listen_keyboard, daemon=True)
            self.thread.start()
            logging.debug("Global hotkey listener started")
        else:
            self.running = False
            logging.error("Failed to grab keyboard, hotkeys not active")
            
    def stop(self):
        """Stop listening for hotkeys"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            
        self._ungrab_keyboard()
        logging.debug("Global hotkey listener stopped")
        
    def __del__(self):
        """Cleanup resources"""
        self.stop() 