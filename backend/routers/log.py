from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
from datetime import datetime

router = APIRouter()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bootstrap_errors.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@router.post("/bootstrap-error")
async def log_bootstrap_error(request: Request):
    """
    Log Bootstrap loading errors from the frontend
    """
    try:
        error_data = await request.json()
        
        # Log the error with detailed information
        logger.error(f"Bootstrap Loading Error - {error_data.get('type', 'Unknown')}")
        logger.error(f"URL: {error_data.get('url', 'Unknown')}")
        logger.error(f"Error: {error_data.get('error', 'Unknown error')}")
        logger.error(f"Timestamp: {error_data.get('timestamp', datetime.now().isoformat())}")
        logger.error(f"User Agent: {error_data.get('user_agent', 'Unknown')}")
        logger.error("-" * 50)
        
        return JSONResponse(
            status_code=200,
            content={"message": "Error logged successfully"}
        )
        
    except Exception as e:
        logger.error(f"Failed to process Bootstrap error log: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": "Failed to log error"}
        )