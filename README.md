# Linux Read Aloud

A Linux application that provides text-to-speech functionality similar to MacOS's Read Aloud feature. This application allows you to select text anywhere on your Linux desktop and have it read aloud to you.

## Features

- Select text and have it read aloud
- Pause, resume, and stop playback
- Adjust speech rate and voice
- System tray integration

## Requirements

- Python 3.6+
- GTK 3
- espeak-ng or festival (TTS engines)

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   sudo apt-get install espeak-ng python3-gi
   ```
3. Run the application:
   ```
   python src/main.py
   ```

## Usage

1. Select text in any application
2. Press the hotkey (default: Ctrl+Alt+S) or use the system tray icon
3. The selected text will be read aloud

## Architecture

- `src/tts/`: Text-to-speech engine interface
- `src/ui/`: GTK-based user interface
- `src/utils/`: Utility functions for text selection and clipboard management

## Testing

The application includes a comprehensive test suite to minimize manual testing time.

### Setting up the test environment

```bash
pip install -r requirements-dev.txt
```

### Running tests

```bash
# Run all tests
make test

# Run unit tests only (no integration tests or tests requiring display)
make unittest

# Run specific test file
python -m pytest tests/test_tts_engine.py

# Generate coverage report
python -m pytest --cov=src
```

See the [tests/README.md](tests/README.md) file for more detailed testing information.

## Development

For development work:

1. Install development dependencies:
   ```
   pip install -r requirements-dev.txt
   ```

2. Install the package in development mode:
   ```
   pip install -e .
   ```

3. Run linting checks:
   ```
   make lint
   ``` 