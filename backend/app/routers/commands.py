import time

from fastapi import APIRouter, HTTPException

from app.models import CommandAck, CommandRequest
from app.mqtt_worker import publish_command

router = APIRouter(prefix="/api/v1/devices", tags=["commands"])


@router.post("/{device_id}/commands", response_model=CommandAck)
def send_command(device_id: str, command: CommandRequest) -> CommandAck:
    payload = {"cmd": command.cmd, "value": command.value, "server_ts": int(time.time())}
    try:
        topic = publish_command(device_id, payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return CommandAck(device_id=device_id, topic=topic, payload=payload)
