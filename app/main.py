"""
FastAPI application main module
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import uuid
from datetime import datetime

from app.api.routes import router
from app.core.logger import logger
from app.config import settings
from app.models import ErrorResponse


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Professional document conversion service that converts DOCX to Markdown with support for tables, math equations, and images",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if settings.debug else ["yourdomain.com", "*.yourdomain.com"]
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Response {request_id}: {response.status_code} "
            f"in {process_time:.3f}s"
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    # Include API routes
    app.include_router(router, prefix="/api/v1", tags=["Document Conversion"])
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Document Converter API",
            "version": settings.app_version,
            "status": "running",
            "timestamp": datetime.utcnow().isoformat(),
            "docs": "/docs" if settings.debug else "Documentation not available in production"
        }
    
    # Exception handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        logger.error(f"HTTP Exception {request_id}: {exc.status_code} - {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=exc.detail,
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id
            ).model_dump()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        logger.error(f"Validation Error {request_id}: {exc.errors()}")
        
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error="Validation error",
                detail=str(exc.errors()),
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        logger.error(f"Unhandled Exception {request_id}: {str(exc)}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal server error",
                detail="An unexpected error occurred" if not settings.debug else str(exc),
                timestamp=datetime.utcnow().isoformat(),
                request_id=request_id
            ).model_dump()
        )
    
    return app


# Create app instance
app = create_app()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Base directory: {settings.base_dir}")
    
    # Ensure directories exist
    from app.config import dir_manager
    dir_manager.create_directories()
    logger.info("Application directories created/verified")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info(f"Shutting down {settings.app_name}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
