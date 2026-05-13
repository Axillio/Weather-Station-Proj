from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field


class SensorReadingIn(BaseModel):
    schema_: str = Field(default="weather.v1", alias="schema")
    device_id: str
    seq: int = Field(ge=0)
    ts: int
    temp_c: float = Field(ge=-10, le=60)
    humidity_pct: float = Field(ge=0, le=100)
    pressure_hpa: float = Field(ge=800, le=1100)
    rain_raw: Optional[int] = Field(default=None, ge=0, le=4095)
    rain: bool
    rssi_dbm: Optional[int] = None
    battery_mv: Optional[int] = None
    fw_version: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class SensorReadingOut(BaseModel):
    id: int
    schema_: str = Field(default="weather.v1", alias="schema")
    device_id: str
    seq: int | None = None
    ts: int
    temp_c: float | None = None
    humidity_pct: float | None = None
    pressure_hpa: float | None = None
    rain_raw: int | None = None
    rain: bool | None = None
    rssi_dbm: int | None = None
    battery_mv: int | None = None
    fw_version: str | None = None
    is_valid: bool = True
    validation_error: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DeviceOut(BaseModel):
    id: str
    name: str | None = None
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceStatusOut(BaseModel):
    device_id: str
    is_online: bool
    status: str
    last_seen_at: datetime | None = None
    seconds_since_seen: int | None = None
    rssi_dbm: int | None = None
    rssi_status: str
    battery_mv: int | None = None
    battery_status: str
    fw_version: str | None = None
    last_seq: int | None = None


class CommandRequest(BaseModel):
    cmd: str = Field(min_length=1)
    value: Optional[int | str | bool] = None


class CommandAck(BaseModel):
    device_id: str
    topic: str
    payload: dict


class AlertConfigIn(BaseModel):
    min_temp_c: float = -10
    max_temp_c: float = 60
    min_humidity_pct: float = 0
    max_humidity_pct: float = 100
    min_pressure_hpa: float = 800
    max_pressure_hpa: float = 1100
    min_battery_mv: int | None = None


class AlertOut(BaseModel):
    id: int
    device_id: str
    alert_type: str | None = None
    message: str | None = None
    severity: str | None = None
    ts: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForecastOut(BaseModel):
    device_id: str
    generated_at: int
    forecast_for: int
    temp_c: float | None = None
    humidity_pct: float | None = None
    model_name: str | None = None
    model_version: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ComparisonOut(BaseModel):
    date: str
    device_id: str | None = None
    local_avg_temp_c: float | None = None
    api_avg_temp_c: float | None = None
    temp_delta_c: float | None = None
    local_avg_humidity_pct: float | None = None
    api_avg_humidity_pct: float | None = None
    humidity_delta_pct: float | None = None
    sample_count: int


NonEmptyString = Annotated[str, Field(min_length=1)]
