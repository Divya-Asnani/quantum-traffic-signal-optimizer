import sys
from pathlib import Path
import itertools
import numpy as np

# Ensure we can import from src
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation import calculate_objective

from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_algorithms.utils import algorithm_globals
from qiskit.primitives import StatevectorSampler
import warnings
from scipy.sparse import SparseEfficiencyWarning

# Suppress harmless internal Qiskit sparse matrix warnings
warnings.filterwarnings("ignore", category=SparseEfficiencyWarning)

# ---------------------------------------------------------------------
# PROBLEM DEFINITION & DECODING
# ---------------------------------------------------------------------

# The 8 binary variables represent:
# [q_N0, q_N1, q_E0, q_E1, q_S0, q_S1, q_W0, q_W1]
APPROACHES = ["North", "East", "South", "West"]

def decode_bitstring(bitstring):
    """
    Decodes an 8-bit bitstring into signal timings.
    
    Encoding per direction i:
    g_i = 10 + 10*q_i0 + 20*q_i1
    
    This guarantees exactly 4 possible green times:
    00 -> 10s
    10 -> 20s
    01 -> 30s
    11 -> 40s
    """
    if len(bitstring) != 8:
        raise ValueError("Bitstring must have exactly 8 bits.")
        
    signal_timing = {}
    for i, approach in enumerate(APPROACHES):
        q0 = bitstring[2*i]
        q1 = bitstring[2*i + 1]
        
        green_time = 10 + (10 * q0) + (20 * q1)
        signal_timing[approach] = green_time
        
    return signal_timing

def is_valid_timing(signal_timing):
    """
    Checks if the timing configuration meets the cycle time constraint.
    """
    return sum(signal_timing.values()) == 60

# ---------------------------------------------------------------------
# QUBO MATRIX CONSTRUCTION
# ---------------------------------------------------------------------

