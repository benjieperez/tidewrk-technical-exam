"""
Cross-platform health-check waiter for make start.
Usage:
    python scripts/wait_for_services.py redis
    python scripts/wait_for_services.py localstack
    python scripts/wait_for_services.py bucket
"""
import sys
import time
import socket
import urllib.request
import urllib.error
import json

TIMEOUT = 120  # seconds before giving up


def wait_for_redis():
    print("Waiting for Redis", end="", flush=True)
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        try:
            with socket.create_connection(("localhost", 6379), timeout=2):
                print(" Ready.", flush=True)
                return
        except OSError:
            print(".", end="", flush=True)
            time.sleep(2)
    print("\nERROR: Redis did not become ready in time.", flush=True)
    sys.exit(1)

def wait_for_localstack():
    print("Waiting for LocalStack S3", end="", flush=True)
    url = "http://localhost:4566/_localstack/health"
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                data = json.loads(resp.read())
                services = data.get("services", {})
                if services.get("s3") in ["running", "available"]:
                    print(" Ready.", flush=True)
                    return
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(2)
    print("\nERROR: LocalStack S3 did not become ready in time.", flush=True)
    sys.exit(1)

def create_bucket():
    bucket = "patient-intake"
    print(f"Creating S3 bucket '{bucket}'...", flush=True)
    url = f"http://localhost:4566/{bucket}"
    req = urllib.request.Request(url, method="PUT")
    req.add_header("Host", f"{bucket}.localhost:4566")
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"Bucket '{bucket}' created.", flush=True)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "BucketAlreadyOwnedByYou" in body or "BucketAlreadyExists" in body:
            print(f"Bucket '{bucket}' already exists - OK.", flush=True)
        else:
            print(f"Warning: unexpected response {e.code}: {body}", flush=True)
    except Exception as e:
        print(f"Warning: could not create bucket: {e}", flush=True)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else ""
    if target == "redis":
        wait_for_redis()
    elif target == "localstack":
        wait_for_localstack()
    elif target == "bucket":
        create_bucket()
    else:
        print(f"Unknown target: {target}")
        sys.exit(1)
