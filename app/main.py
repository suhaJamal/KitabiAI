# app/main.py
"""
Entry point for the FastAPI app.

- Creates the FastAPI instance and sets the app title from settings.
- Initializes logging early so all modules share the same formatter/level.
- Registers the upload router (HTTP routes for home and /upload).
"""


from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from .core.config import settings
from .core.logging import setup_logging
from .routers.upload import router as upload_router
from .routers.generation import router as generation_router
from .routers.library import router as library_router
from .routers.admin import router as admin_router
from .routers.summarization import router as summarization_router
from .routers.rag import router as rag_router
from .routers.auth import router as auth_router, verify_session_token, SESSION_COOKIE

# Setup logging
logger = setup_logging()
logger.info("🚀 Starting KitabiAI application")

# Public path prefixes — no auth required
_PUBLIC_PREFIXES = (
    "/library",
    "/books/",
    "/api/",
    "/health",
    "/version",
    "/static/",
    "/admin/login",
    "/admin/logout",
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path == p or path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)
        token = request.cookies.get(SESSION_COOKIE)
        if not verify_session_token(token):
            return RedirectResponse("/admin/login", status_code=303)
        return await call_next(request)


# Create app
app = FastAPI(title=settings.APP_NAME)
app.add_middleware(AuthMiddleware)

# Serve static assets (logo, favicon, etc.)
_static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_path)), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(generation_router)
app.include_router(library_router)
app.include_router(admin_router)
app.include_router(summarization_router)
app.include_router(rag_router)


# Version endpoint to verify deployment
@app.get("/version")
async def get_version():
    """Return app version to verify deployment"""
    return {
        "version": "2.0.0-gibberish-fix",
        "features": [
            "skip_first_3_pages",
            "gibberish_detection",
            "ocr_sampling_10_pages",
            "unexpected_language_fallback"
        ],
        "deployed_at": "2026-01-08"
    }

# Health check endpoint for Docker
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker."""
    return {"status": "healthy", "service": "kitabiai"}

# Library homepage (index.html)
@app.get("/library")
async def library_home():
    """Serve the library homepage."""
    index_path = Path(__file__).parent / "index.html"
    return FileResponse(index_path)

@app.on_event("startup")
async def startup_event():
    logger.info(f"✅ Application started: {settings.APP_NAME}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Application shutting down")