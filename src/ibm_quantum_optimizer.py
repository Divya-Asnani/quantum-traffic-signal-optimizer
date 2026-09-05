import os
import time
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from src.quantum_optimizer import (
    build_qubo,
    decode_bitstring,
    is_valid_timing
)

from src.evaluation import calculate_objective


# ============================================================
# PROJECT / ENVIRONMENT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / "app" / ".env"

load_dotenv(ENV_FILE)

IBM_TOKEN = os.getenv("IBM_QUANTUM_TOKEN")
IBM_INSTANCE = os.getenv("IBM_QUANTUM_INSTANCE", "")

PREFERRED_BACKEND = "ibm_marrakesh"


# ============================================================
# IBM QUANTUM SERVICE
# ============================================================

@lru_cache(maxsize=1)
def get_ibm_service():

    if not IBM_TOKEN:
        raise ValueError(
            f"IBM_QUANTUM_TOKEN was not found.\n"
            f"Expected .env file at: {ENV_FILE}"
        )

    print("\nConnecting to IBM Quantum...")

    if IBM_INSTANCE:

        service = QiskitRuntimeService(
            channel="ibm_quantum_platform",
            token=IBM_TOKEN,
            instance=IBM_INSTANCE
        )

    else:

        service = QiskitRuntimeService(
            channel="ibm_quantum_platform",
            token=IBM_TOKEN
        )

    print("IBM Quantum service connected.")

    return service


# ============================================================
# IBM QUANTUM BACKEND
# ============================================================

@lru_cache(maxsize=1)
def get_cached_ibm_backend():

    service = get_ibm_service()

    print(
        f"\nSelecting IBM Quantum backend: "
        f"{PREFERRED_BACKEND}"
    )

    backend = service.backend(PREFERRED_BACKEND)

    status = backend.status()

    if not status.operational:

        raise RuntimeError(
            f"IBM backend '{PREFERRED_BACKEND}' "
            f"is currently not operational.\n"
            f"Backend status: {status.status_msg}"
        )

    if backend.num_qubits < 8:

        raise RuntimeError(
            f"IBM backend '{PREFERRED_BACKEND}' "
            f"does not have enough qubits."
        )

    print(
        f"Using backend: {backend.name} "
        f"({backend.num_qubits} qubits)"
    )

    return backend


def get_ibm_backend(service=None):

    """
    Return the cached IBM backend.

    The service parameter is kept for compatibility
    with the existing project code.
    """

    return get_cached_ibm_backend()


# ============================================================
# BUILD QAOA CIRCUIT
# ============================================================

def build_qaoa_circuit(Q, offset, reps=1):

    num_qubits = Q.shape[0]

    if num_qubits != 8:

        raise ValueError(
            f"Expected 8 qubits for traffic optimization, "
            f"received {num_qubits}"
        )

    circuit = QuantumCircuit(num_qubits)

    # --------------------------------------------------------
    # Initial |+> state
    # --------------------------------------------------------

    for q in range(num_qubits):
        circuit.h(q)

    # --------------------------------------------------------
    # Hardware proof-of-concept parameters
    # --------------------------------------------------------

    gamma = 0.2
    beta = 0.3

    # --------------------------------------------------------
    # QAOA layers
    # --------------------------------------------------------

    for _ in range(reps):

        # Cost Hamiltonian - diagonal terms

        for i in range(num_qubits):

            if Q[i, i] != 0:

                circuit.rz(
                    -2 * gamma * float(Q[i, i]),
                    i
                )

        # Cost Hamiltonian - interaction terms

        for i in range(num_qubits):

            for j in range(i + 1, num_qubits):

                if Q[i, j] != 0:

                    circuit.cx(i, j)

                    circuit.rz(
                        -2 * gamma * float(Q[i, j]),
                        j
                    )

                    circuit.cx(i, j)

        # Mixer Hamiltonian

        for q in range(num_qubits):

            circuit.rx(
                2 * beta,
                q
            )

    # --------------------------------------------------------
    # Measurement
    # --------------------------------------------------------

    circuit.measure_all()

    return circuit


# ============================================================
# EXTRACT BEST VALID IBM SOLUTION
# ============================================================

