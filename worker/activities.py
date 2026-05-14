import logging
import os
from datetime import date

from temporalio import activity
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

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


@activity.defn(name="fetch_csv_from_s3")
async def fetch_csv_from_s3(s3_key: str) -> list[dict]:
    """Activity: Download and parse the CSV from S3."""
    logger.info(f"Fetching CSV from S3 key: {s3_key}")
    rows = download_csv_from_s3(s3_key)
    logger.info(f"Fetched {len(rows)} rows from S3")
    return rows


@activity.defn(name="process_patient_rows")
async def process_patient_rows(rows: list[dict]) -> dict:
    """
    Activity: Upsert patients, persons, and insert visits.

    For each row:
    - If MRN exists: update person fields, insert new visit
    - If MRN is new: create patient + person, insert visit

    Returns summary counts.
    """
    engine = get_engine()
    created_patients = 0
    updated_patients = 0
    inserted_visits = 0
    skipped_visits = 0

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
                session.flush()  # get patient.id

                person = Person(
                    id=patient.id,
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                )
                session.add(person)
                created_patients += 1
                logger.info(f"Created new patient MRN={mrn} id={patient.id}")
            else:
                # Update person details if changed
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

            # Insert visit (skip if visit_account_number already exists — idempotency)
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
                logger.info(f"Inserted visit {visit_account_number} for patient id={patient.id}")
            else:
                skipped_visits += 1
                logger.info(f"Skipped duplicate visit {visit_account_number}")

        session.commit()

    summary = {
        "created_patients": created_patients,
        "updated_patients": updated_patients,
        "inserted_visits": inserted_visits,
        "skipped_visits": skipped_visits,
        "total_rows": len(rows),
    }
    logger.info(f"Processing complete: {summary}")
    return summary


def _parse_date(value: str) -> date:
    """Parse ISO date string to date object."""
    return date.fromisoformat(value.strip())
