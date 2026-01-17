from sqlalchemy import create_engine, MetaData, Table, Column
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Integer, Float, String, DateTime, Boolean
from datetime import datetime

DATABASE_URL = "sqlite:///./iot_data.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

metadata = MetaData()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ---------------- SENSOR DATA TABLE ----------------
sensor_data_table = Table(
    "sensor_data",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("device_id", String, index=True),
    Column("temperature", Float),
    Column("gas_level", Float),
    Column("timestamp", DateTime, default=datetime.utcnow)  # ✅ USED FOR TRENDS
)

# ---------------- ALERT TABLE ----------------
alert_table = Table(
    "alerts",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("device_id", String, index=True),
    Column("alert_type", String),        # HIGH_GAS, HIGH_TEMP, LOW_TEMP
    Column("message", String),
    Column("severity", String, nullable=False),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime, default=datetime.utcnow),  # alerts timeline
    Column("resolved_at", DateTime, nullable=True),
)
