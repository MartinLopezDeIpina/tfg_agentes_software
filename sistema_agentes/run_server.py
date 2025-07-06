#!/usr/bin/env python3
"""
Run the Quart application with Uvicorn ASGI server.
"""
import uvicorn
from src.web_app.app_config import Config

if __name__ == "__main__":
    uvicorn.run(
        "src.web_app.app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level="info"
    )