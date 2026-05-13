from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import Alert, get_db
from app.models import AlertConfigIn, AlertOut
from app.services.alert_service import get_alert_config, update_alert_config

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(device_id: str | None = None, limit: int = 100, db: Session = Depends(get_db)) -> list[Alert]:
    query = db.query(Alert)
    if device_id:
        query = query.filter(Alert.device_id == device_id)
    return query.order_by(desc(Alert.created_at)).limit(limit).all()


@router.get("/config", response_model=AlertConfigIn)
def read_alert_config() -> AlertConfigIn:
    return get_alert_config()


@router.post("/config", response_model=AlertConfigIn)
def write_alert_config(config: AlertConfigIn) -> AlertConfigIn:
    return update_alert_config(config)
