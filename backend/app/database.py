from collections.abc import Generator
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (UniqueConstraint("device_id", "seq", name="uq_sensor_readings_device_seq"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ts: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_hpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    rain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rain_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rssi_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    battery_mv: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fw_version: Mapped[str | None] = mapped_column(String, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ApiWeather(Base):
    __tablename__ = "api_weather"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    pressure_hpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String, default="openweathermap")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    generated_at: Mapped[int] = mapped_column(Integer, nullable=False)
    forecast_for: Mapped[int] = mapped_column(Integer, nullable=False)
    temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    alert_type: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    ts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.get(Device, settings.default_device_id) is None:
            db.add(
                Device(
                    id=settings.default_device_id,
                    name="ESP32 Weather Station",
                    location="Default station",
                    latitude=settings.station_lat,
                    longitude=settings.station_lon,
                    is_active=True,
                )
            )
            db.commit()
