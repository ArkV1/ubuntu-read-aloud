import pyperclip
import logging
import subprocess
from Xlib import display, X
import time

class TextSelector:
    """Utility for working with text selection in X11"""
    
    def __init__(self):
        self.previous_clipboard = None
        
    def get_selected_text(self):
        """Get currently selected text from X selection (primary)"""
        # First try to get the primary selection directly
        primary_text = self.get_primary_selection()
        if primary_text and primary_text.strip():
            logging.debug(f"Got text from primary selection: {len(primary_text)} chars")
            return primary_text
            
        # If that fails, try clipboard method
        try:
            logging.debug("Primary selection empty, trying clipboard method")
            # Save current clipboard
            self.previous_clipboard = pyperclip.paste()
            
            # Simulate Ctrl+C to copy selected text to clipboard
            self._simulate_copy()
            
            # Small delay to ensure clipboard is updated
            time.sleep(0.2)  # Slightly longer delay for reliability
            
            # Get text from clipboard
            selected_text = pyperclip.paste()
            
            # Only restore previous clipboard if we got something new
            if selected_text != self.previous_clipboard and self.previous_clipboard:
                pyperclip.copy(self.previous_clipboard)
                
            if selected_text and selected_text.strip():
                logging.debug(f"Got text via clipboard: {len(selected_text)} chars")
                return selected_text
            else:
                logging.debug("No text found in clipboard after simulating copy")
                return ""
        except Exception as e:
            logging.error(f"Error getting selected text: {e}")
            return ""
            
    def _simulate_copy(self):
        """Simulate Ctrl+C key press to copy selected text"""
        # Try multiple methods in order of preference
        methods = [
            self._simulate_copy_xdotool,
            self._simulate_copy_xlib
        ]
        
        for method in methods:
            try:
                if method():
                    return True
            except Exception as e:
                logging.error(f"Error in {method.__name__}: {e}")
                continue
                
        return False
            
    def _simulate_copy_xdotool(self):
        """Use xdotool to simulate Ctrl+C"""
        try:
            subprocess.run(["xdotool", "key", "ctrl+c"], check=True, timeout=1)
            return True
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logging.error(f"xdotool method failed: {e}")
            return False
            
    def _simulate_copy_xlib(self):
        """Use X11 directly to simulate Ctrl+C"""
        try:
            d = display.Display()
            root = d.screen().root
            window = d.get_input_focus().focus
            
            # Create fake Ctrl+C key event
            root.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
            
            # Get key codes
            keycode_ctrl = d.keysym_to_keycode(X.XK_Control_L)
            keycode_c = d.keysym_to_keycode(X.XK_c)
            
            # Press Ctrl
            event = X.KeyPress(
                time=int(time.time()),
                root=root,
                window=window,
                same_screen=1,
                child=X.NONE,
                root_x=0, root_y=0, event_x=0, event_y=0,
                state=0,
                detail=keycode_ctrl
            )
            root.send_event(event, propagate=True)
            
            # Press C
            event = X.KeyPress(
                time=int(time.time()),
                root=root,
                window=window,
                same_screen=1,
                child=X.NONE,
                root_x=0, root_y=0, event_x=0, event_y=0,
                state=X.ControlMask,
                detail=keycode_c
            )
            root.send_event(event, propagate=True)
            
            # Release C
            event = X.KeyRelease(
                time=int(time.time()),
                root=root,
                window=window,
                same_screen=1,
                child=X.NONE,
                root_x=0, root_y=0, event_x=0, event_y=0,
                state=X.ControlMask,
                detail=keycode_c
            )
            root.send_event(event, propagate=True)
            
            # Release Ctrl
            event = X.KeyRelease(
                time=int(time.time()),
                root=root,
                window=window,
                same_screen=1,
                child=X.NONE,
                root_x=0, root_y=0, event_x=0, event_y=0,
                state=0,
                detail=keycode_ctrl
            )
            root.send_event(event, propagate=True)
            
            d.ungrab_keyboard(X.CurrentTime)
            d.flush()
            return True
        except Exception as e:
            logging.error(f"X11 direct method failed: {e}")
            return False
            
    def get_primary_selection(self):
        """Get text from X primary selection"""
        methods = [
            self._get_selection_via_xclip,
            self._get_selection_via_xsel,
            self._get_selection_via_pyperclip
        ]
        
        for method in methods:
            try:
                text = method()
                if text:
                    return text
            except Exception as e:
                logging.error(f"Error in {method.__name__}: {e}")
                continue
                
        return ""
        
    def _get_selection_via_xclip(self):
        """Get text selection using xclip"""
        try:
            result = subprocess.run(
                ["xclip", "-o", "-selection", "primary"],
                capture_output=True,
                text=True,
                check=True,
                timeout=1
            )
            return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logging.debug(f"xclip method failed: {e}")
            return ""
            
    def _get_selection_via_xsel(self):
        """Get text selection using xsel"""
        try:
            result = subprocess.run(
                ["xsel", "-p"],
                capture_output=True,
                text=True,
                check=True,
                timeout=1
            )
            return result.stdout
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logging.debug(f"xsel method failed: {e}")
            return ""
            
    def _get_selection_via_pyperclip(self):
        """Try to get selection via pyperclip's paste function"""
        try:
            # Unfortunately pyperclip doesn't have direct access to X11 PRIMARY selection
            # This is just a fallback that might work on some systems
            return pyperclip.paste()
        except Exception as e:
            logging.debug(f"pyperclip method failed: {e}")
            return "" 