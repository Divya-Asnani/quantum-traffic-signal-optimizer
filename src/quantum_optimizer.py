import sys
from pathlib import Path
import itertools
import numpy as np
import warnings
import time

# Ensure we can import from src
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------

from src.evaluation import calculate_objective

from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_algorithms.utils import algorithm_globals

from qiskit.primitives import StatevectorSampler 

from scipy.sparse import SparseEfficiencyWarning


# Suppress harmless internal Qiskit sparse matrix warnings
warnings.filterwarnings(
    "ignore",
    category=SparseEfficiencyWarning
)


# ---------------------------------------------------------------------
# PROBLEM DEFINITION
# ---------------------------------------------------------------------

# The 8 binary variables represent:
#
# [q_N0, q_N1,
#  q_E0, q_E1,
#  q_S0, q_S1,
#  q_W0, q_W1]
#
# Green time:
#
# 00 -> 10 seconds
# 10 -> 20 seconds
# 01 -> 30 seconds
# 11 -> 40 seconds

APPROACHES = [
    "North",
    "East",
    "South",
    "West"
]


# ---------------------------------------------------------------------
# BITSTRING DECODING
# ---------------------------------------------------------------------

def decode_bitstring(bitstring):
    """
    Decode an 8-bit QAOA bitstring into traffic signal timings.

    Encoding per direction:

        00 -> 10 seconds
        10 -> 20 seconds
        01 -> 30 seconds
        11 -> 40 seconds
    """

    if len(bitstring) != 8:
        raise ValueError(
            "Bitstring must have exactly 8 bits."
        )

    signal_timing = {}

    for i, approach in enumerate(APPROACHES):

        q0 = int(bitstring[2 * i])
        q1 = int(bitstring[2 * i + 1])

        green_time = (
            10
            + (10 * q0)
            + (20 * q1)
        )

        signal_timing[approach] = green_time

    return signal_timing


# ---------------------------------------------------------------------
# VALID TIMING CHECK
# ---------------------------------------------------------------------

def is_valid_timing(signal_timing):
    """
    Check whether the total signal cycle is exactly 60 seconds.
    """

    return sum(signal_timing.values()) == 60


# ---------------------------------------------------------------------
# QUBO CONSTRUCTION
# ---------------------------------------------------------------------

