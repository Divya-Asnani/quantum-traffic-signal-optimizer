import sys
from pathlib import Path
import pandas as pd
import json

# Ensure we can import from src
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.traffic_prediction import predict_traffic
from src.traffic_adapter import get_junction_demand
from src.classical_optimizer import optimize_signal_timing
from src.quantum_optimizer import solve_with_qaoa
from src.comparison import compare_solutions

from src.ibm_quantum_optimizer import (
    submit_qaoa_job_ibm,
    get_qaoa_job_status,
    retrieve_qaoa_job_result,
)

def validate_demand(demand):
    """Ensure custom demand contains correct keys and non-negative values."""
    required_keys = {"North", "East", "South", "West"}
    if not isinstance(demand, dict) or set(demand.keys()) != required_keys:
        raise ValueError(f"Demand must be a dictionary with exact keys {required_keys}")
    for k, v in demand.items():
        if not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"Traffic demand for {k} must be a non-negative number.")


def rebalance_zero_demand_timing(timing, traffic_demand, cycle_time=60):
    """Move green time away from empty approaches to active approaches."""
    empty = [approach for approach, demand in traffic_demand.items() if demand <= 0]
    active = [approach for approach, demand in traffic_demand.items() if demand > 0]

    if not empty or not active:
        return timing

    adjusted = {approach: int(timing.get(approach, 0)) for approach in traffic_demand}
    released_time = sum(adjusted[approach] for approach in empty)
    for approach in empty:
        adjusted[approach] = 0

    while released_time >= 5:
        target = min(active, key=lambda approach: traffic_demand[approach] / max(adjusted[approach], 1))
        adjusted[target] += 5
        released_time -= 5

    if released_time:
        target = max(active, key=lambda approach: traffic_demand[approach])
        adjusted[target] += released_time

    if sum(adjusted.values()) != cycle_time:
        raise ValueError("Rebalanced signal timing does not match the cycle time.")

    return adjusted

def run_pipeline(custom_demand=None):
    
    if custom_demand is None:
        # [1] Loading Data
        data_path = PROJECT_ROOT / "data" / "traffic.csv"
        df = pd.read_csv(data_path)

        # [2] ML Prediction
        raw_prediction = predict_traffic(df)
        
        # [3] Adapting Traffic Output
        traffic_demand = get_junction_demand(raw_prediction)
    else:
        # Externally supplied scenario
        validate_demand(custom_demand)
        traffic_demand = custom_demand
    
    # [4] Classical Optimizer (Unrestricted Global Optimum Search)
    classical_full_result = optimize_signal_timing(traffic_demand)
    classical_full_timing = classical_full_result["signal_timing"]

    # [5] Classical Optimizer (Restricted to Quantum-Compatible Search Space)
    classical_restricted_result = optimize_signal_timing(
        traffic_demand,
        allowed_green_times=[10, 20, 30, 40]
    )
    classical_restricted_timing = classical_restricted_result["signal_timing"]
    
    # [6] Quantum Optimizer (QAOA)
    qaoa_failed = False
    try:
        qaoa_timing, qaoa_metadata = solve_with_qaoa(traffic_demand)
    except Exception as e:
        qaoa_failed = True
        qaoa_timing = classical_restricted_timing
        qaoa_metadata = {"error": str(e)}

    qaoa_timing = rebalance_zero_demand_timing(qaoa_timing, traffic_demand)
    qaoa_metadata["decoded_timing"] = qaoa_timing

    # [7] Validation Check
    assert sum(classical_full_timing.values()) == 60, "Classical full timing sum != 60"
    assert sum(classical_restricted_timing.values()) == 60, "Classical restricted timing sum != 60"
    assert sum(qaoa_timing.values()) == 60, "QAOA timing sum != 60"
    
    for v in classical_restricted_timing.values():
        assert v in [10, 20, 30, 40], f"Classical restricted timing invalid: {v}"
    if not qaoa_failed:
        for approach, value in qaoa_timing.items():
            assert value >= 0, f"QAOA timing invalid: {value}"
            if traffic_demand[approach] > 0:
                assert value > 0, f"Active approach has no green time: {approach}"
            
    # [8] Default Timing Baseline (Always Fixed 60s)
    default_timing = {
        "North": 15,
        "South": 15,
        "East": 15,
        "West": 15
    }
    
    # [9] Unified Comparison
    comparison = compare_solutions(
        traffic_demand,
        default_timing,
        classical_full_timing,
        classical_restricted_timing,
        qaoa_timing
    )
    
    return {
        "traffic_demand": traffic_demand,
        "default_timing": default_timing,
        "classical_full_timing": classical_full_timing,
        "classical_quantum_compatible_timing": classical_restricted_timing,
        "qaoa_timing": qaoa_timing,
        "comparison": comparison,
        "qaoa_metadata": qaoa_metadata,
        "qaoa_failed": qaoa_failed
    }

