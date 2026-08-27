from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.data_preprocessing import (
    prepare_model_data,
    create_features,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
)


# ============================================================
# PATH TO SAVED MODEL
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = PROJECT_ROOT / "models" / "traffic_model.joblib"


# ============================================================
# FEATURES
# ============================================================

CATEGORICAL_FEATURES = [
    "Junction"
]

NUMERICAL_FEATURES = [
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
    "traffic_1h_ago",
    "traffic_2h_ago",
    "traffic_3h_ago",
    "rolling_mean_3h",
]


# ============================================================
# CREATE RANDOM FOREST PIPELINE
# ============================================================

def create_model_pipeline():

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "junction",
                OneHotEncoder(handle_unknown="ignore"),
                CATEGORICAL_FEATURES
            ),
            (
                "numerical",
                "passthrough",
                NUMERICAL_FEATURES
            )
        ]
    )

    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", model)
        ]
    )

    return pipeline


# ============================================================
# TRAIN MODEL
# ============================================================

def train_model(data_path, model_path=MODEL_PATH):

    # Load and preprocess dataset
    df = prepare_model_data(data_path)

    # Sort chronologically
    df = df.sort_values("DateTime").reset_index(drop=True)

    # --------------------------------------------------------
    # 80% TRAIN / 20% TEST
    # --------------------------------------------------------

    split_index = int(len(df) * 0.80)

    split_time = df.loc[
        split_index,
        "DateTime"
    ]

    train_df = df[
        df["DateTime"] < split_time
    ].copy()

    test_df = df[
        df["DateTime"] >= split_time
    ].copy()

    # --------------------------------------------------------
    # INPUT FEATURES AND TARGET
    # --------------------------------------------------------

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    # --------------------------------------------------------
    # CREATE MODEL
    # --------------------------------------------------------

    pipeline = create_model_pipeline()

    # Train
    pipeline.fit(
        X_train,
        y_train
    )

    # --------------------------------------------------------
    # PREDICTIONS
    # --------------------------------------------------------

    predictions = pipeline.predict(X_test)

    # --------------------------------------------------------
    # EVALUATION
    # --------------------------------------------------------

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions
        )
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    # --------------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------------

    model_path = Path(model_path)

    model_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    joblib.dump(
        pipeline,
        model_path
    )

    print("======================================")
    print("       RANDOM FOREST TRAINING")
    print("======================================")

    print(f"Training rows : {len(train_df)}")
    print(f"Testing rows  : {len(test_df)}")

    print("\nModel Performance")
    print("-------------------------")

    print(f"MAE  : {mae:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"R²   : {r2:.4f}")

    print("\nModel saved at:")
    print(model_path)

    return pipeline, {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2
    }


# ============================================================
# LOAD SAVED MODEL
# ============================================================

def load_model(model_path=MODEL_PATH):

    model_path = Path(model_path)

    if not model_path.exists():

        raise FileNotFoundError(
            f"Model not found: {model_path}"
        )

    return joblib.load(model_path)


# ============================================================
# PREDICT TRAFFIC
# ============================================================

# ============================================================
# PREDICT TRAFFIC
# ============================================================

def predict_traffic(
    input_data,
    model_path=MODEL_PATH
):

    # Load trained model
    model = load_model(model_path)

    # Don't modify original dataframe
    df = input_data.copy()

    # --------------------------------------------------------
    # VALIDATE INPUT
    # --------------------------------------------------------

    required_columns = [
        "DateTime",
        "Junction",
        "Vehicles"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # CREATE REQUIRED FEATURES
    # --------------------------------------------------------

    df = create_features(df)

    # Remove rows where historical features
    # are not available
    df = df.dropna(
        subset=[
            "traffic_1h_ago",
            "traffic_2h_ago",
            "traffic_3h_ago",
            "rolling_mean_3h"
        ]
    ).copy()

    if df.empty:
        raise ValueError(
            "Not enough historical data for prediction."
        )

    # --------------------------------------------------------
    # GET LATEST RECORD FOR EACH JUNCTION
    # --------------------------------------------------------

    latest = (
        df
        .sort_values("DateTime")
        .groupby("Junction")
        .tail(1)
        .copy()
    )

    # --------------------------------------------------------
    # SELECT MODEL FEATURES
    # --------------------------------------------------------

    X = latest[FEATURE_COLUMNS]

    # --------------------------------------------------------
    # PREDICT
    # --------------------------------------------------------

    predictions = model.predict(X)

    # --------------------------------------------------------
    # FORMAT OUTPUT
    # --------------------------------------------------------

    result = {}

    for (_, row), prediction in zip(
        latest.iterrows(),
        predictions
    ):

        junction = int(row["Junction"])

        result[f"Junction_{junction}"] = {
            "predicted_vehicles": round(
                float(prediction),
                2
            ),
            "prediction_for": (
                row["DateTime"]
                + pd.Timedelta(hours=1)
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

    return result