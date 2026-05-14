# Healthcare Data Ingestion Pipeline

## Prerequisites
- Docker & Docker Compose
- `make`
- AWS CLI (optional, for manual S3 verification)
---

## Setup Instructions
```bash
git clone https://github.com/benjieperez/tidewrk-technical-exam.git
cd tidewrk-technical-exam
cp .env.example .env
make start
```

## Makefile Usage
| Command              | Description                                  |
|---------------------|----------------------------------------------|
| `make restart`       | Restart all services                         |
| `make start`         | Full startup (build + up + bootstrap)        |
| `make build`         | Build all Docker images                      |
| `make up`            | Start all services                           |
| `make down`          | Stop and remove all containers + volumes     |
| `make logs`          | Tail logs from all services                  |
| `make create-bucket` | Create the S3 bucket in LocalStack          |
| `make test-ingest`   | Send a sample POST /ingest request           |
| `make test-patients` | Call GET /patients                           |
| `make list-s3`       | List files in the S3 bucket                  |
| `make check-patients`| Query patients + persons in PostgreSQL       |
| `make check-visits`  | Query visits in PostgreSQL                   |

---

## API Usage

### POST /ingest
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '[
    {
      "mrn": "MRN-1001",
      "first_name": "John",
      "last_name": "Doe",
      "birth_date": "1990-02-14",
      "visit_account_number": "VST-9001",
      "visit_date": "2024-11-01",
      "reason": "Annual Checkup"
    }
  ]'
```

**Response (202 Accepted):**
```json
{
  "message": "Ingestion accepted and task queued for processing.",
  "workflow_id": "<celery-task-uuid>",
  "s3_key": "intake/20241201_120000_000000.csv",
  "record_count": 1
}
```

### GET /patients

```bash
# All patients
curl http://localhost:8000/patients

# With filters
curl "http://localhost:8000/patients?mrn=MRN-1001&page=1&page_size=10"
curl "http://localhost:8000/patients?first_name=John&last_name=Doe"
```

### GET /patients/{id}

```bash
curl http://localhost:8000/patients/1
```
---


## S3 Verification

```bash
# List all uploaded CSVs
make list-s3

# Download and inspect
aws --endpoint-url=http://localhost:4566 --region us-east-1 \
    s3 cp s3://patient-intake/intake/<filename>.csv /tmp/check.csv && cat /tmp/check.csv
```

---

## Database Verification

```bash
# Query patients + persons in PostgreSQL
make check-patients

# Query visits in PostgreSQL
make check-visits
```

## Celery Worker

### Flower UI
Open http://localhost:5555 to see all task executions, states and worker health in real time.

