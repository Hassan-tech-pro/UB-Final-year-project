import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .core.config import settings, PROJECT_ROOT
from .core.security import SecurityError
from .api.routes import api_router
from .api.websocket import ws_router
from .evaluation.benchmark_suite import benchmark_suite

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agentic_system")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup & shutdown events."""
    logger.info("Initializing Agentic AI Task Automation & Verification System...")
    settings.init_directories()
    # Pre-generate sample files for immediate testing
    benchmark_suite.ensure_sample_files()
    logger.info(f"System ready! Storage workspace at: {settings.WORKSPACE_DIR}")
    yield
    logger.info("Shutting down Agentic AI system.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Stateful Agentic AI Task Automation, Execution, Verification, and Self-Healing Engine.",
    lifespan=lifespan
)

# CORS Middleware
origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
@app.exception_handler(SecurityError)
async def security_exception_handler(request: Request, exc: SecurityError):
    return JSONResponse(
        status_code=403,
        content={"detail": str(exc), "error_type": "SecurityViolation"}
    )

# Include Routers
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)

# Mount frontend static build if present
frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    logger.info(f"Mounting frontend production bundle from: {frontend_dist}")
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Do not catch api or ws
        if full_path.startswith("api") or full_path.startswith("ws"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def root():
        return {
            "system": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "provider": settings.LLM_PROVIDER,
            "docs_url": "/docs"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
