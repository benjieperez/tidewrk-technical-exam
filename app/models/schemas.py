from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Ingest ──────────────────────────────────────────────────────────────────

class VisitRecord(BaseModel):
    mrn: str
    first_name: str
    last_name: str
    birth_date: date
    visit_account_number: str
    visit_date: date
    reason: str


class IngestRequest(BaseModel):
    records: list[VisitRecord]

    @classmethod
    def from_list(cls, data: list[dict]) -> "IngestRequest":
        return cls(records=[VisitRecord(**item) for item in data])


class IngestResponse(BaseModel):
    message: str
    workflow_id: str
    s3_key: str
    record_count: int


# ── Patient responses ────────────────────────────────────────────────────────

class VisitOut(BaseModel):
    id: int
    visit_account_number: str
    visit_date: date
    reason: str

    model_config = {"from_attributes": True}


class PersonOut(BaseModel):
    first_name: str
    last_name: str
    birth_date: date

    model_config = {"from_attributes": True}


class PatientOut(BaseModel):
    id: int
    mrn: str
    created_at: datetime
    person: Optional[PersonOut] = None
    visits: list[VisitOut] = []

    model_config = {"from_attributes": True}


class PaginatedPatients(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    results: list[PatientOut]
