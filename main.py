#!/usr/bin/env python3
import uvicorn
from backend.main import app
from backend.config import config

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app", 
        host=config.server.get('host', '0.0.0.0'), 
        port=config.server.get('port', 8000),
        reload=config.server.get('reload', True)
    )
