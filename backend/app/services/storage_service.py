import time
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Device, SensorReading
from app.models import SensorReadingIn

MAX_FUTURE_DRIFT_SECONDS = 300


def _get_value(payload: Mapping[str, Any], primary: str, legacy: str | None = None) -> Any:
    if primary in payload:
        return payload[primary]
    if legacy and legacy in payload:
        return payload[legacy]
    return None


def normalize_payload(payload: Mapping[str, Any], topic_device_id: str | None = None) -> dict[str, Any]:
    device_id = payload.get("device_id") or topic_device_id
    return {
        "schema": payload.get("schema", "weather.v1"),
        "device_id": device_id,
        "seq": _get_value(payload, "seq"),
        "ts": _get_value(payload, "ts"),
        "temp_c": _get_value(payload, "temp_c", "temp"),
        "humidity_pct": _get_value(payload, "humidity_pct", "hum"),
        "pressure_hpa": _get_value(payload, "pressure_hpa", "pres"),
        "rain_raw": _get_value(payload, "rain_raw"),
        "rain": _get_value(payload, "rain"),
        "rssi_dbm": _get_value(payload, "rssi_dbm"),
        "battery_mv": _get_value(payload, "battery_mv"),
        "fw_version": _get_value(payload, "fw_version"),
    }


def validate_reading(db: Session, payload: Mapping[str, Any], topic_device_id: str | None = None) -> tuple[dict[str, Any], bool, str | None]:
    normalized = normalize_payload(payload, topic_device_id)
    errors: list[str] = []

    payload_device_id = normalized.get("device_id")
    if topic_device_id and payload_device_id and payload_device_id != topic_device_id:
        errors.append("topic device_id does not match payload device_id")

    if not payload_device_id:
        errors.append("device_id is required")
    elif db.get(Device, str(payload_device_id)) is None:
        errors.append("unknown device_id")

    try:
        validated = SensorReadingIn.model_validate(normalized).model_dump(by_alias=True)
        normalized.update(validated)
    except ValidationError as exc:
        for err in exc.errors():
            field = ".".join(str(part) for part in err["loc"])
            errors.append(f"{field}: {err['msg']}")

    ts = normalized.get("ts")
    if isinstance(ts, int | float) and int(ts) > int(time.time()) + MAX_FUTURE_DRIFT_SECONDS:
        errors.append("timestamp too far in the future")

    return normalized, not errors, "; ".join(errors) if errors else None


def store_reading(db: Session, payload: Mapping[str, Any], topic_device_id: str | None = None) -> tuple[SensorReading | None, bool]:
    normalized, is_valid, validation_error = validate_reading(db, payload, topic_device_id)
    reading = SensorReading(
        device_id=str(normalized.get("device_id") or topic_device_id or "unknown"),
        seq=normalized.get("seq") if isinstance(normalized.get("seq"), int) else None,
        ts=int(normalized.get("ts") or time.time()),
        temp_c=_coerce_float(normalized.get("temp_c")),
        humidity_pct=_coerce_float(normalized.get("humidity_pct")),
        pressure_hpa=_coerce_float(normalized.get("pressure_hpa")),
        rain=_coerce_bool(normalized.get("rain")),
        rain_raw=_coerce_int(normalized.get("rain_raw")),
        rssi_dbm=_coerce_int(normalized.get("rssi_dbm")),
        battery_mv=_coerce_int(normalized.get("battery_mv")),
        fw_version=normalized.get("fw_version"),
        is_valid=is_valid,
        validation_error=validation_error,
    )
    db.add(reading)
    try:
        db.commit()
        db.refresh(reading)
        return reading, False
    except IntegrityError:
        db.rollback()
        return None, True


def _coerce_float(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
