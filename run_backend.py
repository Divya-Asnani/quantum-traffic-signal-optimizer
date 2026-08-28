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
from src.evaluation import evaluate_signal_timing

def run_pipeline():
    data_path = PROJECT_ROOT / "data" / "traffic.csv"
    
    print("\n[1] Loading Data...")
    df = pd.read_csv(data_path)

    print("\n[2] Running ML Prediction...")
    # This will load models/traffic_model.joblib automatically
    raw_prediction = predict_traffic(df)
    
    print("\n[3] Adapting Traffic Output...")
    traffic_demand = get_junction_demand(raw_prediction)
    print("Traffic Demand:")
    print(json.dumps(traffic_demand, indent=2))
    
    print("\n[4] Running Classical Optimizer...")
    optimization_result = optimize_signal_timing(traffic_demand)
    
    best_timing = optimization_result["signal_timing"]
    print("Classical Optimized Signal Timing:")
    print(json.dumps(best_timing, indent=2))
    
    print("\n[5] Running Evaluation...")
    evaluation_result = evaluate_signal_timing(traffic_demand, best_timing)
    
    print("\n--- Final Results ---")
    print(f"Objective Value: {evaluation_result['objective']:.2f}")
    print(f"Total Waiting Time: {evaluation_result['total_waiting_time']:.2f} vehicle-seconds")
    print("Queue Lengths:")
    print(json.dumps(evaluation_result['queue_length'], indent=2))
    print("Congestion Scores:")
    print(json.dumps(evaluation_result['congestion'], indent=2))

if __name__ == "__main__":
    run_pipeline()
