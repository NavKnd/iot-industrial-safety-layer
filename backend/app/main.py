from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from backend.db.database import metadata, engine

# Create the database tables
metadata.create_all(bind=engine)


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

from backend.db.database import SessionLocal, sensor_data_table


class SensorData(BaseModel):
    device_id: str
    temperature: float
    gas_level: float


@app.post("/sensor-data")
def insert_sensor_data(data: SensorData):
    db = SessionLocal()
    try:
        insert_query = sensor_data_table.insert().values(
            device_id=data.device_id,
            temperature=data.temperature,
            gas_level=data.gas_level
        )
        db.execute(insert_query)
        db.commit()
        return {"message": "Data inserted successfully!"}
    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

from sqlalchemy import select
from backend.db.database import SessionLocal, sensor_data_table

@app.get("/all-data")
def get_all_data():
    with SessionLocal() as session:
        query = select(sensor_data_table)
        result = session.execute(query).fetchall()
        return [dict(row._mapping) for row in result]
