import csv
import io

from typing import Any

from fastapi import Body
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import SensorReading, get_db
from app.models import SensorReadingOut
from app.services.storage_service import store_reading

router = APIRouter(prefix="/api/v1", tags=["readings"])


@router.get("/latest", response_model=SensorReadingOut)
def latest_reading(device_id: str, db: Session = Depends(get_db)) -> SensorReading:
    reading = (
        db.query(SensorReading)
        .filter(SensorReading.device_id == device_id)
        .order_by(desc(SensorReading.ts), desc(SensorReading.id))
        .first()
    )
    if reading is None:
        raise HTTPException(status_code=404, detail="No readings found")
    return reading


@router.get("/history", response_model=list[SensorReadingOut])
def history(
    device_id: str,
    start: int | None = Query(default=None),
    end: int | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> list[SensorReading]:
    query = db.query(SensorReading).filter(SensorReading.device_id == device_id)
    if start is not None:
        query = query.filter(SensorReading.ts >= start)
    if end is not None:
        query = query.filter(SensorReading.ts <= end)
    return query.order_by(desc(SensorReading.ts)).limit(limit).all()


@router.get("/export")
def export_csv(
    device_id: str,
    start: int | None = Query(default=None),
    end: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    rows = history(device_id=device_id, start=start, end=end, limit=5000, db=db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "device_id",
            "seq",
            "ts",
            "temp_c",
            "humidity_pct",
            "pressure_hpa",
            "rain",
            "rain_raw",
            "rssi_dbm",
            "battery_mv",
            "fw_version",
            "is_valid",
            "validation_error",
            "created_at",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row.id,
                row.device_id,
                row.seq,
                row.ts,
                row.temp_c,
                row.humidity_pct,
                row.pressure_hpa,
                row.rain,
                row.rain_raw,
                row.rssi_dbm,
                row.battery_mv,
                row.fw_version,
                row.is_valid,
                row.validation_error,
                row.created_at.isoformat(),
            ]
        )
    output.seek(0)
    headers = {"Content-Disposition": f'attachment; filename="{device_id}-readings.csv"'}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.post("/ingest", response_model=SensorReadingOut)
def ingest_reading(payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> SensorReading:
    """
    HTTP fallback for demos when MQTT connectivity/DNS is unreliable.
    Uses the same normalization + validation + storage pipeline as the MQTT worker.
    """
    reading, duplicate = store_reading(db, payload)
    if duplicate or reading is None:
        raise HTTPException(status_code=409, detail="Duplicate reading")
    return reading
