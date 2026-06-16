"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient

from app.api.router import api_router
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables
    try:
        from app.db.database import engine
        from app.db.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")

    # Startup: Initialize Qdrant collection
    try:
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        # We will import the actual init function once vector service is set up
        from app.services.vector_service import init_collection
        init_collection(qdrant)
        print("Qdrant collections initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize Qdrant collection: {e}")
        
    yield
    # Shutdown: Clean up connections if needed


app = FastAPI(
    title="NexusAI Enterprise Platform API",
    description="Backend API for hybrid RAG + Text-to-SQL multi-agent orchestration",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Welcome endpoint."""
    return {
        "message": "Welcome to the NexusAI Enterprise Platform API.",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Render/uptime monitoring."""
    return {"status": "healthy", "service": "nexus-api"}
