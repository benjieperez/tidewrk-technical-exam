import logging
import os
from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from worker.celery_app import celery_app
from app.models.models import Patient, Person, Visit
from app.services.s3_service import download_csv_from_s3

logger = logging.getLogger(__name__)

DATABASE_SYNC_URL = os.getenv(
    "DATABASE_SYNC_URL",
    "postgresql://postgres:postgres@postgres:5432/healthcare",
)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_SYNC_URL, echo=False, pool_pre_ping=True)
    return _engine


@celery_app.task(
    name="worker.tasks.process_intake",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def process_intake(self, s3_key: str) -> dict:
    """
    Celery task: Download CSV from S3, upsert patients/persons, insert visits.

    MRN deduplication rules:
    - New MRN     → create Patient + Person (same ID) + Visit
    - Existing MRN → update changed person fields + insert new Visit
    - Duplicate visit_account_number → skip (idempotency)
    """
    logger.info(f"[{self.request.id}] Starting intake for S3 key: {s3_key}")

    # Step 1: Fetch CSV from S3
    try:
        rows = download_csv_from_s3(s3_key)
    except Exception as exc:
        logger.error(f"[{self.request.id}] Failed to fetch CSV: {exc}")
        raise self.retry(exc=exc)

    logger.info(f"[{self.request.id}] Fetched {len(rows)} rows from S3")

    # Step 2: Process rows
    created_patients = 0
    updated_patients = 0
    inserted_visits = 0
    skipped_visits = 0

    try:
        engine = get_engine()
        with Session(engine) as session:
            for row in rows:
                mrn = row["mrn"].strip()
                first_name = row["first_name"].strip()
                last_name = row["last_name"].strip()
                birth_date = _parse_date(row["birth_date"])
                visit_account_number = row["visit_account_number"].strip()
                visit_date = _parse_date(row["visit_date"])
                reason = row["reason"].strip()

                # Resolve or create Patient
                patient = session.execute(
                    select(Patient).where(Patient.mrn == mrn)
                ).scalar_one_or_none()

                if patient is None:
                    patient = Patient(mrn=mrn)
                    session.add(patient)
                    session.flush()  # populate patient.id

                    person = Person(
                        id=patient.id,
                        first_name=first_name,
                        last_name=last_name,
                        birth_date=birth_date,
                    )
                    session.add(person)
                    created_patients += 1
                    logger.info(f"Created patient MRN={mrn} id={patient.id}")
                else:
                    # Update person fields if anything changed
                    person = session.get(Person, patient.id)
                    if person:
                        changed = False
                        if person.first_name != first_name:
                            person.first_name = first_name
                            changed = True
                        if person.last_name != last_name:
                            person.last_name = last_name
                            changed = True
                        if person.birth_date != birth_date:
                            person.birth_date = birth_date
                            changed = True
                        if changed:
                            updated_patients += 1
                            logger.info(f"Updated person for MRN={mrn} id={patient.id}")

                # Insert visit (idempotency: skip if already exists)
                existing_visit = session.execute(
                    select(Visit).where(Visit.visit_account_number == visit_account_number)
                ).scalar_one_or_none()

                if existing_visit is None:
                    visit = Visit(
                        visit_account_number=visit_account_number,
                        patient_id=patient.id,
                        visit_date=visit_date,
                        reason=reason,
                    )
                    session.add(visit)
                    inserted_visits += 1
                    logger.info(f"Inserted visit {visit_account_number} → patient {patient.id}")
                else:
                    skipped_visits += 1
                    logger.info(f"Skipped duplicate visit {visit_account_number}")

            session.commit()

    except Exception as exc:
        logger.error(f"[{self.request.id}] DB error: {exc}")
        raise self.retry(exc=exc)

    summary = {
        "task_id": self.request.id,
        "s3_key": s3_key,
        "total_rows": len(rows),
        "created_patients": created_patients,
        "updated_patients": updated_patients,
        "inserted_visits": inserted_visits,
        "skipped_visits": skipped_visits,
    }
    logger.info(f"[{self.request.id}] Complete: {summary}")
    return summary


def _parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())
