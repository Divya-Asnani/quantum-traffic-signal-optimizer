from src.ibm_quantum_optimizer import (
    solve_with_qaoa_ibm,
)


traffic_demand = {
    "North": 70.75,
    "East": 30.17,
    "South": 28.64,
    "West": 20.61,
}


print("=" * 60)
print("IBM TRAFFIC SIGNAL QAOA TEST")
print("=" * 60)

print("\nStarting IBM Quantum optimization...")

timing, metadata = solve_with_qaoa_ibm(
    traffic_demand,
    shots=512,
    reps=1
)


print("\n" + "=" * 60)
print("FINAL TIMING")
print("=" * 60)

print(timing)


print("\n" + "=" * 60)
print("IBM METADATA")
print("=" * 60)

for key, value in metadata.items():

    if key != "measurement_counts":

        print(f"{key}: {value}")


print("\n" + "=" * 60)
print("IBM JOB SUMMARY")
print("=" * 60)

print(f"Job ID: {metadata.get('job_id')}")
print(f"Backend: {metadata.get('backend')}")
print(f"Shots: {metadata.get('shots')}")
print(f"Raw bitstring: {metadata.get('raw_ibm_bitstring')}")
print(f"Decoded timing: {metadata.get('decoded_timing')}")
print(f"Objective: {metadata.get('traffic_objective')}")
print(f"Valid cycle: {metadata.get('is_valid_cycle_time')}")
print(f"Runtime: {metadata.get('runtime_seconds')} seconds")

print("\nIBM optimization completed successfully.")