def extract_best_bitstring(result, traffic_demand):

    pub_result = result[0]

    counts = pub_result.data.meas.get_counts()

    if not counts:

        raise ValueError(
            "IBM Quantum returned no measurement results."
        )

    valid_solutions = []

    for raw_bitstring, count in counts.items():

        bitstring = raw_bitstring.replace(" ", "")

        if len(bitstring) != 8:
            continue

        # ----------------------------------------------------
        # Convert IBM/Qiskit bit ordering
        # to project ordering
        # ----------------------------------------------------

        decoded_bitstring = tuple(
            int(bit)
            for bit in bitstring[::-1]
        )

        # ----------------------------------------------------
        # Decode traffic signal timing
        # ----------------------------------------------------

        timing = decode_bitstring(
            decoded_bitstring
        )

        # ----------------------------------------------------
        # Check 60-second cycle
        # ----------------------------------------------------

        if not is_valid_timing(timing):
            continue

        # ----------------------------------------------------
        # Calculate traffic objective
        # ----------------------------------------------------

        objective = calculate_objective(
            traffic_demand,
            timing
        )

        valid_solutions.append(
            {
                "raw_bitstring": bitstring,
                "decoded_bitstring": decoded_bitstring,
                "timing": timing,
                "objective": objective,
                "count": count
            }
        )

    # --------------------------------------------------------
    # No valid solution
    # --------------------------------------------------------

    if not valid_solutions:

        raise ValueError(
            "IBM Quantum returned no valid "
            "60-second traffic signal timing solutions."
        )

    # --------------------------------------------------------
    # Select lowest objective
    # --------------------------------------------------------

    best_solution = min(
        valid_solutions,
        key=lambda x: x["objective"]
    )

    print(
        f"\nValid solutions found: "
        f"{len(valid_solutions)}"
    )

    print(
        "\nBest valid IBM solution:"
    )

    print(
        f"Bitstring: "
        f"{best_solution['raw_bitstring']}"
    )

    print(
        f"Timing: "
        f"{best_solution['timing']}"
    )

    print(
        f"Objective: "
        f"{best_solution['objective']:.2f}"
    )

    print(
        f"Measurement count: "
        f"{best_solution['count']}"
    )

    return best_solution


# ============================================================
# IBM QUANTUM QAOA SOLVER
# ============================================================

