# Timing Debug Switch

This document describes the timing debug functionality that can be easily enabled/disabled to help with performance analysis.

## Overview

The timing debug system provides detailed performance logging for:
- Backend API endpoints
- Database operations
- DVC service functions
- Frontend JavaScript operations (optional)

## Configuration

### Priority Hierarchy

Settings are applied in this priority order:
1. **Environment Variables** (highest priority)
2. **Configuration File** (`config.yml`)
3. **Default Values** (lowest priority)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TIMING_DEBUG_ENABLED` | `false` | Enable/disable timing debug |
| `TIMING_DEBUG_LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING` |
| `TIMING_DEBUG_INCLUDE_FRONTEND` | `false` | Enable frontend timing logs |

### Configuration File (`config.yml`)

```yaml
timing_debug:
  enabled: false
  log_level: "INFO"
  include_frontend: false
  detailed_logging: false
```

## Usage Examples

### Enable Timing Debug

**Via Environment Variable:**
```bash
TIMING_DEBUG_ENABLED=true uvicorn main:app --host 0.0.0.0 --port 8383
```

**Via Config File:**
```yaml
timing_debug:
  enabled: true
```

### Enable with Different Log Levels

```bash
# DEBUG level (most verbose)
TIMING_DEBUG_ENABLED=true TIMING_DEBUG_LOG_LEVEL=DEBUG uvicorn main:app

# WARNING level (only slow operations)
TIMING_DEBUG_ENABLED=true TIMING_DEBUG_LOG_LEVEL=WARNING uvicorn main:app
```

### Enable Frontend Timing

```bash
TIMING_DEBUG_ENABLED=true TIMING_DEBUG_INCLUDE_FRONTEND=true uvicorn main:app
```

Or in `config.yml`:
```yaml
timing_debug:
  enabled: true
  include_frontend: true
```

### Disable Timing Debug

**Default (disabled):**
```bash
uvicorn main:app --host 0.0.0.0 --port 8383
```

**Explicitly disable:**
```bash
TIMING_DEBUG_ENABLED=false uvicorn main:app
```

## Log Output

### Backend Logs (`log/app.log`)

When enabled, you'll see timing logs like:
```
2025-10-23 15:11:23,674 - backend.routers.data - INFO - TIMING: list_data_items - starting with user_only=False
2025-10-23 15:11:23,674 - backend.routers.data - INFO - TIMING: list_data_items - calling ensure_tables_exist
2025-10-23 15:11:23,679 - backend.routers.data - INFO - TIMING: list_data_items - ensure_tables_exist completed in 0.0045s
2025-10-23 15:11:23,679 - backend.routers.data - INFO - TIMING: list_data_items - calling get_all_data_items
2025-10-23 15:11:23,680 - backend.dvc_service - INFO - TIMING: get_all_data_items - starting query
2025-10-23 15:11:23,682 - backend.dvc_service - INFO - TIMING: get_all_data_items - query completed in 0.0021s, returned 1 items
2025-10-23 15:11:23,683 - backend.dvc_service - INFO - TIMING: get_all_data_items took 0.0028s
2025-10-23 15:11:23,683 - backend.routers.data - INFO - TIMING: list_data_items - get_all_data_items completed in 0.0034s
2025-10-23 15:11:23,683 - backend.routers.data - INFO - TIMING: list_data_items took 0.0092s
```

### Frontend Logs (Browser Console)

When frontend timing is enabled, you'll see console logs like:
```
TIMING: loadCurrentUser - starting
TIMING: loadCurrentUser - fetching /api/auth/me
TIMING: loadCurrentUser - completed via me
TIMING: loadDataItems - starting
TIMING: loadDataItems - fetching /api/data/?user_only=false
TIMING: loadDataItems - got 1 items
TIMING: loadDataItems - completed successfully
```

## Performance Impact

- **When disabled**: Zero performance overhead (decorator returns original function)
- **When enabled**: Minimal overhead (~1-2ms per function call)
- **Caching**: Configuration settings are cached to avoid repeated lookups

## Implementation Details

### Backend Components

1. **Central Timing Utility** (`backend/utils/timing.py`)
   - `@timing_logger` decorator for functions
   - `log_timing()` for manual timing
   - `TimingBlock` context manager

2. **Configuration Integration** (`backend/config.py`)
   - `get_timing_debug_enabled()`
   - `get_timing_debug_log_level()`
   - `get_timing_debug_include_frontend()`

3. **Applied to Key Functions**:
   - `database.py`: `ensure_tables_exist()`
   - `auth.py`: `/me` and `/me-server` endpoints
   - `data.py`: `list_data_items()` endpoint
   - `dvc_service.py`: `get_user_data_items()`, `get_all_data_items()`

### Frontend Components

1. **Configuration Variable**: `TIMING_DEBUG_ENABLED`
2. **Conditional Logging**: All timing logs wrapped in `if (TIMING_DEBUG_ENABLED)`
3. **Functions Tracked**:
   - `loadCurrentUser()`
   - `loadDataItems()`
   - Page initialization
   - API fetch operations

## Testing

Run the test script to verify functionality:

```bash
./test/test_timing_debug.sh
```

This script tests:
- Default disabled state
- Environment variable enable/disable
- Config file settings
- Log level changes
- Priority hierarchy (env var overrides config)

## Troubleshooting

### No Timing Logs Appearing

1. Check if timing debug is enabled:
   ```bash
   echo $TIMING_DEBUG_ENABLED
   ```

2. Verify config file setting:
   ```bash
   grep -A 5 "timing_debug:" config.yml
   ```

3. Check log file location:
   ```bash
   tail -f log/app.log
   ```

### Import Errors

If you see import errors for `utils.timing`, the fallback functions will be used automatically, and timing debug will be disabled.

### Performance Issues

If you experience performance issues with timing debug enabled:
1. Use `WARNING` log level to only log slow operations
2. Disable frontend timing
3. Check for excessive function calls

## Best Practices

1. **Production**: Keep timing debug disabled unless troubleshooting
2. **Development**: Enable when investigating performance issues
3. **Testing**: Use `DEBUG` level for detailed analysis
4. **Monitoring**: Use `WARNING` level to catch slow operations only

## Examples

### Debugging Slow Dashboard Load

```bash
# Enable full timing debug
TIMING_DEBUG_ENABLED=true TIMING_DEBUG_INCLUDE_FRONTEND=true uvicorn main:app

# Then access dashboard and check:
# - Backend logs: tail -f log/app.log
# - Frontend logs: Browser developer tools console
```

### Monitoring Production Performance

```bash
# Only log slow operations (>100ms will show as WARNING)
TIMING_DEBUG_ENABLED=true TIMING_DEBUG_LOG_LEVEL=WARNING uvicorn main:app
```

### Quick Performance Check

```bash
# Enable temporarily for debugging
TIMING_DEBUG_ENABLED=true uvicorn main:app &
curl -s "http://localhost:8383/api/data/public" > /dev/null
grep "TIMING:" log/app.log
pkill -f uvicorn
```