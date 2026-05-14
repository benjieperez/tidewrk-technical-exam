import os
import io
import csv
import logging
from datetime import datetime

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "http://localhost:4566")
S3_BUCKET = os.getenv("S3_BUCKET", "patient-intake")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

CSV_FIELDNAMES = [
    "mrn",
    "first_name",
    "last_name",
    "birth_date",
    "visit_account_number",
    "visit_date",
    "reason",
]


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
        config=Config(signature_version="s3v4"),
    )


def records_to_csv_bytes(records: list[dict]) -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for record in records:
        row = {k: str(record.get(k, "")) for k in CSV_FIELDNAMES}
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def save_csv_locally(records: list[dict], uploads_dir: str) -> str:
    """Save CSV to local uploads/ directory and return the file path."""
    os.makedirs(uploads_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"intake_{timestamp}.csv"
    filepath = os.path.join(uploads_dir, filename)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()
        for record in records:
            row = {k: str(record.get(k, "")) for k in CSV_FIELDNAMES}
            writer.writerow(row)

    logger.info(f"CSV saved locally: {filepath}")
    return filepath


def upload_csv_to_s3(records: list[dict], s3_key: str) -> str:
    """Upload CSV to S3 and return the key."""
    client = get_s3_client()
    csv_bytes = records_to_csv_bytes(records)

    client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=csv_bytes,
        ContentType="text/csv",
    )
    logger.info(f"CSV uploaded to s3://{S3_BUCKET}/{s3_key}")
    return s3_key


def download_csv_from_s3(s3_key: str) -> list[dict]:
    """Download and parse CSV from S3, returning list of row dicts."""
    client = get_s3_client()
    response = client.get_object(Bucket=S3_BUCKET, Key=s3_key)
    body = response["Body"].read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(body))
    rows = list(reader)
    logger.info(f"Downloaded {len(rows)} rows from s3://{S3_BUCKET}/{s3_key}")
    return rows


def ensure_bucket_exists():
    """Create S3 bucket if it doesn't exist."""
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=S3_BUCKET)
        logger.info(f"Bucket {S3_BUCKET} already exists")
    except client.exceptions.ClientError:
        client.create_bucket(Bucket=S3_BUCKET)
        logger.info(f"Created bucket {S3_BUCKET}")
