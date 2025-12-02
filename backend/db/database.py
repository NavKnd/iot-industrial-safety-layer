from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///./iot_data.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

metadata = MetaData()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from sqlalchemy import Table, Column, Integer, Float, String, DateTime
from datetime import datetime

sensor_data_table = Table(
    "sensor_data",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("device_id", String, index=True),
    Column("temperature", Float),
    Column("gas_level", Float),
    Column("timestamp", DateTime, default=datetime.utcnow),
)
