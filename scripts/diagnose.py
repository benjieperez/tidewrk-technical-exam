"""
Run this on the host to diagnose Docker startup failures.
Usage: python scripts/diagnose.py
"""
import subprocess
import sys

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return r.stdout.strip() + r.stderr.strip()

checks = [
    ("Docker version",          "docker --version"),
    ("Docker running",          "docker info --format \"{{.ServerVersion}}\""),
    ("Existing containers",     "docker ps -a --format \"table {{.Names}}\\t{{.Status}}\\t{{.Ports}}\""),
    ("Port 5432 in use",        "netstat -ano | findstr :5432"),
    ("Port 6379 in use",        "netstat -ano | findstr :6379"),
    ("Port 4566 in use",        "netstat -ano | findstr :4566"),
    ("Port 8000 in use",        "netstat -ano | findstr :8000"),
    ("Postgres logs",           "docker logs healthcare_postgres 2>&1"),
    ("LocalStack logs",         "docker logs healthcare_localstack 2>&1"),
    ("Redis logs",              "docker logs healthcare_redis 2>&1"),
    ("Disk space",              "docker system df"),
]

for label, cmd in checks:
    result = run(cmd)
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(result if result else "(no output)")
