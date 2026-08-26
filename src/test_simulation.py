from src.evaluation import calculate_queue_length
from src.simulation import Intersection


traffic = {
    "North": 80,
    "South": 60,
    "East": 30,
    "West": 20
}

intersection = Intersection(traffic)

print("Traffic demand:")
print(intersection.traffic_demand)

print("\nValidation:")
print(intersection.validate())

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

    result = calculate_queue_length(traffic, timing)

    print("Queue Length:")
    print(result)
    