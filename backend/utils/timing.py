"""
Central timing utility for performance debugging.

This module provides timing decorators and utilities that can be
enabled/disabled via configuration to help with performance analysis.
"""

import time
import functools
import logging
from typing import Callable, Any, Optional

from ..config import config


# Global logger for timing
logger = logging.getLogger(__name__)

# Cache the timing debug setting to avoid repeated config lookups
_timing_debug_enabled = None
_timing_debug_log_level = None


def _is_timing_debug_enabled() -> bool:
    """Check if timing debug is enabled (cached for performance)."""
    global _timing_debug_enabled
    if _timing_debug_enabled is None:
        _timing_debug_enabled = config.get_timing_debug_enabled()
    return _timing_debug_enabled


def _get_timing_debug_log_level() -> str:
    """Get timing debug log level (cached for performance)."""
    global _timing_debug_log_level
    if _timing_debug_log_level is None:
        _timing_debug_log_level = config.get_timing_debug_log_level()
    return _timing_debug_log_level


def timing_logger(func: Optional[Callable] = None, *, name: Optional[str] = None) -> Callable:
    """
    Decorator to log function execution time when timing debug is enabled.
    
    Args:
        func: Function to decorate
        name: Custom name for logging (defaults to function name)
    
    Returns:
        Decorated function or no-op decorator if timing debug is disabled
    """
    def decorator(f: Callable) -> Callable:
        # If timing debug is disabled, return the original function unchanged
        if not _is_timing_debug_enabled():
            return f
        
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = name or getattr(f, '__name__', 'unknown_function')
            
            try:
                result = f(*args, **kwargs)
                end_time = time.time()
                duration = end_time - start_time
                
                # Use the configured log level
                log_level = _get_timing_debug_log_level()
                if log_level == 'DEBUG':
                    logger.debug(f"TIMING: {func_name} took {duration:.4f}s")
                elif log_level == 'WARNING':
                    logger.warning(f"TIMING: {func_name} took {duration:.4f}s")
                else:  # INFO or default
                    logger.info(f"TIMING: {func_name} took {duration:.4f}s")
                
                return result
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                logger.error(f"TIMING: {func_name} failed after {duration:.4f}s: {e}")
                raise
        
        return wrapper
    
    # Handle both @timing_logger and @timing_logger(name="custom") usage
    if func is None:
        return decorator
    else:
        return decorator(func)


def log_timing(message: str, start_time: Optional[float] = None) -> float:
    """
    Log a timing message with optional start time.
    
    Args:
        message: Message to log
        start_time: If provided, calculates duration from this time
        
    Returns:
        Current time (can be used as start_time for next call)
    """
    if not _is_timing_debug_enabled():
        return time.time()
    
    current_time = time.time()
    
    if start_time is not None:
        duration = current_time - float(start_time)
        log_level = _get_timing_debug_log_level()
        if log_level == 'DEBUG':
            logger.debug(f"TIMING: {message} took {duration:.4f}s")
        elif log_level == 'WARNING':
            logger.warning(f"TIMING: {message} took {duration:.4f}s")
        else:  # INFO or default
            logger.info(f"TIMING: {message} took {duration:.4f}s")
    else:
        log_level = _get_timing_debug_log_level()
        if log_level == 'DEBUG':
            logger.debug(f"TIMING: {message}")
        elif log_level == 'WARNING':
            logger.warning(f"TIMING: {message}")
        else:  # INFO or default
            logger.info(f"TIMING: {message}")
    
    return current_time


def reset_timing_cache():
    """Reset the cached timing debug settings (useful for testing)."""
    global _timing_debug_enabled, _timing_debug_log_level
    _timing_debug_enabled = None
    _timing_debug_log_level = None


# Context manager for timing blocks
class TimingBlock:
    """Context manager for timing blocks of code."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        if _is_timing_debug_enabled():
            self.start_time = time.time()
            log_level = _get_timing_debug_log_level()
            if log_level == 'DEBUG':
                logger.debug(f"TIMING: {self.name} - starting")
            elif log_level == 'WARNING':
                logger.warning(f"TIMING: {self.name} - starting")
            else:  # INFO or default
                logger.info(f"TIMING: {self.name} - starting")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if _is_timing_debug_enabled() and self.start_time is not None:
            end_time = time.time()
            duration = end_time - self.start_time
            
            if exc_type is not None:
                logger.error(f"TIMING: {self.name} failed after {duration:.4f}s: {exc_val}")
            else:
                log_level = _get_timing_debug_log_level()
                if log_level == 'DEBUG':
                    logger.debug(f"TIMING: {self.name} completed in {duration:.4f}s")
                elif log_level == 'WARNING':
                    logger.warning(f"TIMING: {self.name} completed in {duration:.4f}s")
                else:  # INFO or default
                    logger.info(f"TIMING: {self.name} completed in {duration:.4f}s")