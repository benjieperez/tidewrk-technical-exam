import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import api_router
from app.db import init_db
from app.services.s3_service import ensure_bucket_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing database tables...")
    await init_db()
    logger.info("Database tables ready.")

    logger.info("Ensuring S3 bucket exists...")
    try:
        ensure_bucket_exists()
        logger.info("S3 bucket ready.")
    except Exception as e:
        logger.warning(f"S3 bucket check failed (non-fatal): {e}")

    yield

    logger.info("Shutting down.")


app = FastAPI(
    title="Healthcare Data Ingestion API",
    description="Accepts structured healthcare visit data, stores as CSV in S3, "
                "and processes asynchronously via Celery workflows.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
