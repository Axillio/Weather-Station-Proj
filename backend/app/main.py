from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.mqtt_worker import start_mqtt_worker, stop_mqtt_worker
from app.routers import alerts, commands, comparison, devices, forecast, readings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    if settings.run_mqtt_worker:
        start_mqtt_worker()
    yield
    if settings.run_mqtt_worker:
        stop_mqtt_worker()


app = FastAPI(
    title="Smart Weather Station API",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router)
app.include_router(readings.router)
app.include_router(forecast.router)
app.include_router(comparison.router)
app.include_router(alerts.router)
app.include_router(commands.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "Smart Weather Station API", "docs": "/docs"}
