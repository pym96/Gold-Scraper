#!/usr/bin/env python3
"""
GoldSpider Service - Main entry point for the combined API and scheduler
"""
import logging
import threading
import time
import signal
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.api import app
from app.scheduler import ScraperScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/service.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("service")

# Create the scheduler
scheduler = ScraperScheduler(interval_minutes=30)

# Add scheduler status endpoint to the API
@app.get("/status")
async def get_status():
    """Get the current status of the scraper and scheduler"""
    return {
        "scheduler_running": scheduler.is_alive(),
        "last_run": scheduler.last_run.isoformat() if scheduler.last_run else None,
        "next_run": scheduler.last_run.isoformat() + " + 30 minutes" if scheduler.last_run else None,
        "api_version": app.version
    }

def run_api_server():
    """Run the FastAPI server with uvicorn"""
    uvicorn.run(app, host="0.0.0.0", port=8000)

def handle_exit(signum, frame):
    """Handle exit signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    scheduler.stop()
    sys.exit(0)

def main():
    """Main entry point for the service"""
    # Ensure necessary directories exist
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    logger.info("Starting Gold Spider service")
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Start the scheduler
        scheduler.start()
        
        # Run the API server (this will block until the server exits)
        run_api_server()
    except Exception as e:
        logger.error(f"Error in service: {e}")
    finally:
        # Ensure scheduler is stopped on exit
        scheduler.stop()
        logger.info("Service shutdown complete")

if __name__ == "__main__":
    main() 