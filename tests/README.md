# Tests for pyTwitchAPI

This directory contains unit tests for the pyTwitchAPI library.

## Running Tests

Install test dependencies:
```bash
pip install pytest pytest-asyncio
```

Run all tests:
```bash
pytest tests/
```

Run with verbose output:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_chat_vip_status.py -v
```

## Test Coverage

- `test_chat_vip_status.py` - VIP status detection and caching in Chat class