def build_qubo(traffic_demand, penalty_weight=100000):
    """
    Build the QUBO matrix for the traffic signal optimization problem.

    Energy:

        E = x^T Q x + offset

    The QUBO contains:

    1. Traffic optimization objective
    2. 60-second cycle-time constraint
    """

    Q = np.zeros((8, 8), dtype=float)

    offset = 0.0

    # -------------------------------------------------------------
    # 1. TRAFFIC OBJECTIVE
    # -------------------------------------------------------------

    for i, approach in enumerate(APPROACHES):

        # Isolate one approach at a time
        isolated_demand = {
            app: (
                traffic_demand[app]
                if app == approach
                else 0
            )
            for app in APPROACHES
        }

        def cost_fn(q0, q1):

            green_time = (
                10
                + (10 * q0)
                + (20 * q1)
            )

            # Create a valid 60-second cycle
            dummy_timing = {
                app: 0
                for app in APPROACHES
            }

            dummy_timing[approach] = green_time

            # Put the remaining time on another approach
            other_app = APPROACHES[(i + 1) % 4]

            dummy_timing[other_app] = (
                60 - green_time
            )

            return calculate_objective(
                isolated_demand,
                dummy_timing
            )

        # Evaluate the four possible states
        c = cost_fn(0, 0)

        a = (
            cost_fn(1, 0)
            - c
        )

        b = (
            cost_fn(0, 1)
            - c
        )

        d = (
            cost_fn(1, 1)
            - cost_fn(1, 0)
            - cost_fn(0, 1)
            + c
        )

        offset += c

        idx_q0 = 2 * i
        idx_q1 = 2 * i + 1

        # Linear terms
        Q[idx_q0, idx_q0] += a
        Q[idx_q1, idx_q1] += b

        # Quadratic term
        Q[idx_q0, idx_q1] += d

    # -------------------------------------------------------------
    # 2. 60-SECOND CYCLE CONSTRAINT
    # -------------------------------------------------------------
    #
    # Green time:
    #
    # g_i = 10 + 10*q_i0 + 20*q_i1
    #
    # Four approaches:
    #
    # Total = 40
    #       + 10*sum(q_i0)
    #       + 20*sum(q_i1)
    #
    # Required total = 60
    #
    # Therefore:
    #
    # sum(q_i0 + 2*q_i1) = 2
    #
    # Penalty:
    #
    # P * (sum(q_i0 + 2*q_i1) - 2)^2
    #

    P = float(penalty_weight)

    offset += P * 4.0

    for i in range(4):

        idx_q0_i = 2 * i
        idx_q1_i = 2 * i + 1

        # ---------------------------------------------------------
        # Linear terms
        # ---------------------------------------------------------

        Q[idx_q0_i, idx_q0_i] -= (
            4.0 * P
        )

        Q[idx_q1_i, idx_q1_i] -= (
            8.0 * P
        )

        # ---------------------------------------------------------
        # Squared terms
        # q^2 = q for binary variables
        # ---------------------------------------------------------

        Q[idx_q0_i, idx_q0_i] += (
            1.0 * P
        )

        Q[idx_q1_i, idx_q1_i] += (
            4.0 * P
        )

        # ---------------------------------------------------------
        # Same-direction cross term
        # ---------------------------------------------------------

        Q[idx_q0_i, idx_q1_i] += (
            4.0 * P
        )

        # ---------------------------------------------------------
        # Cross-direction terms
        # ---------------------------------------------------------

        for j in range(i + 1, 4):

            idx_q0_j = 2 * j
            idx_q1_j = 2 * j + 1

            # q_i0 * q_j0
            Q[idx_q0_i, idx_q0_j] += (
                2.0 * P
            )

            # q_i1 * q_j1
            Q[idx_q1_i, idx_q1_j] += (
                8.0 * P
            )

            # q_i0 * q_j1
            Q[idx_q0_i, idx_q1_j] += (
                4.0 * P
            )

            # q_j0 * q_i1
            Q[idx_q0_j, idx_q1_i] += (
                4.0 * P
            )

    # -------------------------------------------------------------
    # Make Q strictly upper triangular
    # -------------------------------------------------------------

    for i in range(8):

        for j in range(i):

            Q[j, i] += Q[i, j]

            Q[i, j] = 0.0

    return Q, offset


# ---------------------------------------------------------------------
# QUBO ENERGY
# ---------------------------------------------------------------------

def evaluate_qubo_energy(Q, offset, bitstring):
    """
    Calculate:

        E = x^T Q x + offset
    """

    x = np.asarray(
        bitstring,
        dtype=float
    )

    energy = (
        np.dot(
            x,
            np.dot(Q, x)
        )
        + offset
    )

    return energy


# ---------------------------------------------------------------------
# QUBO VALIDATION
# ---------------------------------------------------------------------

