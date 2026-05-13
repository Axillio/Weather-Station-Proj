from sqlalchemy.orm import Session

from app.database import Alert, SensorReading
from app.models import AlertConfigIn

_alert_config = AlertConfigIn()


def get_alert_config() -> AlertConfigIn:
    return _alert_config


def update_alert_config(config: AlertConfigIn) -> AlertConfigIn:
    global _alert_config
    _alert_config = config
    return _alert_config


def evaluate_reading(db: Session, reading: SensorReading) -> list[Alert]:
    alerts: list[Alert] = []
    checks = [
        (reading.temp_c is not None and reading.temp_c < _alert_config.min_temp_c, "temperature_low", "Temperature below threshold"),
        (reading.temp_c is not None and reading.temp_c > _alert_config.max_temp_c, "temperature_high", "Temperature above threshold"),
        (reading.humidity_pct is not None and reading.humidity_pct < _alert_config.min_humidity_pct, "humidity_low", "Humidity below threshold"),
        (reading.humidity_pct is not None and reading.humidity_pct > _alert_config.max_humidity_pct, "humidity_high", "Humidity above threshold"),
        (reading.pressure_hpa is not None and reading.pressure_hpa < _alert_config.min_pressure_hpa, "pressure_low", "Pressure below threshold"),
        (reading.pressure_hpa is not None and reading.pressure_hpa > _alert_config.max_pressure_hpa, "pressure_high", "Pressure above threshold"),
        (
            _alert_config.min_battery_mv is not None and reading.battery_mv is not None and reading.battery_mv < _alert_config.min_battery_mv,
            "battery_low",
            "Battery below threshold",
        ),
    ]
    for failed, alert_type, message in checks:
        if failed:
            alerts.append(Alert(device_id=reading.device_id, alert_type=alert_type, message=message, severity="warning", ts=reading.ts))

    if not reading.is_valid:
        alerts.append(
            Alert(
                device_id=reading.device_id,
                alert_type="invalid_reading",
                message=reading.validation_error,
                severity="info",
                ts=reading.ts,
            )
        )

    if alerts:
        db.add_all(alerts)
        db.commit()
    return alerts
