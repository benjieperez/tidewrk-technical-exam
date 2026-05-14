from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from worker.activities import fetch_csv_from_s3, process_patient_rows


@workflow.defn(name="PatientIntakeWorkflow")
class PatientIntakeWorkflow:
    """
    Orchestrates the patient intake pipeline:
    1. Fetch CSV from S3
    2. Process rows (upsert patients/persons, insert visits)
    """

    @workflow.run
    async def run(self, s3_key: str) -> dict:
        workflow.logger.info(f"PatientIntakeWorkflow started for key: {s3_key}")

        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=2),
            backoff_coefficient=2.0,
        )

        # Step 1: Fetch CSV from S3
        rows: list[dict] = await workflow.execute_activity(
            fetch_csv_from_s3,
            s3_key,
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        workflow.logger.info(f"Fetched {len(rows)} rows from S3")

        # Step 2: Process all rows in a single DB transaction activity
        result: dict = await workflow.execute_activity(
            process_patient_rows,
            rows,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
        )

        workflow.logger.info(f"Workflow complete: {result}")
        return result