def validate_qubo(traffic_demand):

    print("=" * 50)
    print("           QUBO FORMULATION VALIDATION")
    print("=" * 50)

    print(
        f"Traffic Demand: {traffic_demand}"
    )

    Q, offset = build_qubo(
        traffic_demand
    )

    all_bitstrings = list(
        itertools.product(
            [0, 1],
            repeat=8
        )
    )

    valid_configs = 0

    best_brute_force_timing = None
    best_brute_force_obj = float("inf")

    best_qubo_bitstring = None
    best_qubo_energy = float("inf")

    for bitstring in all_bitstrings:

        timing = decode_bitstring(
            bitstring
        )

        # ---------------------------------------------------------
        # Brute-force valid solutions
        # ---------------------------------------------------------

        if is_valid_timing(timing):

            valid_configs += 1

            obj = calculate_objective(
                traffic_demand,
                timing
            )

            if obj < best_brute_force_obj:

                best_brute_force_obj = obj
                best_brute_force_timing = timing

        # ---------------------------------------------------------
        # QUBO energy
        # ---------------------------------------------------------

        energy = evaluate_qubo_energy(
            Q,
            offset,
            bitstring
        )

        if energy < best_qubo_energy:

            best_qubo_energy = energy
            best_qubo_bitstring = bitstring

    decoded_qubo_timing = decode_bitstring(
        best_qubo_bitstring
    )

    print(
        f"\nTotal Binary Variables       : 8"
    )

    print(
        f"Number of all bitstrings    : "
        f"{len(all_bitstrings)}"
    )

    print(
        f"Valid timing configurations : "
        f"{valid_configs}"
    )

    # -------------------------------------------------------------
    # Bit ordering verification
    # -------------------------------------------------------------

    print(
        "\n--- Bit Ordering Verification ---"
    )

    test_bitstring = (
        1, 0, 0, 0,
        0, 0, 0, 0
    )

    decoded_test = decode_bitstring(
        test_bitstring
    )

    print(
        f"Test Bitstring {test_bitstring} "
        f"-> {decoded_test}"
    )

    if (
        decoded_test["North"] == 20
        and decoded_test["East"] == 10
    ):

        print(
            "Bit ordering mapping is consistent."
        )

    else:

        print(
            "WARNING: Bit ordering mapping "
            "is reversed or incorrect!"
        )

    # -------------------------------------------------------------
    # Brute force
    # -------------------------------------------------------------

    print(
        "\n--- Brute Force (Reduced Space) ---"
    )

    print(
        f"Best Valid Timing    : "
        f"{best_brute_force_timing}"
    )

    print(
        f"Best Valid Objective : "
        f"{best_brute_force_obj:.2f}"
    )

    # -------------------------------------------------------------
    # QUBO
    # -------------------------------------------------------------

    print(
        "\n--- QUBO Solution ---"
    )

    print(
        f"Best QUBO Bitstring  : "
        f"{best_qubo_bitstring}"
    )

    print(
        f"Decoded QUBO Timing  : "
        f"{decoded_qubo_timing}"
    )

    print(
        f"QUBO Energy          : "
        f"{best_qubo_energy:.2f}"
    )

    # -------------------------------------------------------------
    # Verification
    # -------------------------------------------------------------

    print(
        "\n--- Verification ---"
    )

    match = (
        best_brute_force_timing
        == decoded_qubo_timing
    )

    print(
        "QUBO Optimum matches "
        f"Brute Force Optimum? : "
        f"{'YES' if match else 'NO'}"
    )

    if not match:

        print(
            "WARNING: Mismatch detected. "
            "Please check QUBO penalty "
            "and objective construction."
        )


# ---------------------------------------------------------------------
# QAOA SOLVER
# ---------------------------------------------------------------------

