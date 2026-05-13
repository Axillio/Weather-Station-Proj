from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import ApiWeather, SensorReading, get_db
from app.models import ComparisonOut

router = APIRouter(prefix="/api/v1", tags=["comparison"])


@router.get("/comparison", response_model=ComparisonOut)
def compare_local_vs_api(date: str, device_id: str | None = None, db: Session = Depends(get_db)) -> ComparisonOut:
    day = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start = int(day.timestamp())
    end = start + 86400

    local_query = db.query(
        func.avg(SensorReading.temp_c),
        func.avg(SensorReading.humidity_pct),
        func.count(SensorReading.id),
    ).filter(SensorReading.ts >= start, SensorReading.ts < end, SensorReading.is_valid.is_(True))
    if device_id:
        local_query = local_query.filter(SensorReading.device_id == device_id)
    local_temp, local_humidity, sample_count = local_query.one()

    api_temp, api_humidity = (
        db.query(func.avg(ApiWeather.temp_c), func.avg(ApiWeather.humidity_pct))
        .filter(ApiWeather.ts >= start, ApiWeather.ts < end)
        .one()
    )

    return ComparisonOut(
        date=date,
        device_id=device_id,
        local_avg_temp_c=local_temp,
        api_avg_temp_c=api_temp,
        temp_delta_c=(local_temp - api_temp) if local_temp is not None and api_temp is not None else None,
        local_avg_humidity_pct=local_humidity,
        api_avg_humidity_pct=api_humidity,
        humidity_delta_pct=(local_humidity - api_humidity) if local_humidity is not None and api_humidity is not None else None,
        sample_count=sample_count,
    )
