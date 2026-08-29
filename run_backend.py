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

def validate_demand(demand):
    """Ensure custom demand contains correct keys and non-negative values."""
    required_keys = {"North", "East", "South", "West"}
    if not isinstance(demand, dict) or set(demand.keys()) != required_keys:
        raise ValueError(f"Demand must be a dictionary with exact keys {required_keys}")
    for k, v in demand.items():
        if not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"Traffic demand for {k} must be a non-negative number.")

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

    # [7] Validation Check
    assert sum(classical_full_timing.values()) == 60, "Classical full timing sum != 60"
    assert sum(classical_restricted_timing.values()) == 60, "Classical restricted timing sum != 60"
    assert sum(qaoa_timing.values()) == 60, "QAOA timing sum != 60"
    
    for v in classical_restricted_timing.values():
        assert v in [10, 20, 30, 40], f"Classical restricted timing invalid: {v}"
    if not qaoa_failed:
        for v in qaoa_timing.values():
            assert v in [10, 20, 30, 40], f"QAOA timing invalid: {v}"
            
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

if __name__ == "__main__":
    # If run directly, print a simple report
    result = run_pipeline()
    print("Backend run successful!")
    print(json.dumps({k: v for k, v in result.items() if k not in ["comparison", "classical_results", "qaoa_results"]}, indent=2))