def solve_with_qaoa_ibm(
    traffic_demand,
    shots=512,
    reps=1
):

    total_start_time = time.time()

    print("=" * 60)
    print("IBM QUANTUM QAOA EXECUTION")
    print("=" * 60)

    print(
        f"Traffic Demand: "
        f"{traffic_demand}"
    )


    # ========================================================
    # STEP 1: BUILD QUBO
    # ========================================================

    step_start = time.time()

    Q, offset = build_qubo(
        traffic_demand
    )

    qubo_time = time.time() - step_start

    print(
        "\nQUBO created successfully."
    )

    print(
        f"Number of qubits: "
        f"{Q.shape[0]}"
    )

    print(
        f"QUBO construction time: "
        f"{qubo_time:.4f} seconds"
    )

    # ========================================================
    # STEP 2: GET CACHED IBM SERVICE
    # ========================================================

    step_start = time.time()

    service = get_ibm_service()

    connection_time = time.time() - step_start

    print(
        f"IBM connection/access time: "
        f"{connection_time:.4f} seconds"
    )

    # ========================================================
    # STEP 3: GET CACHED BACKEND
    # ========================================================

    step_start = time.time()

    backend = get_cached_ibm_backend()

    backend_selection_time = time.time() - step_start

    print(
        f"Backend access time: "
        f"{backend_selection_time:.4f} seconds"
    )

    print(
        f"\nIBM Backend: "
        f"{backend.name}"
    )

    print(
        f"Backend Qubits: "
        f"{backend.num_qubits}"
    )

    # ========================================================
    # STEP 4: BUILD QAOA CIRCUIT
    # ========================================================

    step_start = time.time()

    circuit = build_qaoa_circuit(
        Q,
        offset,
        reps=reps
    )

    circuit_time = time.time() - step_start

    print(
        "\nQAOA circuit created."
    )

    print(
        f"Logical Qubits: "
        f"{circuit.num_qubits}"
    )

    print(
        f"Original circuit depth: "
        f"{circuit.depth()}"
    )

    print(
        f"Circuit construction time: "
        f"{circuit_time:.4f} seconds"
    )

    # ========================================================
    # STEP 5: TRANSPILE
    # ========================================================

    step_start = time.time()

    print(
        "\nTranspiling circuit for IBM hardware..."
    )

    pass_manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=1
    )

    isa_circuit = pass_manager.run(
        circuit
    )

    transpilation_time = time.time() - step_start

    print(
        "Transpilation complete."
    )

    print(
        f"Transpiled depth: "
        f"{isa_circuit.depth()}"
    )

    print(
        f"Transpiled gates: "
        f"{isa_circuit.size()}"
    )

    print(
        f"Transpilation time: "
        f"{transpilation_time:.4f} seconds"
    )

    # ========================================================
    # STEP 6: SUBMIT TO IBM HARDWARE
    # ========================================================

    step_start = time.time()

    print(
        "\nSubmitting job to IBM Quantum..."
    )

    sampler = SamplerV2(
        mode=backend
    )

    job = sampler.run(
        [isa_circuit],
        shots=shots
    )

    submission_time = time.time() - step_start

    job_id = job.job_id()

    print(
        "\nJOB SUBMITTED"
    )

    print(
        f"Job ID: "
        f"{job_id}"
    )

    print(
        f"Job submission time: "
        f"{submission_time:.4f} seconds"
    )

    # ========================================================
    # STEP 7: WAIT FOR RESULT
    # ========================================================

    print(
        "\nWaiting for IBM Quantum result..."
    )

    step_start = time.time()

    result = job.result()

    result_wait_time = time.time() - step_start

    print(
        "IBM Quantum job completed."
    )

    print(
        f"IBM result wait time: "
        f"{result_wait_time:.4f} seconds"
    )

    # ========================================================
    # STEP 8: EXTRACT BEST SOLUTION
    # ========================================================

    step_start = time.time()

    best_solution = extract_best_bitstring(
        result,
        traffic_demand
    )

    measurement_processing_time = (
        time.time() - step_start
    )

    bitstring = best_solution[
        "raw_bitstring"
    ]

    decoded_bitstring = best_solution[
        "decoded_bitstring"
    ]

    counts = result[
        0
    ].data.meas.get_counts()

    print(
        f"Measurement processing time: "
        f"{measurement_processing_time:.4f} seconds"
    )

    # ========================================================
    # STEP 9: DECODE TIMING
    # ========================================================

    step_start = time.time()

    timing = decode_bitstring(
        decoded_bitstring
    )

    valid_cycle = is_valid_timing(
        timing
    )

    objective = calculate_objective(
        traffic_demand,
        timing
    )

    evaluation_time = time.time() - step_start

    # ========================================================
    # STEP 10: TOTAL RUNTIME
    # ========================================================

    total_runtime = (
        time.time()
        - total_start_time
    )

    # ========================================================
    # STEP 11: METADATA
    # ========================================================

    metadata = {

        "selected_bitstring":
            decoded_bitstring,

        "raw_ibm_bitstring":
            bitstring,

        "decoded_timing":
            timing,

        "traffic_objective":
            objective,

        "num_qubits":
            8,

        "physical_backend_qubits":
            backend.num_qubits,

        "qaoa_reps":
            reps,

        "shots":
            shots,

        "backend":
            backend.name,

        "execution":
            "IBM Quantum Hardware",

        "transpiled_depth":
            isa_circuit.depth(),

        "transpiled_gates":
            isa_circuit.size(),

        "job_id":
            job_id,

        "is_valid_cycle_time":
            valid_cycle,

        "qubo_time_seconds":
            round(qubo_time, 4),

        "connection_time_seconds":
            round(connection_time, 4),

        "backend_selection_time_seconds":
            round(backend_selection_time, 4),

        "circuit_construction_time_seconds":
            round(circuit_time, 4),

        "transpilation_time_seconds":
            round(transpilation_time, 4),

        "job_submission_time_seconds":
            round(submission_time, 4),

        "result_wait_time_seconds":
            round(result_wait_time, 4),

        "measurement_processing_time_seconds":
            round(
                measurement_processing_time,
                4
            ),

        "evaluation_time_seconds":
            round(evaluation_time, 4),

        "runtime_seconds":
            round(total_runtime, 2),

        "measurement_counts":
            counts
    }

    # ========================================================
    # DISPLAY RESULT
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "--- IBM QUANTUM RESULT ---"
    )

    print(
        f"Raw bitstring: "
        f"{bitstring}"
    )

    print(
        f"Decoded bitstring: "
        f"{decoded_bitstring}"
    )

    print(
        f"Signal timing: "
        f"{timing}"
    )

    print(
        f"Total cycle: "
        f"{sum(timing.values())} seconds"
    )

    print(
        f"Objective: "
        f"{objective:.2f}"
    )

    print(
        f"Valid 60-second cycle: "
        f"{valid_cycle}"
    )

    print(
        f"Backend: "
        f"{backend.name}"
    )

    print(
        f"Shots: "
        f"{shots}"
    )

    print(
        f"Total Runtime: "
        f"{total_runtime:.2f} seconds"
    )

    # ========================================================
    # RUNTIME BREAKDOWN
    # ========================================================

    print(
        "\n--- RUNTIME BREAKDOWN ---"
    )

    print(
        f"QUBO construction: "
        f"{qubo_time:.4f} sec"
    )

    print(
        f"IBM connection/access: "
        f"{connection_time:.4f} sec"
    )

    print(
        f"Backend access: "
        f"{backend_selection_time:.4f} sec"
    )

    print(
        f"Circuit construction: "
        f"{circuit_time:.4f} sec"
    )

    print(
        f"Transpilation: "
        f"{transpilation_time:.4f} sec"
    )

    print(
        f"Job submission: "
        f"{submission_time:.4f} sec"
    )

    print(
        f"IBM result wait: "
        f"{result_wait_time:.4f} sec"
    )

    print(
        f"Measurement processing: "
        f"{measurement_processing_time:.4f} sec"
    )

    print(
        f"Evaluation: "
        f"{evaluation_time:.4f} sec"
    )

    print(
        f"\nTOTAL: "
        f"{total_runtime:.2f} sec"
    )

    print(
        "=" * 60
    )

    return timing, metadata

