import time

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import ApiWeather


def fetch_and_store_openweather(db: Session) -> ApiWeather:
    settings = get_settings()
    params = {
        "lat": settings.station_lat,
        "lon": settings.station_lon,
        "appid": settings.openweather_api_key,
        "units": "metric",
    }
    response = httpx.get("https://api.openweathermap.org/data/2.5/weather", params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    main = data.get("main", {})
    weather = ApiWeather(
        ts=int(data.get("dt") or time.time()),
        temp_c=main.get("temp"),
        humidity_pct=main.get("humidity"),
        pressure_hpa=main.get("pressure"),
        source="openweathermap",
    )
    db.add(weather)
    db.commit()
    db.refresh(weather)
    return weather
