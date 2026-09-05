from src.evaluation import calculate_objective


def compare_solutions(
    traffic_demand,
    default_timing,
    classical_full_timing,
    classical_restricted_timing,
    qaoa_timing
):
    """
    Compare default, classical, quantum-compatible classical,
    and QAOA signal timings.
    """

    default_objective = calculate_objective(
        traffic_demand,
        default_timing
    )

    classical_full_objective = calculate_objective(
        traffic_demand,
        classical_full_timing
    )

    classical_restricted_objective = calculate_objective(
        traffic_demand,
        classical_restricted_timing
    )

    qaoa_objective = calculate_objective(
        traffic_demand,
        qaoa_timing
    )

    return {
        "default": {
            "timing": default_timing,
            "objective": default_objective
        },
        "classical_full": {
            "timing": classical_full_timing,
            "objective": classical_full_objective
        },
        "classical_quantum_compatible": {
            "timing": classical_restricted_timing,
            "objective": classical_restricted_objective
        },
        "qaoa": {
            "timing": qaoa_timing,
            "objective": qaoa_objective
        }
    }


def print_comparison(
    traffic_demand,
    default_timing,
    classical_full_timing,
    classical_restricted_timing,
    qaoa_timing
):
    """
    Print a readable comparison report.
    """

    comparison = compare_solutions(
        traffic_demand,
        default_timing,
        classical_full_timing,
        classical_restricted_timing,
        qaoa_timing
    )

    print("=" * 60)
    print("CLASSICAL VS QUANTUM COMPARISON")
    print("=" * 60)

    print("\nTraffic Demand:")
    print(traffic_demand)

    print("\nDefault Timing:")
    print(default_timing)
    print(
        f"Objective: "
        f"{comparison['default']['objective']:.2f}"
    )

    print("\nClassical Full Timing:")
    print(classical_full_timing)
    print(
        f"Objective: "
        f"{comparison['classical_full']['objective']:.2f}"
    )

    print("\nClassical Quantum-Compatible Timing:")
    print(classical_restricted_timing)
    print(
        f"Objective: "
        f"{comparison['classical_quantum_compatible']['objective']:.2f}"
    )

    print("\nQAOA Timing:")
    print(qaoa_timing)
    print(
        f"Objective: "
        f"{comparison['qaoa']['objective']:.2f}"
    )

    print("\n" + "=" * 60)
