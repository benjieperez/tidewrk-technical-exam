import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.schemas import PatientOut, PaginatedPatients
from app.services.patient_service import get_patients_paginated, get_patient_by_id

router = APIRouter()


@router.get("/patients", response_model=PaginatedPatients)
async def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    mrn: Optional[str] = Query(None, description="Filter by MRN (partial match)"),
    first_name: Optional[str] = Query(None, description="Filter by first name (partial match)"),
    last_name: Optional[str] = Query(None, description="Filter by last name (partial match)"),
    db: AsyncSession = Depends(get_db),
):
    total, patients = await get_patients_paginated(
        session=db,
        page=page,
        page_size=page_size,
        mrn=mrn,
        first_name=first_name,
        last_name=last_name,
    )
    pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedPatients(
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        results=[PatientOut.model_validate(p) for p in patients],
    )


@router.get("/patients/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    patient = await get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    return PatientOut.model_validate(patient)
