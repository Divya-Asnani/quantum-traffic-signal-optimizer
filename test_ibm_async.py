from src.ibm_quantum_optimizer import (
    submit_qaoa_job_ibm,
    get_qaoa_job_status,
    retrieve_qaoa_job_result,
)


traffic_demand = {
    "North": 70.75,
    "East": 30.17,
    "South": 28.64,
    "West": 20.61,
}


print("=" * 60)
print("IBM QUANTUM ASYNC TEST")
print("=" * 60)


# ============================================================
# STEP 1: SUBMIT JOB
# ============================================================

print("\nSubmitting job to IBM Quantum...")

job_id, submission_metadata = submit_qaoa_job_ibm(
    traffic_demand,
    shots=512,
    reps=1,
)


print("\n" + "=" * 60)
print("JOB SUBMITTED SUCCESSFULLY")
print("=" * 60)

print(f"Job ID: {job_id}")
print(f"Backend: {submission_metadata['backend']}")
print(f"Shots: {submission_metadata['shots']}")
print(
    f"Submission pipeline: "
    f"{submission_metadata['submission_pipeline_seconds']} sec"
)


# ============================================================
# STEP 2: CHECK STATUS
# ============================================================

print("\nChecking IBM job status...")

status = get_qaoa_job_status(job_id)

print(f"Job status: {status}")


print("\n" + "=" * 60)
print("ASYNC TEST COMPLETE")
print("=" * 60)

print("\nIMPORTANT:")
print("The job has been submitted.")
print(f"Save this Job ID: {job_id}")
print("We will retrieve the result separately.")