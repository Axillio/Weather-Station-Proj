from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import Device, SensorReading, get_db
from app.models import DeviceOut, DeviceStatusOut

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.get("", response_model=list[DeviceOut])
def list_devices(db: Session = Depends(get_db)) -> list[Device]:
    return db.query(Device).order_by(Device.id).all()


@router.get("/{device_id}/status", response_model=DeviceStatusOut)
def device_status(device_id: str, db: Session = Depends(get_db)) -> DeviceStatusOut:
    reading = (
        db.query(SensorReading)
        .filter(SensorReading.device_id == device_id)
        .order_by(desc(SensorReading.created_at), desc(SensorReading.id))
        .first()
    )
    if reading is None:
        return DeviceStatusOut(
            device_id=device_id,
            is_online=False,
            status="down",
            rssi_status="unknown",
            battery_status="unknown",
        )

    now = datetime.now(timezone.utc)
    last_seen = reading.created_at.replace(tzinfo=timezone.utc) if reading.created_at.tzinfo is None else reading.created_at
    seconds_since_seen = max(0, int((now - last_seen).total_seconds()))
    is_online = seconds_since_seen <= 60

    rssi_status = "unknown"
    if reading.rssi_dbm is not None:
        if reading.rssi_dbm >= -65:
            rssi_status = "good"
        elif reading.rssi_dbm >= -80:
            rssi_status = "weak"
        else:
            rssi_status = "poor"

    battery_status = "unknown"
    if reading.battery_mv is not None:
        if reading.battery_mv >= 3700:
            battery_status = "good"
        elif reading.battery_mv >= 3400:
            battery_status = "low"
        else:
            battery_status = "critical"

    return DeviceStatusOut(
        device_id=device_id,
        is_online=is_online,
        status="online" if is_online else "down",
        last_seen_at=reading.created_at,
        seconds_since_seen=seconds_since_seen,
        rssi_dbm=reading.rssi_dbm,
        rssi_status=rssi_status,
        battery_mv=reading.battery_mv,
        battery_status=battery_status,
        fw_version=reading.fw_version,
        last_seq=reading.seq,
    )
