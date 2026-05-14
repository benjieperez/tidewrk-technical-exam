from fastapi import APIRouter
from app.api.ingest import router as ingest_router
from app.api.patients import router as patients_router

api_router = APIRouter()
api_router.include_router(ingest_router, tags=["Ingestion"])
api_router.include_router(patients_router, tags=["Patients"])

__all__ = ["api_router"]
