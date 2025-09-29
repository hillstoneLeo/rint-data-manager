from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from ..config import config

router = APIRouter()

# Setup logging configuration for bootstrap errors
logging_config = config.logging
log_file = 'log/bootstrap_errors.log'
log_level = logging_config.get('level', 'INFO')
log_format = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Ensure log directory exists
log_path = Path(log_file)
if log_path.suffix:
    log_path.parent.mkdir(parents=True, exist_ok=True)
else:
    log_path.mkdir(parents=True, exist_ok=True)

# Configure logging for bootstrap errors
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format=log_format,
    handlers=[
        logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=200 * 1024 * 1024,  # 200MB
            backupCount=5
        ),
        logging.StreamHandler()
    ])

logger = logging.getLogger(__name__)


@router.post("/bootstrap-error")
async def log_bootstrap_error(request: Request):
    """
    Log Bootstrap loading errors from the frontend
    """
    try:
        error_data = await request.json()

        # Log the error with detailed information
        logger.error(
            f"Bootstrap Loading Error - {error_data.get('type', 'Unknown')}")
        logger.error(f"URL: {error_data.get('url', 'Unknown')}")
        logger.error(f"Error: {error_data.get('error', 'Unknown error')}")
        logger.error(
            f"Timestamp: {error_data.get('timestamp', datetime.now().isoformat())}"
        )
        logger.error(f"User Agent: {error_data.get('user_agent', 'Unknown')}")
        logger.error("-" * 50)

        return JSONResponse(status_code=200,
                            content={"message": "Error logged successfully"})

    except Exception as e:
        logger.error(f"Failed to process Bootstrap error log: {str(e)}")
        return JSONResponse(status_code=500,
                            content={"message": "Failed to log error"})
