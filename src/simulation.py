class Intersection:
    """
    Represents a four-way signalized intersection.
    """

    APPROACHES = ["North", "South", "East", "West"]

    def __init__(self, traffic_demand):
        self.traffic_demand = traffic_demand

    def validate(self):
        """Validate that all four approaches have traffic data."""

        for approach in self.APPROACHES:
            if approach not in self.traffic_demand:
                raise ValueError(
                    f"Missing traffic demand for {approach}"
                )

            if self.traffic_demand[approach] < 0:
                raise ValueError(
                    f"Traffic demand cannot be negative for {approach}"
                )

        return True

    