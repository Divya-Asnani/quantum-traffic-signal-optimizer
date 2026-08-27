def get_junction_demand(prediction_result):
    """
    Extract predicted vehicle counts from Person 1's
    traffic prediction output.

    Returns:
        Dictionary containing predicted traffic for
        each junction.
    """

    demand = {}

    for junction, result in prediction_result.items():

        if "predicted_vehicles" not in result:
            raise ValueError(
                f"Missing predicted_vehicles for {junction}"
            )

        demand[junction] = result["predicted_vehicles"]

    return demand