# ============================================================
# ASYNCHRONOUS IBM QUANTUM EXECUTION
# ============================================================

def submit_qaoa_job_ibm(
    traffic_demand,
    shots=512,
    reps=1
):
    """
    Submit a QAOA job to real IBM Quantum hardware
    without waiting for the result.

    Returns:
        job_id
        metadata
    """

    print("=" * 60)
    print("IBM QUANTUM QAOA JOB SUBMISSION")
    print("=" * 60)

    start_total = time.perf_counter()

    # --------------------------------------------------------
    # 1. Build QUBO
    # --------------------------------------------------------

    qubo_start = time.perf_counter()

    Q, offset = build_qubo(
    traffic_demand
)

    qubo_time = time.perf_counter() - qubo_start

    print(f"QUBO created successfully.")
    print(f"Number of qubits: {Q.shape[0]}")
    print(f"QUBO construction time: {qubo_time:.4f} seconds")

    # --------------------------------------------------------
    # 2. IBM Quantum connection
    # --------------------------------------------------------

    connection_start = time.perf_counter()

    service = get_ibm_service()

    connection_time = time.perf_counter() - connection_start

    print("\nIBM Quantum service connected.")
    print(f"IBM connection/access time: {connection_time:.4f} seconds")

    # --------------------------------------------------------
    # 3. Backend
    # --------------------------------------------------------

    backend_start = time.perf_counter()

    backend = get_cached_ibm_backend()

    backend_time = time.perf_counter() - backend_start

    print(f"\nUsing backend: {backend.name}")
    print(f"Backend Qubits: {backend.num_qubits}")
    print(f"Backend access time: {backend_time:.4f} seconds")

    # --------------------------------------------------------
    # 4. Build QAOA circuit
    # --------------------------------------------------------

    circuit_start = time.perf_counter()

    circuit = build_qaoa_circuit(
    Q,
    offset,
    reps=reps

)

    circuit_time = time.perf_counter() - circuit_start

    print("\nQAOA circuit created.")
    print(f"Logical Qubits: {circuit.num_qubits}")
    print(f"Original circuit depth: {circuit.depth()}")
    print(f"Circuit construction time: {circuit_time:.4f} seconds")

    # --------------------------------------------------------
    # 5. Transpile
    # --------------------------------------------------------

    transpile_start = time.perf_counter()

    pm = generate_preset_pass_manager(
        backend=backend,
        optimization_level=1
    )

    transpiled_circuit = pm.run(circuit)

    transpile_time = time.perf_counter() - transpile_start

    print("\nTranspiling circuit for IBM hardware...")
    print("Transpilation complete.")
    print(f"Transpiled depth: {transpiled_circuit.depth()}")
    print(f"Transpiled gates: {len(transpiled_circuit.data)}")
    print(f"Transpilation time: {transpile_time:.4f} seconds")

    # --------------------------------------------------------
    # 6. Submit job WITHOUT waiting
    # --------------------------------------------------------

    print("\nSubmitting job to IBM Quantum...")

    submission_start = time.perf_counter()

    sampler = SamplerV2(mode=backend)

    job = sampler.run(
        [transpiled_circuit],
        shots=shots
    )

    submission_time = time.perf_counter() - submission_start
    total_submit_time = time.perf_counter() - start_total

    job_id = job.job_id()

    print("\nJOB SUBMITTED")
    print(f"Job ID: {job_id}")
    print(f"Job submission time: {submission_time:.4f} seconds")
    print(f"Total submission pipeline time: {total_submit_time:.4f} seconds")

    metadata = {
        "job_id": job_id,
        "backend": backend.name,
        "shots": shots,
        "qaoa_reps": reps,
        "num_qubits": circuit.num_qubits,
        "physical_backend_qubits": backend.num_qubits,
        "original_depth": circuit.depth(),
        "transpiled_depth": transpiled_circuit.depth(),
        "transpiled_gates": len(transpiled_circuit.data),
        "qubo_time_seconds": round(qubo_time, 4),
        "connection_time_seconds": round(connection_time, 4),
        "backend_selection_time_seconds": round(backend_time, 4),
        "circuit_construction_time_seconds": round(circuit_time, 4),
        "transpilation_time_seconds": round(transpile_time, 4),
        "job_submission_time_seconds": round(submission_time, 4),
        "submission_pipeline_seconds": round(total_submit_time, 4),
        "traffic_demand": traffic_demand,
        "execution": "IBM Quantum Hardware",
    }

    return job_id, metadata


