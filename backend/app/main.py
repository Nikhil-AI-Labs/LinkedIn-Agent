"""FastAPI application entry point."""

import sys
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.errors import AppError
from app.db.session import close_db, init_db, get_engine

# Fix for Windows: psycopg requires SelectorEventLoop, not ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info(
        "Starting LinkedIn AI Agent",
        version=settings.app_version,
        auth_mode=settings.auth_mode,
        browser_provider=settings.browser_provider if settings.auth_mode == "browser" else None,
        debug=settings.debug,
    )

    # Initialize database connection
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

    # Initialize LangGraph checkpointer
    try:
        from app.agents.checkpointer import init_checkpointer
        
        await init_checkpointer()
        logger.info("LangGraph checkpointer initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize checkpointer", error=str(e))
        raise

    # Check Kimi WebBridge service connection (official local service on port 10086)
    if settings.auth_mode == "browser" and settings.browser_provider == "kimi_webbridge":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:10086/status")
                if response.status_code == 200:
                    data = response.json()
                    if data.get("extension_connected"):
                        logger.info(
                            "✅ Kimi WebBridge connected",
                            extension_version=data.get("extension_version"),
                            uptime=data.get("uptime_seconds"),
                        )
                    else:
                        logger.warning(
                            "⚠️  Kimi WebBridge service running but extension NOT connected. "
                            "Open Chrome/Edge with Kimi extension and log into LinkedIn."
                        )
                else:
                    logger.warning("⚠️  Kimi WebBridge service returned non-200 status")
        except Exception as e:
            logger.warning(
                "⚠️  Kimi WebBridge service not reachable. "
                "Install it: powershell -c \"irm https://kimi-web-img.moonshot.cn/webbridge/install.ps1 | iex\"",
                error=str(e),
            )

    # TODO: Start APScheduler for monitoring

    yield

    # Shutdown
    logger.info("Shutting down LinkedIn AI Agent")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Handle custom application errors."""
    logger.error(
        "app_error",
        error_code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "trace_id": request.headers.get("X-Trace-ID"),
                **exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "trace_id": request.headers.get("X-Trace-ID"),
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(
        "unexpected_error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "trace_id": request.headers.get("X-Trace-ID"),
            }
        },
    )


# ============================================================================
# Register Routers
# ============================================================================

from app.api.v1.routes import chat, actions, watchlist, voice_live, linkedin

app.include_router(chat.router)
app.include_router(actions.router)
app.include_router(watchlist.router)
app.include_router(voice_live.router)
app.include_router(linkedin.router)




@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint (no authentication required)."""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.app_version,
            "auth_mode": settings.auth_mode,
        }
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "LinkedIn AI Agent API",
        "version": settings.app_version,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
