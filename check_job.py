import os
from pathlib import Path
from dotenv import load_dotenv

from qiskit_ibm_runtime import QiskitRuntimeService

# ============================================================
# LOAD ENVIRONMENT
# ============================================================

project_root = Path(__file__).resolve().parent
env_path = project_root / "app" / ".env"

load_dotenv(env_path)

token = os.getenv("IBM_QUANTUM_TOKEN")
instance = os.getenv("IBM_QUANTUM_INSTANCE")

print("=" * 60)
print("IBM QUANTUM JOB STATUS CHECK")
print("=" * 60)

print("\nEnvironment variables found:")
print(f"IBM_QUANTUM_TOKEN: {'YES' if token else 'NO'}")
print(f"IBM_QUANTUM_INSTANCE: {'YES' if instance else 'NO'}")

if not token or not instance:
    print("\nERROR: IBM Quantum credentials are missing.")
    raise SystemExit(1)

# ============================================================
# CONNECT TO IBM QUANTUM
# ============================================================

print("\nConnecting to IBM Quantum...")

service = QiskitRuntimeService(
    channel="ibm_quantum_platform",
    token=token,
    instance=instance
)

print("Connected successfully.")

# ============================================================
# EXISTING JOB
# ============================================================

job_id = "dactmie42tqs73aslfng"

print("\nJob ID:")
print(job_id)

print("\nChecking job status...")

job = service.job(job_id)

print(f"Status: {job.status()}")

# ============================================================
# RESULT
# ============================================================

if str(job.status()) == "DONE":

    print("\nJob completed successfully.")

    result = job.result()

    print("\nRaw IBM Quantum result:")
    print(result)

else:
    print("\nJob is not completed yet.")
    print("Run this script again later to check the status.")

print("\n" + "=" * 60)