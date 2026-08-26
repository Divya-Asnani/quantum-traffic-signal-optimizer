from src.evaluation import evaluate_signal_timing


def compare_solutions(
    traffic_demand,
    default_timing,
    classical_timing,
    quantum_timing
):
    """
    Compare default, classical, and quantum signal timings
    using the same evaluation function.
    """

    # Evaluate default timing
    default_result = evaluate_signal_timing(
        traffic_demand,
        default_timing
    )

    # Evaluate classical timing
    classical_result = evaluate_signal_timing(
        traffic_demand,
        classical_timing
    )

    # Evaluate quantum timing
    quantum_result = evaluate_signal_timing(
        traffic_demand,
        quantum_timing
    )

    return {
        "default": default_result,
        "classical": classical_result,
        "quantum": quantum_result
    }


# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":

    # Temporary traffic data
    traffic = {
        "North": 80,
        "South": 60,
        "East": 30,
        "West": 20
    }

    # Current/default signal timing
    default_timing = {
        "North": 30,
        "South": 30,
        "East": 30,
        "West": 30
    }

    # Temporary classical optimizer output
    classical_timing = {
        "North": 40,
        "South": 35,
        "East": 25,
        "West": 20
    }

    # Temporary QAOA output
    quantum_timing = {
        "North": 45,
        "South": 35,
        "East": 25,
        "West": 15
    }

    comparison = compare_solutions(
        traffic,
        default_timing,
        classical_timing,
        quantum_timing
    )

    print("\n========== SOLUTION COMPARISON ==========")

    for solution, result in comparison.items():

        print(f"\n{solution.upper()}")

        print("Signal Timing:")
        print(result["signal_timing"])

        print("Total Queue:")
        print(result["total_queue"])

        print("Total Waiting Time:")
        print(result["total_waiting_time"])

        print("Average Congestion:")
        print(result["average_congestion"])

        print("Objective:")
        print(result["objective"])

        