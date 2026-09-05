import time

from src.classical_optimizer import optimize_signal_timing


# ============================================================
# SAME TRAFFIC DEMAND USED FOR IBM QUANTUM
# ============================================================

traffic_demand = {
    "North": 70.75,
    "East": 30.17,
    "South": 28.64,
    "West": 20.61
}


# ============================================================
# RUN CLASSICAL OPTIMIZER
# ============================================================

print("=" * 60)
print("CLASSICAL TRAFFIC SIGNAL OPTIMIZATION")
print("=" * 60)

print("\nTraffic Demand:")
print(traffic_demand)

print("\nRunning classical optimizer...")

start_time = time.time()

result = optimize_signal_timing(
    traffic_demand,
    cycle_time=60,
    min_green=5,
    max_green=45,
    step=5
)

runtime = time.time() - start_time


# ============================================================
# GET RESULTS
# ============================================================

timing = result["signal_timing"]
objective = result["objective"]


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 60)
print("CLASSICAL OPTIMIZATION RESULT")
print("=" * 60)

print("\nOptimal Signal Timing:")

for direction, green_time in timing.items():
    print(
        f"{direction}: "
        f"{green_time} seconds"
    )

print(
    f"\nTotal Cycle: "
    f"{sum(timing.values())} seconds"
)

print(
    f"Objective: "
    f"{objective:.2f}"
)

print(
    f"Runtime: "
    f"{runtime:.6f} seconds"
)

print("=" * 60)