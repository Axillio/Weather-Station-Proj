from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ForecastOut
from app.services.forecast_service import generate_forecast

router = APIRouter(prefix="/api/v1", tags=["forecast"])


@router.get("/forecast", response_model=ForecastOut)
def get_forecast(device_id: str, db: Session = Depends(get_db)):
    return generate_forecast(db, device_id)
