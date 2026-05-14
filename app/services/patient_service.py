import logging
from datetime import date

from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Patient, Person, Visit

logger = logging.getLogger(__name__)


async def get_patients_paginated(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    mrn: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> tuple[int, list[Patient]]:
    """Return (total_count, patients) with pagination and optional filters."""

    base_query = (
        select(Patient)
        .options(selectinload(Patient.person), selectinload(Patient.visits))
    )

    # Build join + filter conditions
    if first_name or last_name:
        base_query = base_query.join(Person, Patient.id == Person.id)

    filters = []
    if mrn:
        filters.append(Patient.mrn.ilike(f"%{mrn}%"))
    if first_name:
        filters.append(Person.first_name.ilike(f"%{first_name}%"))
    if last_name:
        filters.append(Person.last_name.ilike(f"%{last_name}%"))

    if filters:
        base_query = base_query.where(*filters)

    # Count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    patients_result = await session.execute(
        base_query.offset(offset).limit(page_size).order_by(Patient.id)
    )
    patients = patients_result.scalars().all()

    return total, list(patients)


async def get_patient_by_id(session: AsyncSession, patient_id: int) -> Patient | None:
    result = await session.execute(
        select(Patient)
        .options(selectinload(Patient.person), selectinload(Patient.visits))
        .where(Patient.id == patient_id)
    )
    return result.scalar_one_or_none()
