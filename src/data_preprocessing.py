import pandas as pd


def load_data(file_path):
    """
    Load the raw traffic dataset.
    """
    df = pd.read_csv(file_path)

    # Convert DateTime to proper datetime format
    df["DateTime"] = pd.to_datetime(df["DateTime"])

    return df


def create_features(df):
    """
    Create time-based and historical traffic features.
    """

    # Work on a copy
    df = df.copy()

    # Ensure correct data types
    df["DateTime"] = pd.to_datetime(
    df["DateTime"],
    format="mixed",
    errors="coerce"
)
    df["Junction"] = pd.to_numeric(
        df["Junction"],
        errors="coerce"
    )

    df["Vehicles"] = pd.to_numeric(
        df["Vehicles"],
        errors="coerce"
    )

    # Remove invalid required rows
    df = df.dropna(
        subset=[
            "DateTime",
            "Junction",
            "Vehicles"
        ]
    )

    # Sort by junction and time
    df = df.sort_values(
        ["Junction", "DateTime"]
    ).reset_index(drop=True)
    # -----------------------------
    # Time-based features
    # -----------------------------

    df["hour"] = df["DateTime"].dt.hour

    df["day_of_week"] = df["DateTime"].dt.dayofweek

    df["month"] = df["DateTime"].dt.month

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    # -----------------------------
    # Historical traffic features
    # -----------------------------

    df["traffic_1h_ago"] = (
        df.groupby("Junction")["Vehicles"]
        .shift(1)
    )

    df["traffic_2h_ago"] = (
        df.groupby("Junction")["Vehicles"]
        .shift(2)
    )

    df["traffic_3h_ago"] = (
        df.groupby("Junction")["Vehicles"]
        .shift(3)
    )

    # -----------------------------
    # Rolling average of previous
    # three hours
    # -----------------------------

    df["rolling_mean_3h"] = (
        df.groupby("Junction")["Vehicles"]
        .transform(
            lambda x: x.shift(1).rolling(3).mean()
        )
    )

    # -----------------------------
    # Prediction target
    # -----------------------------

    # Predict traffic volume one hour ahead
    df["target_vehicles"] = (
        df.groupby("Junction")["Vehicles"]
        .shift(-1)
    )

    return df


def prepare_model_data(file_path):
    """
    Load the raw dataset, create features,
    and remove rows that cannot be used
    for model training.
    """

    df = load_data(file_path)

    df = create_features(df)

    # Remove rows without enough historical data
    # or without a future target.
    df_model = df.dropna(
        subset=[
            "traffic_1h_ago",
            "traffic_2h_ago",
            "traffic_3h_ago",
            "rolling_mean_3h",
            "target_vehicles",
        ]
    ).copy()

    # Sort chronologically for time-based splitting
    df_model = (
        df_model
        .sort_values("DateTime")
        .reset_index(drop=True)
    )

    return df_model


# Features used by the ML model
FEATURE_COLUMNS = [
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "Junction",
    "traffic_1h_ago",
    "traffic_2h_ago",
    "traffic_3h_ago",
    "rolling_mean_3h",
]

# Prediction target
TARGET_COLUMN = "target_vehicles"