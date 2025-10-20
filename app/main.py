"""
Entry point for the FastAPI app.

- Creates the FastAPI instance and sets the app title from settings.
- Initializes logging early so all modules share the same formatter/level.
- Registers the upload router (HTTP routes for home and /upload).
"""

from fastapi import FastAPI
from .core.config import settings
from .core.logging import setup_logging
from .core.tracing import setup_tracing
from .routers.upload import router as upload_router

# Setup logging
logger = setup_logging()
logger.info("🚀 Starting KitabiAI application")

# Create app
app = FastAPI(title=settings.APP_NAME)

# Setup tracing
# tracer = setup_tracing(app)

# Include routers
app.include_router(upload_router)

@app.on_event("startup")
async def startup_event():
    logger.info(f"✅ Application started: {settings.APP_NAME}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Application shutting down")