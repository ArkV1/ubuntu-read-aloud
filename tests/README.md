# Read Aloud Tests

This directory contains the test suite for the Read Aloud application.

## Test Structure

- `test_tts_engine.py`: Tests for the text-to-speech engine
- `test_text_selection.py`: Tests for text selection functionality
- `test_ui.py`: Tests for the UI components
- `test_integration.py`: Integration tests
- `test_cli.py`: Tests for command-line interface
- `run_tests.py`: Script to run all tests
- `conftest.py`: pytest configuration

## Running Tests

### Using pytest (recommended)

To run all tests:
```bash
python -m pytest
```

To run a specific test file:
```bash
python -m pytest tests/test_tts_engine.py
```

To run tests with a specific marker:
```bash
python -m pytest -m "not requires_display"
```

### Using unittest

To run all tests:
```bash
python tests/run_tests.py
```

To run a specific test file:
```bash
python -m unittest tests/test_tts_engine.py
```

### Using make

```bash
make test         # Run all tests
make unittest     # Run unit tests only (not integration or requiring display)
```

## Test Coverage

To generate a test coverage report:
```bash
pip install pytest-cov
python -m pytest --cov=src
```

For a detailed HTML report:
```bash
python -m pytest --cov=src --cov-report=html
```

## Mock Testing Guidelines

Most tests use mock objects to simulate the behavior of real components. This allows testing without actual hardware, display, or speech output. When creating new tests:

1. Use `unittest.mock` for mocking dependencies
2. Use `@patch` to mock imports
3. For UI tests, mock GTK components
4. For tests requiring display, use the `requires_display` marker

## Adding New Tests

1. Create a new test file with name `test_*.py`
2. Use the appropriate unittest framework
3. Add test cases for all code paths
4. Mark tests that require special environments 