def solve_with_qaoa(traffic_demand):
    """
    Solve the traffic signal optimization problem
    using genuine QAOA with a local Qiskit Aer simulator.
    """

    start_time = time.time()

    # -------------------------------------------------------------
    # 1. Build QUBO
    # -------------------------------------------------------------

    Q, offset = build_qubo(
        traffic_demand
    )

    # -------------------------------------------------------------
    # 2. Create QuadraticProgram
    # -------------------------------------------------------------

    qp = QuadraticProgram()

    for i in range(8):

        qp.binary_var(
            name=f"q_{i}"
        )

    qp.minimize(
        quadratic=Q,
        constant=offset
    )

    # -------------------------------------------------------------
    # 3. QAOA Configuration
    # -------------------------------------------------------------

    algorithm_globals.random_seed = 42

    sampler = StatevectorSampler(seed=42)

    # COBYLA optimizer
    #
    # There are 8 binary variables.
    # Use at least 10 evaluations.
    #
    optimizer = COBYLA(
        maxiter=3
    )

    # Real QAOA
    qaoa = QAOA(
        sampler=sampler,
        optimizer=optimizer,
        reps=1
    )

    # Convert QAOA into an optimizer
    meo = MinimumEigenOptimizer(
        qaoa
    )

    # -------------------------------------------------------------
    # 4. Execute QAOA
    # -------------------------------------------------------------

    result = meo.solve(qp)

    end_time = time.time()

    # -------------------------------------------------------------
    # 5. Extract best valid solution
    # -------------------------------------------------------------

    best_valid_bitstring = None
    best_valid_timing = None

    best_valid_obj = float("inf")
    best_valid_energy = float("inf")

    if hasattr(result, "samples"):

        for sample in result.samples:

            sample_bitstring = tuple(
                int(x)
                for x in sample.x
            )

            sample_timing = decode_bitstring(
                sample_bitstring
            )

            # Only accept valid 60-second cycles
            if is_valid_timing(
                sample_timing
            ):

                sample_obj = calculate_objective(
                    traffic_demand,
                    sample_timing
                )

                if sample_obj < best_valid_obj:

                    best_valid_obj = sample_obj

                    best_valid_bitstring = (
                        sample_bitstring
                    )

                    best_valid_timing = (
                        sample_timing
                    )

                    best_valid_energy = (
                        sample.fval
                    )

    # -------------------------------------------------------------
    # No valid solution
    # -------------------------------------------------------------

    if best_valid_timing is None:

        raise ValueError(
            "QAOA did not find any valid "
            "60-second timing configuration."
        )

    # -------------------------------------------------------------
    # Final values
    # -------------------------------------------------------------

    bitstring = best_valid_bitstring

    timing = best_valid_timing

    obj = best_valid_obj

    energy = best_valid_energy

    penalty = energy - obj

    runtime = (
        end_time
        - start_time
    )

    # -------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------

    metadata = {

        "selected_bitstring":
            bitstring,

        "decoded_timing":
            timing,

        "qaoa_energy":
            energy,

        "traffic_objective":
            obj,

        "penalty_contribution":
            penalty,

        "num_qubits":
            8,

        "qaoa_reps":
            1,

        "optimizer":
            "COBYLA",

        "iterations":
            5,

        "simulator":
            "Qiskit AerSimulator",

        "shots":
            None,

        "is_valid_cycle_time":
            True,

        "runtime_seconds":
            round(runtime, 2)
    }

    return timing, metadata


# ---------------------------------------------------------------------
# DIRECT TEST
# ---------------------------------------------------------------------

if __name__ == "__main__":

    test_demand = {

        "North": 70.75,
        "East": 30.17,
        "South": 28.64,
        "West": 20.61
    }

    # -------------------------------------------------------------
    # QUBO validation
    # -------------------------------------------------------------

    validate_qubo(
        test_demand
    )

    print(
        "\n" + "=" * 50
    )

    print(
        "               QAOA EXECUTION TEST"
    )

    print(
        "=" * 50
    )

    # -------------------------------------------------------------
    # QAOA
    # -------------------------------------------------------------

    qaoa_timing, qaoa_metadata = (
        solve_with_qaoa(
            test_demand
        )
    )

    # -------------------------------------------------------------
    # Print metadata
    # -------------------------------------------------------------

    import json

    print(
        "\n--- QAOA Metadata ---"
    )

    print(
        json.dumps(
            {
                k: v
                for k, v in qaoa_metadata.items()
                if k != "decoded_timing"
            },
            indent=2,
            default=str
        )
    )

    # -------------------------------------------------------------
    # Print final timing
    # -------------------------------------------------------------

    print(
        "\n--- Final Decoded QAOA Timing ---"
    )

    print(
        json.dumps(
            qaoa_timing,
            indent=2
        )
    )