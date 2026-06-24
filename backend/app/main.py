"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
        from sqlalchemy import text
        import os

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
            # Check if customers table exists
            check_query = text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'customers');"
            )
            result = await conn.execute(check_query)
            exists = result.scalar()
            
            if not exists:
                print("Seeding database with customers, employees, and sales tables...")
                base_dir = os.path.dirname(os.path.abspath(__file__))
                sql_path = os.path.join(base_dir, "db", "seed_data.sql")
                if os.path.exists(sql_path):
                    with open(sql_path, "r", encoding="utf-8") as f:
                        sql_content = f.read()
                    
                    # Split statements by semicolon and execute them
                    statements = []
                    current_stmt = []
                    for line in sql_content.splitlines():
                        if line.strip().startswith("--") or not line.strip():
                            continue
                        current_stmt.append(line)
                        if line.strip().endswith(";"):
                            statements.append("\n".join(current_stmt))
                            current_stmt = []
                            
                    for stmt in statements:
                        if stmt.strip():
                            await conn.execute(text(stmt))
                    print("Database tables created and seeded successfully.")
                else:
                    print(f"Seed script not found at path: {sql_path}")
            else:
                print("Database tables initialized successfully (already seeded).")
    except Exception as e:
        print(f"Failed to initialize database tables: {e}")

    # Startup: Initialize Qdrant collection
    try:
        from app.services.vector_service import get_qdrant_client, init_collection
        qdrant = get_qdrant_client()
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception occurred: {exc}", exc_info=True)
    response = JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
    )
    # Manually append CORS headers to avoid browser blocks
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
    return response


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
    """Health check endpoint for Render/uptime monitoring and vector db keep-alive."""
    qdrant_status = "unknown"
    try:
        from app.services.vector_service import get_qdrant_client
        qdrant = get_qdrant_client()
        # Ping Qdrant to reset the inactivity timer and prevent cluster suspension
        qdrant.get_collections()
        qdrant_status = "healthy"
    except Exception as e:
        qdrant_status = f"unhealthy: {e}"
        print(f"Healthcheck Qdrant ping failed: {e}")

    return {
        "status": "healthy",
        "service": "nexus-api",
        "qdrant_status": qdrant_status
    }