def get_qaoa_job_status(job_id):
    """
    Check the current status of an IBM Quantum job.

    Does NOT wait for completion.
    """

    service = get_ibm_service()

    job = service.job(job_id)

    status = job.status()

    return str(status)


def retrieve_qaoa_job_result(
    job_id,
    traffic_demand
):
    """
    Retrieve a completed IBM Quantum QAOA job.

    This function should be called only after the job
    status becomes DONE.
    """

    start_time = time.perf_counter()

    service = get_ibm_service()

    job = service.job(job_id)

    print("=" * 60)
    print("RETRIEVING IBM QUANTUM RESULT")
    print("=" * 60)

    print(f"Job ID: {job_id}")
    print(f"Status: {job.status()}")

    result = job.result()

    result_wait_time = time.perf_counter() - start_time

    best_solution = extract_best_bitstring(
        result,
        traffic_demand
    )

    if best_solution is None:
        raise RuntimeError(
            "IBM Quantum completed, but no valid 60-second "
            "traffic timing solution was found."
        )

    timing = best_solution["timing"]

    metadata = {
        "job_id": job_id,
        "backend": job.backend().name,
        "raw_ibm_bitstring": best_solution["raw_bitstring"],
        "selected_bitstring": best_solution["decoded_bitstring"],
        "decoded_timing": timing,
        "traffic_objective": best_solution["objective"],
        "measurement_count": best_solution["count"],
        "is_valid_cycle_time": is_valid_timing(timing),
        "result_wait_time_seconds": round(
            result_wait_time,
            4
        ),
        "execution": "IBM Quantum Hardware",
    }

    return timing, metadata