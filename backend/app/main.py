from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import time

from .api.routes import router as api_router
from .config import settings
from .services.metrics import inc_counter, observe_histogram, snapshot


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lecture Navigator API",
        version="0.1.0",
        description="RAG + Agent API to search lecture timestamps",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request timing + metrics middleware
    @app.middleware("http")
    async def add_timing(request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        dur_ms = (time.perf_counter() - start) * 1000
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} {dur_ms:.1f}ms")
        response.headers["X-Response-Time-ms"] = f"{dur_ms:.1f}"
        inc_counter(f"requests_total:{request.url.path}")
        observe_histogram(f"latency_ms:{request.url.path}", dur_ms)
        return response

    # Register API routes
    app.include_router(api_router, prefix="/api")

    # Health endpoint
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # Metrics endpoint
    @app.get("/metrics")
    async def metrics():
        return snapshot()

    return app


# Global app instance for uvicorn
app = create_app()