def build_qubo(traffic_demand, penalty_weight=100000):
    """
    Builds the QUBO matrix and constant offset for the optimization problem.
    Energy = x^T Q x + offset
    """
    Q = np.zeros((8, 8))
    offset = 0.0
    
    # 1. Traffic Objective Terms (Separable by direction)
    # We precompute the cost of the 4 states for each direction
    # and fit them to f(q0, q1) = c + a*q0 + b*q1 + d*q0*q1
    
    for i, approach in enumerate(APPROACHES):
        # We need the objective ONLY for this approach.
        # Since evaluation.calculate_objective is a sum of independent approach costs,
        # we can calculate it by passing 0 demand for other approaches to isolate it.
        
        isolated_demand = {app: (traffic_demand[app] if app == approach else 0) for app in APPROACHES}
        
        def cost_fn(q0, q1):
            timing = decode_bitstring([0]*8) # dummy
            timing[approach] = 10 + 10*q0 + 20*q1
            # Give 60 to others just to pass the valid sum if evaluation relies on it
            # Actually, evaluate_signal_timing/calculate_objective uses sum(timing.values()) for cycle time!
            # So cycle time must be 60.
            # We construct a full timing dict that sums to 60.
            dummy_timing = {app: 10 for app in APPROACHES}
            dummy_timing[approach] = 10 + 10*q0 + 20*q1
            # The remaining time doesn't matter because demand for other approaches is 0.
            # But wait, cycle time matters for wait time: Wait = Q * (cycle - green) / 2
            # Cycle time is exactly 60 in our constraint. So we fix cycle_time = 60 in cost calculation.
            # Let's mock a timing dict that sums to 60.
            dummy_timing = {app: 0 for app in APPROACHES}
            dummy_timing[approach] = 10 + 10*q0 + 20*q1
            # Adjust one of the 0 demand approaches to make the total sum 60
            other_app = APPROACHES[(i+1)%4]
            dummy_timing[other_app] = 60 - dummy_timing[approach]
            
            return calculate_objective(isolated_demand, dummy_timing)
        
        c = cost_fn(0, 0)
        a = cost_fn(1, 0) - c
        b = cost_fn(0, 1) - c
        d = cost_fn(1, 1) - cost_fn(1, 0) - cost_fn(0, 1) + c
        
        offset += c
        
        # Add to QUBO matrix (diagonal terms = linear terms since q^2 = q)
        idx_q0 = 2*i
        idx_q1 = 2*i + 1
        
        Q[idx_q0, idx_q0] += a
        Q[idx_q1, idx_q1] += b
        # Off-diagonal (upper triangular)
        Q[idx_q0, idx_q1] += d

    # 2. Cycle Time Penalty Constraint
    # Enforce: sum_i (q_{i,0} + 2 q_{i,1}) = 2
    # Penalty: P * (sum_i q_{i,0} + 2 sum_i q_{i,1} - 2)^2
    # Expansion:
    # P * [ (sum_i q_{i,0})^2 + 4(sum_i q_{i,1})^2 + 4(sum_i q_{i,0})(sum_i q_{i,1}) - 4(sum_i q_{i,0}) - 8(sum_i q_{i,1}) + 4 ]
    
    offset += penalty_weight * 4.0
    
    for i in range(4):
        idx_q0_i = 2*i
        idx_q1_i = 2*i + 1
        
        # Linear terms: -4 P q_{i,0} and -8 P q_{i,1}
        Q[idx_q0_i, idx_q0_i] -= 4.0 * penalty_weight
        Q[idx_q1_i, idx_q1_i] -= 8.0 * penalty_weight
        
        # Squared terms: P (q_{i,0})^2 = P q_{i,0} and 4 P (q_{i,1})^2 = 4 P q_{i,1}
        Q[idx_q0_i, idx_q0_i] += 1.0 * penalty_weight
        Q[idx_q1_i, idx_q1_i] += 4.0 * penalty_weight
        
        # Cross terms within the same direction: 4 P q_{i,0} q_{i,1}
        Q[idx_q0_i, idx_q1_i] += 4.0 * penalty_weight
        
        for j in range(i+1, 4):
            idx_q0_j = 2*j
            idx_q1_j = 2*j + 1
            
            # Cross terms from (sum_i q_{i,0})^2 -> 2 P q_{i,0} q_{j,0}
            Q[idx_q0_i, idx_q0_j] += 2.0 * penalty_weight
            
            # Cross terms from 4(sum_i q_{i,1})^2 -> 8 P q_{i,1} q_{j,1}
            Q[idx_q1_i, idx_q1_j] += 8.0 * penalty_weight
            
            # Cross terms from 4(sum_i q_{i,0})(sum_j q_{j,1})
            # 4 P q_{i,0} q_{j,1}
            Q[idx_q0_i, idx_q1_j] += 4.0 * penalty_weight
            # 4 P q_{j,0} q_{i,1}
            Q[idx_q0_j, idx_q1_i] += 4.0 * penalty_weight

    # Ensure strictly upper triangular for standard QUBO representation
    for i in range(8):
        for j in range(i):
            Q[j, i] += Q[i, j]
            Q[i, j] = 0.0
            
    return Q, offset

def evaluate_qubo_energy(Q, offset, bitstring):
    """
    Calculates E = x^T Q x + offset
    """
    x = np.array(bitstring)
    energy = np.dot(x, np.dot(Q, x)) + offset
    return energy

# ---------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------

def validate_qubo(traffic_demand):
    print("==================================================")
    print("           QUBO FORMULATION VALIDATION            ")
    print("==================================================")
    print(f"Traffic Demand: {traffic_demand}")
    
    Q, offset = build_qubo(traffic_demand)
    
    all_bitstrings = list(itertools.product([0, 1], repeat=8))
    
    valid_configs = 0
    best_brute_force_timing = None
    best_brute_force_obj = float('inf')
    
    best_qubo_bitstring = None
    best_qubo_energy = float('inf')
    
    for bitstring in all_bitstrings:
        timing = decode_bitstring(bitstring)
        
        # 1. Brute Force the Shared Objective
        if is_valid_timing(timing):
            valid_configs += 1
            obj = calculate_objective(traffic_demand, timing)
            if obj < best_brute_force_obj:
                best_brute_force_obj = obj
                best_brute_force_timing = timing
                
        # 2. Calculate QUBO Energy
        energy = evaluate_qubo_energy(Q, offset, bitstring)
        if energy < best_qubo_energy:
            best_qubo_energy = energy
            best_qubo_bitstring = bitstring
            
    # Decode the optimal QUBO state
    decoded_qubo_timing = decode_bitstring(best_qubo_bitstring)
    
    print(f"\nTotal Binary Variables       : 8")
    print(f"Number of all bitstrings   : {len(all_bitstrings)}")
    print(f"Valid timing configurations: {valid_configs}")
    
    print("\n--- Bit Ordering Verification ---")
    test_bitstring = (1, 0, 0, 0, 0, 0, 0, 0)
    decoded_test = decode_bitstring(test_bitstring)
    print(f"Test Bitstring {test_bitstring} -> {decoded_test}")
    if decoded_test['North'] == 20 and decoded_test['East'] == 10:
        print("Bit ordering mapping is consistent.")
    else:
        print("WARNING: Bit ordering mapping is reversed or incorrect!")
    
    print("\n--- Brute Force (Reduced Space) ---")
    print(f"Best Valid Timing    : {best_brute_force_timing}")
    print(f"Best Valid Objective : {best_brute_force_obj:.2f}")
    
    print("\n--- QUBO Solution ---")
    print(f"Best QUBO Bitstring  : {best_qubo_bitstring}")
    print(f"Decoded QUBO Timing  : {decoded_qubo_timing}")
    print(f"QUBO Energy          : {best_qubo_energy:.2f}")
    
    print("\n--- Verification ---")
    match = (best_brute_force_timing == decoded_qubo_timing)
    print(f"QUBO Optimum matches Brute Force Optimum? : {'YES' if match else 'NO'}")
    
    if not match:
        print(f"WARNING: Mismatch detected. Please check QUBO penalty and objective construction.")
        
