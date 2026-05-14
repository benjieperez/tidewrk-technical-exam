.PHONY: build up down logs start create-bucket wait-localstack wait-redis help \
        test-ingest test-patients list-s3 check-patients check-visits

# Config
COMPOSE        := docker-compose
BUCKET         := patient-intake
PYTHON         := python


## Build all Docker images
build:
	$(COMPOSE) build

## Start all services (without bootstrapping)
up:
	$(COMPOSE) up -d

## Stop and remove all containers + volumes
down:
	$(COMPOSE) down -v

## Tail logs from all services
logs:
	$(COMPOSE) logs -f

## Full startup: build → up → wait → create S3 bucket
start: build up wait-redis wait-localstack create-bucket
	@echo.
	@echo Healthcare Pipeline is READY
	@echo
	@echo   API Docs:   http://localhost:8000/docs
	@echo   Flower UI:  http://localhost:5555
	@echo   LocalStack: http://localhost:4566/_localstack/health


restart: down start wait-redis wait-localstack create-bucket

# ── Bootstrap helpers ─────────────────────────────────────────────────────────

## Wait for Redis to be healthy
wait-redis:
	$(PYTHON) scripts/wait_for_services.py redis

## Wait for LocalStack S3 to be healthy
wait-localstack:
	$(PYTHON) scripts/wait_for_services.py localstack

## Create the S3 bucket in LocalStack
create-bucket:
	$(PYTHON) scripts/wait_for_services.py bucket

# ── Verification helpers ──────────────────────────────────────────────────────

## List files in the S3 bucket
list-s3:
	$(COMPOSE) exec localstack awslocal s3 ls s3://$(BUCKET)/ --recursive

## Query patients + persons in PostgreSQL
check-patients:
	$(COMPOSE) exec postgres psql -U postgres -d healthcare -c "SELECT p.id, p.mrn, p.created_at, pe.first_name, pe.last_name, pe.birth_date FROM patients p JOIN persons pe ON p.id = pe.id ORDER BY p.id;"

## Query visits in PostgreSQL
check-visits:
	$(COMPOSE) exec postgres psql -U postgres -d healthcare -c "SELECT v.id, v.visit_account_number, v.visit_date, v.reason, v.patient_id FROM visits v ORDER BY v.patient_id, v.visit_date;"

## Send a sample POST /ingest request
test-ingest:
	$(PYTHON) -c "import urllib.request, json; req=urllib.request.Request('http://localhost:8000/ingest', data=json.dumps([{'mrn':'MRN-1001','first_name':'John','last_name':'Doe','birth_date':'1990-02-14','visit_account_number':'VST-9001','visit_date':'2024-11-01','reason':'Annual Checkup'},{'mrn':'MRN-1002','first_name':'Jane','last_name':'Smith','birth_date':'1985-07-22','visit_account_number':'VST-9002','visit_date':'2024-11-05','reason':'Follow-up'},{'mrn':'MRN-1001','first_name':'John','last_name':'Doe','birth_date':'1990-02-14','visit_account_number':'VST-9003','visit_date':'2024-12-01','reason':'Lab Results Review'}]).encode(), headers={'Content-Type':'application/json'}, method='POST'); print(json.dumps(json.loads(urllib.request.urlopen(req).read()), indent=2))"

## GET /patients
test-patients:
	$(PYTHON) -c "import urllib.request, json; print(json.dumps(json.loads(urllib.request.urlopen('http://localhost:8000/patients').read()), indent=2))"

## Show available make targets
help:
	@echo Available targets: build, up, down, logs, start, create-bucket, wait-redis, wait-localstack, list-s3, check-patients, check-visits, test-ingest, test-patients
