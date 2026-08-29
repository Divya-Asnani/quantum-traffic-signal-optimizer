from itertools import product

from src.evaluation import (
    calculate_queue_length,
    calculate_waiting_time,
    calculate_congestion,
    calculate_objective,
)


def optimize_signal_timing(
    traffic_demand,
    cycle_time=60,
    min_green=5,
    max_green=45,
    step=5,
    allowed_green_times=None,
):
    """
    Classical exhaustive/grid-search optimizer.

    Searches different green-time allocations while
    keeping the total green time equal to the cycle time.

    Example:

        North = 25
        South = 15
        East  = 10
        West  = 10

        Total = 60 seconds
    """

    approaches = list(traffic_demand.keys())

    best_timing = None
    best_objective = float("inf")

    if allowed_green_times is not None:
        possible_times = allowed_green_times
    else:
        possible_times = range(
            min_green,
            max_green + 1,
            step
        )

    # Generate every possible timing combination
    for timing_values in product(
        possible_times,
        repeat=len(approaches)
    ):

        # Check cycle-time constraint
        if sum(timing_values) != cycle_time:
            continue

        signal_timing = dict(
            zip(approaches, timing_values)
        )

        objective = calculate_objective(
            traffic_demand,
            signal_timing
        )

        if objective < best_objective:

            best_objective = objective
            best_timing = signal_timing.copy()

    if best_timing is None:
        raise ValueError(
            "No valid signal timing configuration found. "
            "Check cycle_time, min_green, max_green and step."
        )

    return {
        "signal_timing": best_timing,
        "objective": best_objective,
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    traffic = {
        "North": 80,
        "South": 60,
        "East": 30,
        "West": 20,
    }

    result = optimize_signal_timing(
        traffic
    )

    print("\nClassical Optimization Result")
    print("--------------------------------")

    print("Traffic Demand:")
    print(traffic)

    print("\nOptimal Signal Timing:")
    print(result["signal_timing"])

    print("\nObjective:")
    print(round(result["objective"], 2))