# ---------------------------------------------------------------------
# QAOA SOLVER
# ---------------------------------------------------------------------

def solve_with_qaoa(traffic_demand):
    """
    Solves the traffic optimization problem using QAOA on a local simulator.
    """
    import time
    
    start_time = time.time()
    
    # 1. Build QUBO Matrix
    Q, offset = build_qubo(traffic_demand)
    
    # 2. Formulate as QuadraticProgram
    qp = QuadraticProgram()
    for i in range(8):
        qp.binary_var(name=f"q_{i}")
        
    qp.minimize(quadratic=Q, constant=offset)
    
    # 3. QAOA Configuration
    algorithm_globals.random_seed = 42
    
    # Using local exact sampler for stable brute-force-like testing
    sampler = StatevectorSampler(seed=42) 
    optimizer = COBYLA(maxiter=100)
    
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=1)
    meo = MinimumEigenOptimizer(qaoa)
    
    # 4. Solve
    result = meo.solve(qp)
    
    end_time = time.time()
    
    # 5. Extract and Validate Solution
    best_valid_bitstring = None
    best_valid_timing = None
    best_valid_obj = float('inf')
    best_valid_energy = float('inf')
    
    if hasattr(result, 'samples'):
        for sample in result.samples:
            sample_bitstring = tuple(int(x) for x in sample.x)
            sample_timing = decode_bitstring(sample_bitstring)
            if is_valid_timing(sample_timing):
                sample_obj = calculate_objective(traffic_demand, sample_timing)
                if sample_obj < best_valid_obj:
                    best_valid_obj = sample_obj
                    best_valid_bitstring = sample_bitstring
                    best_valid_timing = sample_timing
                    best_valid_energy = sample.fval
                    
    if best_valid_timing is None:
        raise ValueError("QAOA did not find any valid timing configuration in the sampled distribution.")
        
    bitstring = best_valid_bitstring
    timing = best_valid_timing
    obj = best_valid_obj
    energy = best_valid_energy
    penalty = energy - obj
    
    metadata = {
        "selected_bitstring": bitstring,
        "decoded_timing": timing,
        "qaoa_energy": energy,
        "traffic_objective": obj,
        "penalty_contribution": penalty,
        "num_qubits": 8,
        "qaoa_reps": 1,
        "optimizer": "COBYLA",
        "iterations": 100,
        "is_valid_cycle_time": True,
        "runtime_seconds": round(end_time - start_time, 2)
    }
    
    return timing, metadata

if __name__ == "__main__":
    # Test with the real traffic demand output we got previously
    test_demand = {
        "North": 70.75,
        "East": 30.17,
        "South": 28.64,
        "West": 20.61
    }
    validate_qubo(test_demand)
    
    print("\n==================================================")
    print("               QAOA EXECUTION TEST                ")
    print("==================================================")
    
    qaoa_timing, qaoa_metadata = solve_with_qaoa(test_demand)
    
    import json
    print("\n--- QAOA Metadata ---")
    print(json.dumps({k: v for k, v in qaoa_metadata.items() if k != 'decoded_timing'}, indent=2))
    
    print("\n--- Final Decoded QAOA Timing ---")
    print(json.dumps(qaoa_timing, indent=2))
