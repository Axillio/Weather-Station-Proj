import time

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import Forecast, SensorReading


def generate_forecast(db: Session, device_id: str, horizon_seconds: int = 3600) -> Forecast:
    latest = (
        db.query(SensorReading)
        .filter(SensorReading.device_id == device_id, SensorReading.is_valid.is_(True))
        .order_by(desc(SensorReading.ts))
        .first()
    )
    now = int(time.time())
    forecast = Forecast(
        device_id=device_id,
        generated_at=now,
        forecast_for=now + horizon_seconds,
        temp_c=latest.temp_c if latest else None,
        humidity_pct=latest.humidity_pct if latest else None,
        model_name="persistence_baseline",
        model_version="0.1.0",
    )
    db.add(forecast)
    db.commit()
    db.refresh(forecast)
    return forecast
