#!/usr/bin/env python3
import uvicorn
from backend.main import app
from backend.config import config
import logging
import logging.handlers
from pathlib import Path

# Setup logging configuration
logging_config = config.logging
log_file = logging_config.get('file', 'log/app.log')
log_level = logging_config.get('level', 'INFO')
log_format = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure log directory exists
if log_file:
    log_path = Path(log_file)
    if log_path.suffix:
        log_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        log_path.mkdir(parents=True, exist_ok=True)

# Configure root logger
root_logger = logging.getLogger()
if log_level:
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
else:
    root_logger.setLevel(logging.INFO)

# Remove existing handlers to avoid duplicates
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Create formatter
formatter = logging.Formatter(log_format)

# File handler with rotation
if log_file:
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=200 * 1024 * 1024,  # 200MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# Log that logging has been set up
logger = logging.getLogger(__name__)
logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")

if __name__ == "__main__":
    uvicorn.run("backend.main:app",
                host=config.server.get('host', '0.0.0.0'),
                port=config.server.get('port', 8000),
                reload=config.server.get('reload', True),
                log_config="uvicorn_log_config.json")
