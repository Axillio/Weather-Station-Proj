from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


_BACKEND_DIR = Path(__file__).resolve().parents[1]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    app_env: str = "development"

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_tls: bool = False

    database_url: str = "sqlite:///./weather.db"

    openweather_api_key: str = "your_key_here"
    station_lat: float = 31.5204
    station_lon: float = 74.3587

    jwt_secret: str = "replace_this"
    default_device_id: str = Field(default="ws-esp32-001")
    run_mqtt_worker: bool = True
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    model_config = SettingsConfigDict(
        # Resolve relative to the backend folder so `uvicorn` can be launched from any cwd.
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
