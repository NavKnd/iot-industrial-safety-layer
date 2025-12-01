from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(
    title="IoT-Ready Industrial Safety Layer",
    description="Backend API for sensor data ingestion, validation, and alerts.",
    version="0.1.0",
)

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    message: str

@app.get("/", response_model=HealthResponse)
def root():
    """
    Simple health-check endpoint.
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow(),
        message="IoT Safety Layer backend is running.",
    )
