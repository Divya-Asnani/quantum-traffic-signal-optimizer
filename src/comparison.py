from src.evaluation import evaluate_signal_timing


def compare_solutions(
    traffic_demand,
    default_timing,
    classical_full_timing,
    classical_restricted_timing,
    quantum_timing
):
    """
    Compare default, unrestricted classical, quantum-compatible classical,
    and QAOA signal timings using the same evaluation function.
    """

    default_result = evaluate_signal_timing(
        traffic_demand,
        default_timing
    )

    classical_full_result = evaluate_signal_timing(
        traffic_demand,
        classical_full_timing
    )

    classical_restricted_result = evaluate_signal_timing(
        traffic_demand,
        classical_restricted_timing
    )

    quantum_result = evaluate_signal_timing(
        traffic_demand,
        quantum_timing
    )
    
    # Calculate Gaps
    gap_vs_restricted = quantum_result["objective"] - classical_restricted_result["objective"]
    gap_vs_full = quantum_result["objective"] - classical_full_result["objective"]

    return {
        "default": default_result,
        "classical_full": classical_full_result,
        "classical_restricted": classical_restricted_result,
        "quantum": quantum_result,
        "qaoa_gap_vs_quantum_compatible": gap_vs_restricted,
        "qaoa_gap_vs_full_classical": gap_vs_full,
    }
