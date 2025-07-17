from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.api.routes import router
from app.database.setup import initialize_database
from app.config.settings import settings
import logging
import uvicorn
import time
import json

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log") if settings.environment != "development" else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize system components on startup"""
    logger.info("Starting FAQ AGENTIC FLOW system...")
    
    try:
        initialize_database()
        logger.info("Database initialized successfully")
        
        logger.info("FAQ AGENTIC FLOW system initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise
    
    yield
    
    logger.info("Shutting down FAQ AGENTIC FLOW system")

app = FastAPI(
    title="FAQ AGENTIC FLOW API",
    description="AI-powered FAQ assistant with multi-agent architecture",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.your-domain.com"] if settings.environment == "production" else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.environment == "development" else ["https://your-website.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing and security information"""
    start_time = time.time()
    request_id = f"{int(time.time() * 1000)}-{hash(str(request.url)) % 1000000}"
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    process_time = time.time() - start_time
    
    log_data = {
        "request_id": request_id,
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "status_code": response.status_code,
        "process_time": round(process_time * 1000, 2)  # milliseconds
    }
    
    if response.status_code >= 400:
        logger.warning(f"Request failed: {json.dumps(log_data)}")
    else:
        logger.info(f"Request processed: {json.dumps(log_data)}")
    
    return response

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception for {request.method} {request.url}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )

app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FAQ AGENTIC FLOW API",
        "version": "1.0.0",
        "status": "healthy",
        "environment": settings.environment
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FAQ AGENTIC FLOW API",
        "version": "1.0.0",
        "timestamp": time.time()
    }

@app.get("/metrics")
async def metrics():
    """Basic metrics endpoint for monitoring"""
    if settings.environment == "production":
        return {"message": "Metrics endpoint not available in production"}
    
    import psutil
    import os
    
    return {
        "system": {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        },
        "process": {
            "pid": os.getpid(),
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
            "cpu_percent": psutil.Process().cpu_percent()
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        access_log=False, 
        server_header=False,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": settings.log_level.upper(),
                "handlers": ["default"],
            },
        }
    )