def prepare_pipeline(custom_demand=None):
    """
    Prepare traffic demand and classical solutions
    without running the IBM Quantum job.
    """

    if custom_demand is None:
        data_path = PROJECT_ROOT / "data" / "traffic.csv"
        df = pd.read_csv(data_path)

        raw_prediction = predict_traffic(df)
        traffic_demand = get_junction_demand(raw_prediction)

    else:
        validate_demand(custom_demand)
        traffic_demand = custom_demand

    # Full classical optimization
    classical_full_result = optimize_signal_timing(
        traffic_demand
    )

    classical_full_timing = (
        classical_full_result["signal_timing"]
    )

    # Quantum-compatible classical optimization
    classical_restricted_result = optimize_signal_timing(
        traffic_demand,
        allowed_green_times=[10, 20, 30, 40]
    )

    classical_restricted_timing = (
        classical_restricted_result["signal_timing"]
    )

    # Fixed baseline
    default_timing = {
        "North": 15,
        "South": 15,
        "East": 15,
        "West": 15
    }

    return {
        "traffic_demand": traffic_demand,
        "default_timing": default_timing,
        "classical_full_timing": classical_full_timing,
        "classical_quantum_compatible_timing":
            classical_restricted_timing
    }


def submit_ibm_pipeline(
    custom_demand=None,
    shots=512,
    reps=1
):
    """
    Prepare the traffic optimization pipeline and submit
    the QAOA circuit to real IBM Quantum hardware.

    This function returns immediately after submission.
    """

    prepared = prepare_pipeline(
        custom_demand=custom_demand
    )

    traffic_demand = prepared["traffic_demand"]

    job_id, ibm_metadata = submit_qaoa_job_ibm(
        traffic_demand,
        shots=shots,
        reps=reps
    )

    prepared["ibm_job_id"] = job_id
    prepared["qaoa_metadata"] = ibm_metadata
    prepared["qaoa_status"] = "QUEUED"

    return prepared


def retrieve_ibm_pipeline(
    job_id,
    traffic_demand,
    prepared_results
):
    """
    Retrieve a completed IBM Quantum job and create
    the final comparison results.
    """

    qaoa_timing, qaoa_metadata = retrieve_qaoa_job_result(
        job_id,
        traffic_demand
    )

    classical_full_timing = (
        prepared_results["classical_full_timing"]
    )

    classical_restricted_timing = (
        prepared_results[
            "classical_quantum_compatible_timing"
        ]
    )

    default_timing = (
        prepared_results["default_timing"]
    )

    comparison = compare_solutions(
        traffic_demand,
        default_timing,
        classical_full_timing,
        classical_restricted_timing,
        qaoa_timing
    )

    return {
        "traffic_demand": traffic_demand,
        "default_timing": default_timing,
        "classical_full_timing": classical_full_timing,
        "classical_quantum_compatible_timing":
            classical_restricted_timing,
        "qaoa_timing": qaoa_timing,
        "comparison": comparison,
        "qaoa_metadata": qaoa_metadata,
        "qaoa_failed": False,
        "qaoa_status": "DONE",
        "ibm_job_id": job_id
    }

if __name__ == "__main__":
    # If run directly, print a simple report
    result = run_pipeline()
    print("Backend run successful!")
    print(json.dumps({k: v for k, v in result.items() if k not in ["comparison", "classical_results", "qaoa_results"]}, indent=2))
