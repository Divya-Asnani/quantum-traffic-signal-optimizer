def calculate_queue_length(traffic_demand, signal_timing):
    """
    Calculate estimated queue length for each approach.

    Assumption:
    1 vehicle can be served per second of green time.
    """

    queue_length = {}

    for approach in traffic_demand:
        demand = traffic_demand[approach]
        green_time = signal_timing[approach]

        vehicles_served = green_time

        queue = max(0, demand - vehicles_served)

        queue_length[approach] = queue

    return queue_length


def calculate_waiting_time(traffic_demand, signal_timing):
    """
    Calculate estimated total waiting time.

    Waiting time is measured in vehicle-seconds.

    Assumption:
    Vehicles waiting during the red phase experience
    an average wait of half the red duration.
    """

    queue_length = calculate_queue_length(
        traffic_demand,
        signal_timing
    )

    total_waiting_time = {}

    cycle_time = sum(signal_timing.values())

    for approach in traffic_demand:

        green_time = signal_timing[approach]

        red_time = cycle_time - green_time

        average_wait = red_time / 2

        waiting_time = (
            queue_length[approach] * average_wait
        )

        total_waiting_time[approach] = waiting_time

    return total_waiting_time


def calculate_congestion(traffic_demand, signal_timing):
    """
    Calculate congestion score for each approach.

    Congestion score is based on the percentage
    of traffic demand remaining in the queue.

    Score range: 0 to 100.
    """

    queue_length = calculate_queue_length(
        traffic_demand,
        signal_timing
    )

    congestion = {}

    for approach in traffic_demand:

        demand = traffic_demand[approach]
        queue = queue_length[approach]

        if demand == 0:
            congestion[approach] = 0
        else:
            score = (queue / demand) * 100
            congestion[approach] = min(100, score)

    return congestion


def calculate_objective(traffic_demand, signal_timing):
    """
    Calculate the overall traffic objective.

    Lower objective value means better traffic performance.
    """

    queue_length = calculate_queue_length(
        traffic_demand,
        signal_timing
    )

    waiting_time = calculate_waiting_time(
        traffic_demand,
        signal_timing
    )

    congestion = calculate_congestion(
        traffic_demand,
        signal_timing
    )

    total_queue = sum(queue_length.values())
    total_waiting = sum(waiting_time.values())
    
    if len(congestion) > 0:
        average_congestion = sum(congestion.values()) / len(congestion)
    else:
        average_congestion = 0

    # Unified interpretable weights
    queue_weight = 60
    congestion_weight = 50

    objective = (
        total_waiting
        + (queue_weight * total_queue)
        + (congestion_weight * average_congestion)
    )

    return objective


def evaluate_signal_timing(traffic_demand, signal_timing):
    """
    Evaluate a complete signal timing configuration.

    Returns:
        Queue length
        Waiting time
        Congestion
        Objective value
    """

    queue_length = calculate_queue_length(
        traffic_demand,
        signal_timing
    )

    waiting_time = calculate_waiting_time(
        traffic_demand,
        signal_timing
    )

    congestion = calculate_congestion(
        traffic_demand,
        signal_timing
    )

    objective = calculate_objective(
        traffic_demand,
        signal_timing
    )

    total_queue = sum(queue_length.values())
    total_waiting = sum(waiting_time.values())
    average_congestion = sum(congestion.values()) / len(congestion)

    return {
        "signal_timing": signal_timing,
        "queue_length": queue_length,
        "waiting_time": waiting_time,
        "congestion": congestion,
        "total_queue": total_queue,
        "total_waiting_time": total_waiting,
        "average_congestion": average_congestion,
        "objective": objective
    }


# --------------------------------------------------
# TEST
# --------------------------------------------------

if __name__ == "__main__":

    traffic = {
        "North": 80,
        "South": 60,
        "East": 30,
        "West": 20
    }

    timing = {
        "North": 30,
        "South": 30,
        "East": 30,
        "West": 30
    }

    # Calculate queue
    queue = calculate_queue_length(
        traffic,
        timing
    )

    # Calculate waiting time
    waiting = calculate_waiting_time(
        traffic,
        timing
    )

    # Calculate congestion
    congestion = calculate_congestion(
        traffic,
        timing
    )

    # Calculate objective
    objective = calculate_objective(
        traffic,
        timing
    )

    # Complete evaluation
    result = evaluate_signal_timing(
        traffic,
        timing
    )

    print("\n========== TRAFFIC EVALUATION ==========")

    print("\nTraffic Demand:")
    print(traffic)

    print("\nSignal Timing:")
    print(timing)

    print("\nQueue Length:")
    print(queue)

    print("\nWaiting Time (vehicle-seconds):")
    print(waiting)

    print("\nTotal Waiting Time:")
    print(sum(waiting.values()))

    print("\nCongestion Score:")
    print(congestion)

    print("\nObjective Value:")
    print(objective)

    print("\nComplete Evaluation:")
    print(result)