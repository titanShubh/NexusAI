"""Main API router aggregating all sub-routers."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.analytics import router as analytics_router
from app.api.schema import router as schema_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(documents_router, prefix="/documents")
api_router.include_router(chat_router)
api_router.include_router(analytics_router, prefix="/analytics")
api_router.include_router(schema_router, prefix="/schema")
