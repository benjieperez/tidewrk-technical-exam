import os
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import IngestResponse, VisitRecord
from app.services.s3_service import save_csv_locally, upload_csv_to_s3

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOADS_DIR = os.getenv("UPLOADS_DIR", "uploads")


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest(records: list[VisitRecord]):
    """
    Accept a JSON array of visit records, store as CSV locally and in S3,
    then dispatch a Celery task for async processing.
    """
    if not records:
        raise HTTPException(status_code=400, detail="Payload must contain at least one record.")

    rows = [
        {
            "mrn": r.mrn,
            "first_name": r.first_name,
            "last_name": r.last_name,
            "birth_date": str(r.birth_date),
            "visit_account_number": r.visit_account_number,
            "visit_date": str(r.visit_date),
            "reason": r.reason,
        }
        for r in records
    ]

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    s3_key = f"intake/{timestamp}.csv"

    # Save locally to uploads/
    save_csv_locally(rows, UPLOADS_DIR)

    # Upload to LocalStack S3
    try:
        upload_csv_to_s3(rows, s3_key)
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"S3 upload error: {str(e)}")

    # Dispatch Celery task
    try:
        from worker.tasks import process_intake
        task = process_intake.delay(s3_key)
        logger.info(f"Celery task dispatched: {task.id} for key {s3_key}")
    except Exception as e:
        logger.error(f"Failed to dispatch Celery task: {e}")
        raise HTTPException(status_code=500, detail=f"Task dispatch error: {str(e)}")

    return IngestResponse(
        message="Ingestion accepted and task queued for processing.",
        workflow_id=task.id,
        s3_key=s3_key,
        record_count=len(records),
    )
