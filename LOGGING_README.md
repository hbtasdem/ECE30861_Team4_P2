# Logging System Documentation

## Overview

This project includes a comprehensive logging system that provides:
- **Multiple verbosity levels** (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **File and console output** with different formats
- **Log rotation** and management
- **Environment variable configuration**
- **Structured logging** with correlation IDs
- **Performance logging** utilities

## Quick Start

### Basic Usage

```python
from phase1metrics.logging_config import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Use different log levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Something unexpected happened")
logger.error("An error occurred")
logger.critical("Critical system error")
```

### Performance Logging

```python
from phase1metrics.logging_config import log_performance
import time

start_time = time.time()
# ... do some work ...
log_performance("operation_name", time.time() - start_time, logger)
```

### Error Logging with Context

```python
from phase1metrics.logging_config import log_error_with_context

try:
    # ... risky operation ...
    pass
except Exception as e:
    log_error_with_context(e, "function_name", logger)
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONSOLE_LOG_LEVEL` | `INFO` | Log level for console output |
| `FILE_LOG_LEVEL` | `DEBUG` | Log level for file output |
| `LOG_FORMAT` | `detailed` | Format type (simple, detailed, json) |
| `MAX_LOG_FILE_SIZE` | `10485760` | Max log file size in bytes (10MB) |
| `LOG_BACKUP_COUNT` | `5` | Number of backup files to keep |

### Programmatic Configuration

```python
from phase1metrics.logging_config import set_log_level

# Change log level at runtime
set_log_level("DEBUG")
```

## Log Formats

### Simple Format
```
14:30:25 - module_name - INFO - This is a message
```

### Detailed Format (Default)
```
2024-01-15 14:30:25 - module_name - INFO - file.py:42 - This is a message
```

### JSON Format
```json
{
  "timestamp": "2024-01-15T14:30:25.123456",
  "level": "INFO",
  "logger": "module_name",
  "message": "This is a message",
  "module": "file.py",
  "function": "function_name",
  "line": 42
}
```

## Log Files

- **Location**: `logs/` directory (created automatically)
- **Naming**: `{module_name}_{YYYYMMDD}.log`
- **Rotation**: Automatic when file exceeds `MAX_LOG_FILE_SIZE`
- **Retention**: Keeps `LOG_BACKUP_COUNT` backup files

## Advanced Features

### Correlation IDs

For request tracing across multiple modules:

```python
# Set correlation ID for all future logs
correlation_id = "req_12345"
logger = get_logger(__name__, correlation_id)

# All log messages will include the correlation ID
logger.info("Processing request")
```

### Custom Formatters

The system supports three built-in formatters:
- `simple`: Basic timestamp and message
- `detailed`: Includes file, line, and function info
- `json`: Structured JSON output

### Log Rotation

Log files are automatically rotated when they exceed the maximum size:
- Original file is renamed with `.1` suffix
- New log file is created
- Old backups are rotated (`.1` → `.2`, etc.)
- Oldest backup is deleted when limit is reached

## Integration with Existing Code

The logging system has been integrated into existing modules:

### Before (Old System)
```python
import os

if int(os.getenv("LOG_LEVEL", "0")) > 0:
    print(f"[ERROR] Failed to fetch model info: {e}")
```

### After (New System)
```python
from .logging_config import get_logger, log_error_with_context

logger = get_logger(__name__)
log_error_with_context(e, "Failed to fetch model info", logger)
```

## Testing

Run the logging tests:

```bash
python -m pytest tests/test_logging_config.py -v
```

## Examples

See `phase1metrics/logging_example.py` for comprehensive usage examples.

## Migration Guide

### From Old System

1. **Replace print statements**:
   ```python
   # Old
   print(f"[ERROR] Error message: {e}")
   
   # New
   logger.error(f"Error message: {e}")
   ```

2. **Replace LOG_LEVEL checks**:
   ```python
   # Old
   if int(os.getenv("LOG_LEVEL", "0")) > 0:
       print(f"[ERROR] {message}")
   
   # New
   logger.error(message)
   ```

3. **Add performance logging**:
   ```python
   # Old
   start_time = time.time()
   # ... work ...
   end_time = time.time()
   print(f"Operation took {end_time - start_time:.3f}s")
   
   # New
   start_time = time.time()
   # ... work ...
   log_performance("operation_name", time.time() - start_time, logger)
   ```

## Best Practices

1. **Use appropriate log levels**:
   - `DEBUG`: Detailed information for debugging
   - `INFO`: General information about program execution
   - `WARNING`: Something unexpected but not an error
   - `ERROR`: An error occurred but program can continue
   - `CRITICAL`: Serious error that may cause program to stop

2. **Include context in messages**:
   ```python
   # Good
   logger.error(f"Failed to fetch model {model_id}: {e}")
   
   # Bad
   logger.error("Failed to fetch model")
   ```

3. **Use performance logging for timing**:
   ```python
   # Good
   log_performance("api_call", duration, logger)
   
   # Bad
   logger.info(f"API call took {duration:.3f}s")
   ```

4. **Don't log sensitive information**:
   ```python
   # Good
   logger.debug(f"Processing user {user_id}")
   
   # Bad
   logger.debug(f"Processing user {user_id} with password {password}")
   ```

## Troubleshooting

### Logs not appearing
- Check `CONSOLE_LOG_LEVEL` environment variable
- Ensure logger level is set correctly
- Verify log files are being created in `logs/` directory

### Performance issues
- Reduce `FILE_LOG_LEVEL` to `WARNING` or `ERROR`
- Increase `MAX_LOG_FILE_SIZE` to reduce rotation frequency
- Use `simple` format instead of `detailed` or `json`

### Log files too large
- Decrease `MAX_LOG_FILE_SIZE`
- Increase `LOG_BACKUP_COUNT` for more retention
- Consider using `json` format for better compression
