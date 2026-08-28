def get_junction_demand(prediction_result):
    """
    Extract predicted vehicle counts from the traffic prediction output
    and map them to intersection approaches.

    Returns:
        Dictionary containing predicted traffic for
        North, South, East, West approaches.
    """

    demand = {}
    
    JUNCTION_MAPPING = {
        "Junction_1": "North",
        "Junction_2": "South",
        "Junction_3": "East",
        "Junction_4": "West"
    }

    for junction, result in prediction_result.items():

        if "predicted_vehicles" not in result:
            raise ValueError(
                f"Missing predicted_vehicles for {junction}"
            )

        approach = JUNCTION_MAPPING.get(junction, junction)
        demand[approach] = result["predicted_vehicles"]

    return demand