class Intersection:
    """
    Represents a signalized intersection.

    The intersection contains four traffic approaches.
    The names can represent physical directions such as
    North/South/East/West or another agreed mapping.
    """

    APPROACHES = ["North", "South", "East", "West"]

    def __init__(self, traffic_demand):
        self.traffic_demand = traffic_demand

    def validate(self):
        """Validate traffic demand for all approaches."""

        if not isinstance(self.traffic_demand, dict):
            raise ValueError("Traffic demand must be a dictionary.")

        for approach in self.APPROACHES:

            if approach not in self.traffic_demand:
                raise ValueError(
                    f"Missing traffic demand for {approach}"
                )

            demand = self.traffic_demand[approach]

            if not isinstance(demand, (int, float)):
                raise ValueError(
                    f"Traffic demand for {approach} must be numeric."
                )

            if demand < 0:
                raise ValueError(
                    f"Traffic demand cannot be negative for {approach}"
                )

        return True

    def get_total_demand(self):
        """Return total predicted traffic demand."""

        self.validate()

        return sum(self.traffic_demand.values())