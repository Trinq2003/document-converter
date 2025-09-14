#!/usr/bin/env python3
"""
Simple script to run the Document Converter API
"""

import uvicorn
from app.main import app
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
