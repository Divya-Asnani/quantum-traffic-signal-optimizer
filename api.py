from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
from pathlib import Path

from run_backend import (
    PROJECT_ROOT,
    submit_ibm_pipeline,
    retrieve_ibm_pipeline,
)
from src.comparison import compare_solutions
from src.evaluation import calculate_objective
from src.traffic_adapter import get_junction_demand
from src.traffic_prediction import predict_traffic

# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Quantum Traffic Signal Optimizer API",
    version="2.0.0"
)

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# REQUEST MODEL
# ============================================================

class TrafficDemand(BaseModel):
    North: float = Field(ge=0)
    East: float = Field(ge=0)
    South: float = Field(ge=0)
    West: float = Field(ge=0)


# ============================================================
# IN-MEMORY JOB STORE
# ============================================================

jobs = {}


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Quantum Traffic Signal Optimizer"
    }


# ============================================================
# AI TRAFFIC PREDICTION
# ============================================================

@app.get("/api/predict")
def predict_next_hour():

    try:

        data_path = Path(PROJECT_ROOT) / "data" / "traffic.csv"
        data = pd.read_csv(data_path)
        prediction = predict_traffic(data)
        demand = get_junction_demand(prediction)

        return {
            "traffic_demand": demand,
            "predictions": prediction,
            "source": "AI Prediction",
            "model": "Random Forest Regressor",
            "dataset": "data/traffic.csv"
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# SUBMIT QAOA JOB
# ============================================================

@app.post("/api/optimize")
def optimize(demand: TrafficDemand):

    try:

        custom_demand = {
            "North": demand.North,
            "East": demand.East,
            "South": demand.South,
            "West": demand.West
        }

        prepared = submit_ibm_pipeline(
            custom_demand=custom_demand,
            shots=512,
            reps=1
        )

        job_id = prepared["ibm_job_id"]

        jobs[job_id] = prepared

        queued_comparison = {
            "default": {
                "timing": prepared["default_timing"],
                "objective": calculate_objective(
                    prepared["traffic_demand"],
                    prepared["default_timing"]
                )
            },
            "classical_full": {
                "timing": prepared["classical_full_timing"],
                "objective": calculate_objective(
                    prepared["traffic_demand"],
                    prepared["classical_full_timing"]
                )
            },
            "classical_quantum_compatible": {
                "timing": prepared["classical_quantum_compatible_timing"],
                "objective": calculate_objective(
                    prepared["traffic_demand"],
                    prepared["classical_quantum_compatible_timing"]
                )
            },
            "qaoa": None
        }

        return {
            "status": "QUEUED",
            "job_id": job_id,
            "traffic_demand": prepared["traffic_demand"],
            "default_timing": prepared["default_timing"],
            "classical_full_timing": prepared["classical_full_timing"],
            "classical_quantum_compatible_timing":
                prepared["classical_quantum_compatible_timing"],
            "comparison": queued_comparison,
            "qaoa_metadata": prepared["qaoa_metadata"]
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# CHECK JOB STATUS
# ============================================================

@app.get("/api/job/{job_id}/status")
def job_status(job_id: str):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job ID not found."
        )

    try:

        from src.ibm_quantum_optimizer import get_qaoa_job_status

        status = get_qaoa_job_status(job_id)

        return {
            "job_id": job_id,
            "status": status
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# RETRIEVE COMPLETED RESULT
# ============================================================

@app.get("/api/job/{job_id}/result")
def job_result(job_id: str):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job ID not found."
        )

    prepared = jobs[job_id]

    try:

        from src.ibm_quantum_optimizer import get_qaoa_job_status

        status = get_qaoa_job_status(job_id)

        if "DONE" not in status.upper():
            return {
                "status": status,
                "job_id": job_id,
                "message": "IBM Quantum job is not completed yet."
            }

        result = retrieve_ibm_pipeline(
            job_id=job_id,
            traffic_demand=prepared["traffic_demand"],
            prepared_results=prepared
        )

        result["status"] = "DONE"

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )