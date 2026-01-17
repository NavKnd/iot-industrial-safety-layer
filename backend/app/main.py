from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import datetime
from collections import defaultdict, deque
import statistics
import os


from backend.db.database import (
    metadata,
    engine,
    SessionLocal,
    sensor_data_table,
    alert_table
)

from sqlalchemy import select, update, func, desc


# ------------------ DATABASE SETUP ------------------
metadata.create_all(bind=engine)


# ------------------ FASTAPI APP ------------------
app = FastAPI(
    title="IoT-Ready Industrial Safety Layer",
    description="Backend API for sensor data ingestion, validation, and alerts.",
    version="1.0.0",
)



# ------------------ HEALTH CHECK ------------------
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    message: str


@app.get("/", response_model=HealthResponse)
def root():
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow(),
        message="IoT Safety Layer backend is running.",
    )


# ------------------ SENSOR MODEL ------------------
class SensorData(BaseModel):
    device_id: str = Field(..., min_length=3, max_length=50)
    temperature: float = Field(..., ge=-40, le=150)
    gas_level: float = Field(..., ge=0, le=1000)


# ------------------ IN-MEMORY HISTORY (Z-SCORE) ------------------
WINDOW_SIZE = 20
temp_history = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))
gas_history = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))


def zscore_anomaly(values, current):
    if len(values) < 10:
        return False

    mean = statistics.mean(values)
    stdev = statistics.stdev(values)

    if stdev == 0:
        return False

    return abs(current - mean) > 3 * stdev


# ------------------ SENSOR INGESTION ------------------
@app.post("/sensor-data")
def insert_sensor_data(data: SensorData):
    db = SessionLocal()

    try:
        # Store sensor data
        db.execute(
            sensor_data_table.insert().values(
                device_id=data.device_id,
                temperature=data.temperature,
                gas_level=data.gas_level
            )
        )
        db.commit()

    except Exception as e:
        db.rollback()
        return {"error": str(e)}

    # ---------- STORE FOR Z-SCORE ----------
    temp_history[data.device_id].append(data.temperature)
    gas_history[data.device_id].append(data.gas_level)

    alerts = []

    # ---------- THRESHOLD ALERTS ----------
    if data.gas_level > 600:
        alerts.append(("HIGH_GAS", "HIGH", "Dangerous gas level detected"))
    elif data.gas_level > 300:
        alerts.append(("HIGH_GAS", "MEDIUM", "Elevated gas level detected"))

    if data.temperature > 80:
        alerts.append(("HIGH_TEMP", "HIGH", "Critical temperature detected"))
    elif data.temperature > 60:
        alerts.append(("HIGH_TEMP", "MEDIUM", "High temperature detected"))
    elif data.temperature < 0:
        alerts.append(("LOW_TEMP", "LOW", "Low temperature detected"))

    # ---------- Z-SCORE ANOMALY ----------
    if zscore_anomaly(temp_history[data.device_id], data.temperature):
        alerts.append((
            "TEMP_ANOMALY",
            "MEDIUM",
            "Temperature deviates significantly from recent behavior"
        ))

    if zscore_anomaly(gas_history[data.device_id], data.gas_level):
        alerts.append((
            "GAS_ANOMALY",
            "HIGH",
            "Gas level deviates significantly from recent behavior"
        ))

    # ---------- ROLLING DEVIATION (DB-BASED) ----------
    recent_query = (
        select(sensor_data_table)
        .where(sensor_data_table.c.device_id == data.device_id)
        .order_by(desc(sensor_data_table.c.timestamp))
        .limit(10)
    )

    recent_rows = db.execute(recent_query).fetchall()

    if len(recent_rows) >= 5:
        temps = [row.temperature for row in recent_rows]
        gases = [row.gas_level for row in recent_rows]

        avg_temp = sum(temps) / len(temps)
        avg_gas = sum(gases) / len(gases)

        temp_dev = abs(data.temperature - avg_temp) / avg_temp * 100
        gas_dev = abs(data.gas_level - avg_gas) / avg_gas * 100

        if temp_dev > 25:
            alerts.append((
                "TEMP_ROLLING_ANOMALY",
                "MEDIUM",
                f"Temperature deviation {temp_dev:.1f}% from rolling average"
            ))

        if gas_dev > 30:
            alerts.append((
                "GAS_ROLLING_ANOMALY",
                "HIGH",
                f"Gas level deviation {gas_dev:.1f}% from rolling average"
            ))

    # ---------- INSERT ALERTS ----------
    for alert_type, severity, message in alerts:
        db.execute(
            alert_table.insert().values(
                device_id=data.device_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                is_active=True
            )
        )

    db.commit()

    # ---------- AUTO-RESOLVE ----------
    if data.gas_level <= 300:
        db.execute(
            update(alert_table)
            .where(
                (alert_table.c.device_id == data.device_id) &
                (alert_table.c.alert_type.in_(["HIGH_GAS", "GAS_ANOMALY"])) &
                (alert_table.c.is_active == True)
            )
            .values(
                is_active=False,
                resolved_at=datetime.utcnow()
            )
        )


    if 0 <= data.temperature <= 60:
        db.execute(
            update(alert_table)
            .where(
                (alert_table.c.device_id == data.device_id) &
                (alert_table.c.alert_type.in_(["HIGH_TEMP", "LOW_TEMP", "TEMP_ANOMALY"])) &
                (alert_table.c.is_active == True)
            )
            .values(
                is_active=False,
                resolved_at=datetime.utcnow()
            )
        )


    db.commit()
    db.close()

    return {"status": "sensor data processed with threshold + rolling anomaly detection"}


# ------------------ DATA ENDPOINTS ------------------
@app.get("/all-data")
def get_all_data():
    with SessionLocal() as session:
        result = session.execute(select(sensor_data_table)).fetchall()
        return [dict(row._mapping) for row in result]


@app.get("/alerts")
def get_alerts():
    db = SessionLocal()
    rows = db.execute(
        select(alert_table).where(alert_table.c.is_active == True)
    ).fetchall()
    db.close()
    return [dict(row._mapping) for row in rows]


@app.get("/alerts/history")
def get_alert_history():
    db = SessionLocal()
    rows = db.execute(
        select(alert_table).where(alert_table.c.is_active == False)
    ).fetchall()
    db.close()
    return [dict(row._mapping) for row in rows]


@app.get("/alerts/stats")
def alert_stats():
    db = SessionLocal()
    total = db.execute(select(func.count()).select_from(alert_table)).scalar()
    active = db.execute(
        select(func.count()).select_from(alert_table)
        .where(alert_table.c.is_active == True)
    ).scalar()
    db.close()

    return {
        "total_alerts": total,
        "active_alerts": active,
        "resolved_alerts": total - active
    }
