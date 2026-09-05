from src.ibm_quantum_optimizer import (
    get_qaoa_job_status,
    retrieve_qaoa_job_result,
)


traffic_demand = {
    "North": 70.75,
    "East": 30.17,
    "South": 28.64,
    "West": 20.61,
}


JOB_ID = "dactmie42tqs73aslfng"


print("=" * 60)
print("IBM QUANTUM ASYNC RESULT RETRIEVAL")
print("=" * 60)


# ============================================================
# STEP 1: CHECK JOB STATUS
# ============================================================

status = get_qaoa_job_status(JOB_ID)

print(f"\nJob ID: {JOB_ID}")
print(f"Current status: {status}")


# ============================================================
# STEP 2: RETRIEVE RESULT ONLY IF COMPLETE
# ============================================================

if status.upper() == "DONE":

    print("\nIBM job is complete.")
    print("Retrieving result...")

    timing, metadata = retrieve_qaoa_job_result(
        JOB_ID,
        traffic_demand
    )

    print("\n" + "=" * 60)
    print("FINAL IBM QUANTUM RESULT")
    print("=" * 60)

    print(f"Timing: {timing}")
    print(f"Raw bitstring: {metadata['raw_ibm_bitstring']}")
    print(f"Objective: {metadata['traffic_objective']}")
    print(f"Valid cycle: {metadata['is_valid_cycle_time']}")
    print(f"Measurement count: {metadata['measurement_count']}")

else:

    print("\nJob is not finished yet.")
    print("Do NOT submit another job.")
    print("Run this same retrieval script again later.")